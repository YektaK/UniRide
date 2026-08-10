import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const pageSource = readFileSync(new URL("./page.tsx", import.meta.url), "utf8");

describe("route-test BFF contract", () => {
  it("uses the authenticated admin client and forwards local search settings", () => {
    expect(pageSource).toContain('import { adminApi } from "@/lib/admin-api"');
    expect(pageSource).toContain("adminApi.routes.optimize({");
    expect(pageSource).toContain("local_search_type: algorithmSupportsLocalSearch(algorithm) ? localSearchType : undefined");
    expect(pageSource).toContain("max_travel_time: 180");
  });

  it("does not import or call the optimizer service directly", () => {
    expect(pageSource).not.toMatch(/from "@\/services\/optimizer-service"/);
    expect(pageSource).not.toContain("optimizeRoutes");
    expect(pageSource).not.toContain("/api/optimize-route");
  });
});
