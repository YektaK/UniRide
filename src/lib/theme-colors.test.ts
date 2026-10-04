import { readdirSync, readFileSync } from "node:fs";
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
      const plain = typeof value === "function" ? value({}) : (value as string);
      const faded = typeof value === "function" ? value({ opacityValue: "0.5" }) : (value as string);
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
      const resolved = typeof value === "function" ? value({}) : (value as string);
      const variable = /^var\((--[\w-]+)\)$/.exec(resolved)?.[1];
      expect(variable, name).toBeTruthy();
      expect(rootBlock, `${name} -> ${variable}`).toContain(`${variable}:`);
      expect(darkBlock, `${name} -> ${variable}`).toContain(`${variable}:`);
    }
  });
});

// Regression: charts used hsl(var(--chart-n)) / hsl(var(--muted)); with oklch() variables that is an
// invalid color, so the series and tooltip cursor rendered wrong. Use var(--x) directly.
describe("source files", () => {
  function sourceFiles(dir: string): string[] {
    return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) return entry.name === "node_modules" ? [] : sourceFiles(full);
      return /\.(ts|tsx)$/.test(entry.name) ? [full] : [];
    });
  }

  it("never wraps a theme variable in hsl(var(--...))", () => {
    const srcRoot = path.resolve(__dirname, "..");
    const thisFile = path.resolve(__filename);
    const offenders = sourceFiles(srcRoot)
      .filter((file) => path.resolve(file) !== thisFile)
      .filter((file) => /hsl\(\s*var\(\s*--/.test(readFileSync(file, "utf8")))
      .map((file) => path.relative(srcRoot, file));
    expect(offenders).toEqual([]);
  });
});
