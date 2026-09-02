import { readFileSync } from "node:fs";
import * as ts from "typescript";

import { describe, expect, it } from "vitest";

type MessageValue = string | { [key: string]: MessageValue };
type Messages = { page: { benchmark: { [key: string]: MessageValue } } };

const pageSource = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
const enMessages = JSON.parse(
  readFileSync(new URL("../../messages/en.json", import.meta.url), "utf8")
) as Messages;
const trMessages = JSON.parse(
  readFileSync(new URL("../../messages/tr.json", import.meta.url), "utf8")
) as Messages;

const staticStringValue = (node: ts.Expression): string | undefined => {
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
    return node.text;
  }
  return undefined;
};

const collectBenchmarkKeys = (source: string): string[] => {
  const fileName = "benchmark-page.tsx";
  const compilerOptions: ts.CompilerOptions = { jsx: ts.JsxEmit.Preserve, noLib: true, noResolve: true, target: ts.ScriptTarget.Latest };
  const host = ts.createCompilerHost(compilerOptions);
  host.fileExists = (requestedFileName) => requestedFileName === fileName;
  host.readFile = (requestedFileName) => requestedFileName === fileName ? source : undefined;
  host.getSourceFile = (requestedFileName, languageVersion) => requestedFileName === fileName ? ts.createSourceFile(fileName, source, languageVersion, true, ts.ScriptKind.TSX) : undefined;
  const program = ts.createProgram({ rootNames: [fileName], options: compilerOptions, host });
  const sourceFile = program.getSourceFile(fileName);
  if (!sourceFile) throw new Error("Benchmark page source file was not created.");
  const checker = program.getTypeChecker();
  const bindings: ts.Identifier[] = [];

  const visitBindings = (node: ts.Node): void => {
    if (
      ts.isVariableDeclaration(node) &&
      ts.isIdentifier(node.name) &&
      node.name.text === "t" &&
      ts.isVariableDeclarationList(node.parent) &&
      (node.parent.flags & ts.NodeFlags.Const) !== 0 &&
      node.initializer &&
      ts.isCallExpression(node.initializer) &&
      ts.isIdentifier(node.initializer.expression) &&
      node.initializer.expression.text === "useTranslations" &&
      node.initializer.arguments.length === 1 &&
      staticStringValue(node.initializer.arguments[0]) === "page.benchmark"
    ) {
      bindings.push(node.name);
    }
    ts.forEachChild(node, visitBindings);
  };
  visitBindings(sourceFile);

  if (bindings.length !== 1) {
    throw new Error(`Expected exactly one benchmark translator binding, found ${bindings.length}.`);
  }

  const benchmarkTranslatorSymbol = checker.getSymbolAtLocation(bindings[0]);
  if (!benchmarkTranslatorSymbol) {
    throw new Error("Benchmark translator binding has no symbol.");
  }

  const translatorSymbols = new Set<ts.Symbol>([benchmarkTranslatorSymbol]);
  let changed = true;
  while (changed) {
    changed = false;
    const propagate = (node: ts.Node): void => {
      if (ts.isCallExpression(node)) {
        const parameters = checker.getResolvedSignature(node)?.declaration?.parameters ?? [];
        node.arguments.forEach((argument, index) => {
          const argumentSymbol = ts.isIdentifier(argument) ? checker.getSymbolAtLocation(argument) : undefined;
          const parameter = parameters[index];
          const parameterSymbol = parameter && ts.isIdentifier(parameter.name) ? checker.getSymbolAtLocation(parameter.name) : undefined;
          if (
            argumentSymbol && parameterSymbol && translatorSymbols.has(argumentSymbol) &&
            !translatorSymbols.has(parameterSymbol)
          ) {
            translatorSymbols.add(parameterSymbol);
            changed = true;
          }
        });
      }
      ts.forEachChild(node, propagate);
    };
    propagate(sourceFile);
  }

  const keys = new Set<string>();
  const visitCalls = (node: ts.Node): void => {
    const callSymbol = ts.isCallExpression(node) && ts.isIdentifier(node.expression)
      ? checker.getSymbolAtLocation(node.expression)
      : undefined;
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      callSymbol !== undefined && translatorSymbols.has(callSymbol) &&
      node.arguments.length > 0
    ) {

      const key = staticStringValue(node.arguments[0]);
      if (key !== undefined) {
        keys.add(key);
      }
    }
    ts.forEachChild(node, visitCalls);
  };
  visitCalls(sourceFile);

  return [...keys].sort();
};

