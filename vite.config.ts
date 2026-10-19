import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx", "scripts/**/*.test.ts"],
    // Each jsdom worker imports the full React/Radix tree; on machines with
    // many cores the unbounded default oversubscribes CPU and random tests
    // hit the 5 s per-test timeout. Capping workers keeps per-test timing
    // honest without raising any timeout.
    maxWorkers: 4,
  },
});
