import fs from "node:fs";
import { verifyTypedSelection, type VerifyCase } from "../src/services/typed-selection-verify";

/**
 * WP-E4b: independent TypeScript confirmation of typed day selections (design section 1.5).
 *
 * Run exactly like the npm script `experiments:fleet`:
 *   node --conditions=react-server --import tsx scripts/verify-typed-selection.ts <input.json> [--out <output.json>]
 *
 * Input JSON: one case object or `{ "cases": [case, ...] }` (see `VerifyCase` in
 * src/services/typed-selection-verify.ts): route data (route_details, student_ids, class counts), the vehicle
 * types and limits, and the selection (the chosen option's routes per wave with their labels), plus the Python
 * intervals to compare with. Output JSON: `{ "results": [ { caseId, ok, assignment, problems, recheck,
 * intervalDifferences } ] }` on stdout (or to --out). Exit code 0 when the input was processed (a failed check is
 * a result, not an error), 2 on unreadable or malformed input (a one-line JSON error on stderr). Offline: no
 * network, no database, no clock.
 */
function main(): number {
  const argv = process.argv.slice(2);
  const outIndex = argv.indexOf("--out");
  const outPath = outIndex >= 0 ? argv[outIndex + 1] : undefined;
  const inPath = argv.find((a, i) => !a.startsWith("--") && (outIndex < 0 || i !== outIndex + 1));
  if (!inPath) {
    console.error(JSON.stringify({ error: "usage: verify-typed-selection.ts <input.json> [--out <output.json>]" }));
    return 2;
  }
  let results: unknown[];
  try {
    const parsed = JSON.parse(fs.readFileSync(inPath, "utf8")) as { cases?: VerifyCase[] } | VerifyCase;
    const cases: VerifyCase[] = "cases" in parsed && Array.isArray(parsed.cases) ? parsed.cases : [parsed as VerifyCase];
    results = cases.map((item) => verifyTypedSelection(item));
  } catch (error) {
    console.error(JSON.stringify({ error: error instanceof Error ? error.message.slice(0, 2000) : "invalid input" }));
    return 2;
  }
  const text = JSON.stringify({ results }) + "\n";
  if (outPath) fs.writeFileSync(outPath, text, { encoding: "utf8" });
  else process.stdout.write(text);
  return 0;
}

process.exitCode = main();
