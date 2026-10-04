import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import tailwindConfig from "../../tailwind.config";

type ColorValue = string | ((options: { opacityValue?: string }) => string) | { [key: string]: ColorValue };

const globalsCss = readFileSync(path.resolve(__dirname, "../app/globals.css"), "utf8");

function collect(node: ColorValue, trail: string[] = []): Array<{ name: string; value: ColorValue }> {
  if (typeof node === "string" || typeof node === "function") return [{ name: trail.join("-"), value: node }];
  return Object.entries(node).flatMap(([key, child]) => collect(child, [...trail, key]));
}

const colors = collect(tailwindConfig.theme?.extend?.colors as ColorValue);

// Regression: the theme variables hold complete oklch() colors. Wrapping them in hsl(var(--x))
// made every bg-primary / bg-input / bg-background utility an invalid declaration (transparent
// switches, text-like buttons).
describe("tailwind theme colors", () => {
  it("defines the semantic colors", () => {
    expect(colors.length).toBeGreaterThan(20);
  });

  it("never wraps a variable in hsl() or rgb()", () => {
    for (const { name, value } of colors) {
      const plain = typeof value === "function" ? value({}) : value;
      const faded = typeof value === "function" ? value({ opacityValue: "0.5" }) : value;
      expect(plain, name).not.toMatch(/\b(hsl|rgb)a?\(/);
      expect(faded, name).not.toMatch(/\b(hsl|rgb)a?\(/);
    }
  });

  it("resolves to the css variable, with a color-mix for opacity modifiers", () => {
    const primary = colors.find((color) => color.name === "primary-DEFAULT")?.value;
    expect(typeof primary).toBe("function");
    const resolve = primary as (options: { opacityValue?: string }) => string;
    expect(resolve({})).toBe("var(--primary)");
    expect(resolve({ opacityValue: "0.9" })).toBe("color-mix(in oklab, var(--primary) 90%, transparent)");
  });

  it("only references variables that globals.css defines in :root and .dark", () => {
    const rootBlock = globalsCss.slice(globalsCss.indexOf(":root"), globalsCss.indexOf(".dark"));
    const darkBlock = globalsCss.slice(globalsCss.indexOf(".dark"));
    for (const { name, value } of colors) {
      const resolved = typeof value === "function" ? value({}) : value;
      const variable = /^var\((--[\w-]+)\)$/.exec(resolved)?.[1];
      expect(variable, name).toBeTruthy();
      expect(rootBlock, `${name} -> ${variable}`).toContain(`${variable}:`);
      expect(darkBlock, `${name} -> ${variable}`).toContain(`${variable}:`);
    }
  });
});
