import { readFileSync } from "node:fs";
import * as ts from "typescript";

import { describe, expect, it } from "vitest";

type MessageValue = string | { [key: string]: MessageValue };
type Messages = { page: { admin: { benchmark: { [key: string]: MessageValue } } } };

const NAMESPACE = "page.admin.benchmark";

const read = (path: string): string => readFileSync(new URL(path, import.meta.url), "utf8");
const pageSource = read("../app/(app)/admin/benchmark/page.tsx");
const enMessages = JSON.parse(read("../../messages/en.json")) as Messages;
const trMessages = JSON.parse(read("../../messages/tr.json")) as Messages;

type Usage = { key: string; params: string[]; tags: string[] };

const literal = (node: ts.Node | undefined): string | undefined =>
  node && (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) ? node.text : undefined;

/** Collects literal t("key", {params}) calls made through the page.admin.benchmark translator. */
const collectUsages = (source: string): Usage[] => {
  const sf = ts.createSourceFile("page.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const names = new Set<string>();
  const find = (node: ts.Node): void => {
    if (
      ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer &&
      ts.isCallExpression(node.initializer) && ts.isIdentifier(node.initializer.expression) &&
      node.initializer.expression.text === "useTranslations" &&
      literal(node.initializer.arguments[0]) === NAMESPACE
    ) names.add(node.name.text);
    ts.forEachChild(node, find);
  };
  find(sf);
  if (names.size === 0) throw new Error("No translator bound to " + NAMESPACE);

  const usages = new Map<string, { params: Set<string>; tags: Set<string> }>();
  const isTranslatorCall = (callee: ts.Expression): boolean =>
    (ts.isIdentifier(callee) && names.has(callee.text)) ||
    (ts.isPropertyAccessExpression(callee) && ts.isIdentifier(callee.expression) &&
      names.has(callee.expression.text) && ["rich", "markup", "raw"].includes(callee.name.text));
  const visit = (node: ts.Node): void => {
    if (ts.isCallExpression(node) && isTranslatorCall(node.expression)) {
      const key = literal(node.arguments[0]);
      if (key !== undefined) {
        const entry = usages.get(key) ?? { params: new Set<string>(), tags: new Set<string>() };
        const arg = node.arguments[1];
        if (arg && ts.isObjectLiteralExpression(arg)) {
          for (const p of arg.properties) {
            if (!ts.isPropertyAssignment(p) && !ts.isShorthandPropertyAssignment(p) && !ts.isMethodDeclaration(p)) continue;
            if (!ts.isIdentifier(p.name)) continue;
            const isTag = ts.isMethodDeclaration(p) ||
              (ts.isPropertyAssignment(p) && (ts.isArrowFunction(p.initializer) || ts.isFunctionExpression(p.initializer)));
            (isTag ? entry.tags : entry.params).add(p.name.text);
          }
        }
        usages.set(key, entry);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return [...usages]
    .map(([key, e]) => ({ key, params: [...e.params], tags: [...e.tags] }))
    .sort((a, b) => a.key.localeCompare(b.key));
};

const usages = collectUsages(pageSource);

const resolve = (messages: Messages, key: string): MessageValue | undefined =>
  key.split(".").reduce<MessageValue | undefined>(
    (v, seg) => (v && typeof v === "object" ? v[seg] : undefined),
    messages.page.admin.benchmark
  );

const flatten = (value: MessageValue, prefix = ""): string[] =>
  typeof value === "string"
    ? [prefix]
    : Object.entries(value).flatMap(([k, c]) => flatten(c, prefix ? `${prefix}.${k}` : k));

describe("admin benchmark page message catalog", () => {
  it("finds the keys the page uses (including enum-derived category labels)", () => {
    expect(usages.length).toBeGreaterThanOrEqual(100);
    const keys = usages.map((u) => u.key);
    for (const cat of ["small", "medium", "large"]) expect(keys).toContain(`categories.${cat}`);
  });

  it.each([
    ["en", enMessages],
    ["tr", trMessages],
  ] as const)("resolves every page key to a non-empty string in %s", (_l, messages) => {
    const bad = usages.filter(({ key }) => {
      const v = resolve(messages, key);
      return typeof v !== "string" || v.trim() === "";
    }).map((u) => u.key);
    expect(bad).toEqual([]);
  });

  it.each([
    ["en", enMessages],
    ["tr", trMessages],
  ] as const)("declares every interpolation parameter the page passes in %s", (_l, messages) => {
    const bad = usages.flatMap(({ key, params }) => {
      const v = resolve(messages, key);
      return typeof v === "string"
        ? params.filter((p) => !v.includes(`{${p}}`)).map((p) => `${key}:{${p}}`)
        : [];
    });
    expect(bad).toEqual([]);
  });

  it.each([
    ["en", enMessages],
    ["tr", trMessages],
  ] as const)("declares every rich-text tag the page passes in %s", (_l, messages) => {
    const bad = usages.flatMap(({ key, tags }) => {
      const v = resolve(messages, key);
      return typeof v === "string"
        ? tags.filter((t) => !v.includes(`<${t}>`) || !v.includes(`</${t}>`)).map((t) => `${key}:<${t}>`)
        : [];
    });
    expect(bad).toEqual([]);
  });

  it("collects t.rich, t.markup and t.raw calls with params and tags", () => {
    const fixture = `
      const t = useTranslations("${NAMESPACE}");
      t.rich("r", { n: 1, b: (c) => c });
      t.markup("m", { x });
      t.raw("w");
    `;
    expect(collectUsages(fixture)).toEqual([
      { key: "m", params: ["x"], tags: [] },
      { key: "r", params: ["n"], tags: ["b"] },
      { key: "w", params: [], tags: [] },
    ]);
  });

  it("keeps tr and en key sets identical under page.admin.benchmark", () => {
    expect(flatten(trMessages.page.admin.benchmark).sort()).toEqual(
      flatten(enMessages.page.admin.benchmark).sort()
    );
  });
});
