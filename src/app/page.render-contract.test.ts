import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const pageSource = readFileSync(new URL("./page.tsx", import.meta.url), "utf8");

describe("BenchmarkSuitePage render contract", () => {
  it("keeps browser-only state out of the initial render", () => {
    expect(pageSource).toContain("const [runHistory, setRunHistory] = useState<RunHistoryEntry[]>([]);");
    expect(pageSource).toContain("const [isDark, setIsDark] = useState(false);");
    expect(pageSource).toContain("setRunHistory(loadRunHistory());");
    expect(pageSource).toContain('setIsDark(document.documentElement.classList.contains("dark"));');
  });

  it("derives elapsed time from a captured observation instead of render-time Date.now", () => {
    expect(pageSource).toContain("const elapsedSeconds = (startTimeIso: string, observedAt: number) =>");
    expect(pageSource).toContain("const estimateRemainingSeconds = (startTimeIso: string, progressPercent: number, observedAt: number) =>");
    expect(pageSource).toContain("elapsedSeconds(startTimeIso, observedAt)");
    expect(pageSource).toContain("const [observedAt, setObservedAt] = useState(0);");
    expect(pageSource).toContain("elapsedSeconds(runStatus.start_time, observedAt)");
    expect(pageSource).toContain("estimateRemainingSeconds(runStatus.start_time, runStatus.progress_percent, observedAt)");
    expect(pageSource).not.toMatch(
      /const elapsedSeconds[\s\S]*?Date\.now\(\)[\s\S]*?const estimateRemainingSeconds/
    );
    expect(pageSource.match(/setObservedAt\(Date\.now\(\)\)/g)?.length).toBeGreaterThanOrEqual(3);
  });
});