const benchmarkKeys = collectBenchmarkKeys(pageSource);

const resolveMessage = (messages: Messages, key: string): MessageValue | undefined =>
  key.split(".").reduce<MessageValue | undefined>(
    (value, segment) =>
      value && typeof value === "object" ? value[segment] : undefined,
    messages.page.benchmark
  );

const flattenKeys = (value: MessageValue, prefix = ""): string[] =>
  typeof value === "string"
    ? [prefix]
    : Object.entries(value).flatMap(([key, child]) =>
        flattenKeys(child, prefix ? `${prefix}.${key}` : key)
      );

describe("benchmark message catalog contract", () => {
  it.each([
    ["en", enMessages],
    ["tr", trMessages],
  ] as const)("resolves every page benchmark key in %s", (_locale, messages) => {
    const missing = benchmarkKeys.filter((key) => resolveMessage(messages, key) === undefined);
    expect(missing).toEqual([]);

    for (const key of benchmarkKeys) {
      const value = resolveMessage(messages, key);
      expect(typeof value === "string" ? value.trim() : value).toBeTruthy();
    }
  });

  it("keeps English and Turkish page benchmark key shapes aligned", () => {
    expect(flattenKeys(enMessages.page.benchmark).sort()).toEqual(
      flattenKeys(trMessages.page.benchmark).sort()
    );
  });

  it("does not expose raw Turkish page benchmark key names", () => {
    for (const key of benchmarkKeys) {
      expect(resolveMessage(trMessages, key)).not.toBe(`page.benchmark.${key}`);
    }
  });

  it("collects only literal calls to the benchmark translator binding", () => {
    const fixture = `
      const t = useTranslations("page.benchmark");
      const tc = useTranslations("common");
      const unrelated = useTranslations("page.benchmark");
      // t("comment")
      const quoted = 't("string")';
      t("included");
      t(\`alsoIncluded\`);
      tc("excludedCommon");
      unrelated("excludedTranslator");
      t(dynamicKey);
      t(\`template-\${suffix}\`);
    `;

    expect(collectBenchmarkKeys(fixture)).toEqual(["alsoIncluded", "included"]);
  });

  it("requires exactly one benchmark translator binding", () => {
    expect(() =>
      collectBenchmarkKeys('const t = useTranslations("page.benchmark"); const t = useTranslations("page.benchmark");')
    ).toThrow("Expected exactly one");
});

  it("excludes calls to nested t bindings that shadow the benchmark translator", () => {
    const fixture = `
      const t = useTranslations("page.benchmark");
      t("root");
      function withParameter(t: (key: string) => string) {
        t("shadowedParameter");
      }
      function withLocal() {
        const t = useTranslations("page.other");
        t("shadowedLocal");
      }
    `;

    expect(collectBenchmarkKeys(fixture)).toEqual(["root"]);
  });

  it("follows the benchmark translator when it is forwarded into a helper", () => {
    const fixture = `
      const t = useTranslations("page.benchmark");
      t("root");
      function helper(translator: (key: string) => string) {
        translator("forwarded");
      }
      function unrelated(translator: (key: string) => string) {
        translator("shadowedUnrelated");
      }
      const other = useTranslations("common");
      helper(t);
      unrelated(other);
    `;

    expect(collectBenchmarkKeys(fixture)).toEqual(["forwarded", "root"]);
  });

  it("collects all current benchmark page translation keys", () => {
    expect(benchmarkKeys).toHaveLength(196);
  });
});
