import { readFileSync } from "node:fs";
import * as ts from "typescript";

import { describe, expect, it } from "vitest";

type Messages = { common: { sidebar: Record<string, string> } };

const sidebarSource = readFileSync(
  new URL("../components/layout/app-sidebar.tsx", import.meta.url),
  "utf8"
);
const enMessages = JSON.parse(
  readFileSync(new URL("../../messages/en.json", import.meta.url), "utf8")
) as Messages;
const trMessages = JSON.parse(
  readFileSync(new URL("../../messages/tr.json", import.meta.url), "utf8")
) as Messages;

const collectSidebarKeys = (source: string): string[] => {
  const sourceFile = ts.createSourceFile(
    "app-sidebar.tsx",
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX
  );
  const keys = new Set<string>();

  const visit = (node: ts.Node): void => {
    if (
      ts.isPropertyAssignment(node) &&
      node.name.getText(sourceFile) === "labelKey" &&
      ts.isStringLiteral(node.initializer)
    ) {
      keys.add(node.initializer.text);
    }
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      node.expression.text === "t" &&
      node.arguments.length > 0 &&
      ts.isStringLiteral(node.arguments[0])
    ) {
      keys.add(node.arguments[0].text);
    }
    ts.forEachChild(node, visit);
  };

  visit(sourceFile);
  return [...keys].sort();
};

const sidebarKeys = collectSidebarKeys(sidebarSource);

describe("sidebar message catalog contract", () => {
  it.each([
    ["en", enMessages],
    ["tr", trMessages],
  ] as const)("resolves every active sidebar key in %s", (_locale, messages) => {
    const missing = sidebarKeys.filter(
      (key) => !messages.common.sidebar[key]?.trim()
    );

    expect(missing).toEqual([]);
  });

  it("collects the current menu and logout keys", () => {
    expect(sidebarKeys).toHaveLength(22);
    expect(sidebarKeys).toContain("sandbox");
    expect(sidebarKeys).toContain("logout");
  });
});
