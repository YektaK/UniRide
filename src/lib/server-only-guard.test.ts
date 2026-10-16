import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// Audit L4: service-role / admin helpers must fail the build if a client
// component ever imports them (defence in depth).
const GUARDED_FILES = ["supabase-admin.ts", "admin-auth.ts"];

describe("server-only guard (audit L4)", () => {
  for (const file of GUARDED_FILES) {
    it(`${file} imports "server-only" as a top-level import`, () => {
      const source = readFileSync(join(__dirname, file), "utf8");
      expect(source).toMatch(/^import\s+(["'])server-only\1;?\s*$/m);
    });
  }
});
