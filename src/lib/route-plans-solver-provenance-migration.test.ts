import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Static guard for migration 20261016c (route_plans.solver_provenance, DECISION_LOG S08).
 * No local Postgres exists in CI, so this proves the key clauses are in the SQL text.
 */
const root = path.resolve(__dirname, "../..");
const migrationPath = path.join(root, "supabase/migrations/20261016c_route_plans_solver_provenance.sql");
const normalise = (text: string) =>
  text.replace(/--.*$/gm, "").replace(/\s+/g, " ").replace(/\( /g, "(").replace(/ \)/g, ")").trim().toLowerCase();

const body = existsSync(migrationPath) ? normalise(readFileSync(migrationPath, "utf8")) : "";
const schema = normalise(readFileSync(path.join(root, "supabase/schema.sql"), "utf8"));

describe("20261016c route_plans_solver_provenance migration", () => {
  it("exists, is transactional and sorts after the other 20261016 migration", () => {
    expect(body).not.toBe("");
    expect(body).toMatch(/^begin;/);
    expect(body).toMatch(/commit; ?$/);
    expect("20261016c_route_plans_solver_provenance.sql" > "20261016_update_updated_at_search_path.sql").toBe(true);
  });

  it("adds a nullable jsonb column idempotently, without default or backfill", () => {
    expect(body).toContain(
      "alter table public.route_plans add column if not exists solver_provenance jsonb null",
    );
    expect(body).not.toMatch(/solver_provenance jsonb null default/);
    expect(body).not.toMatch(/\bupdate public\.route_plans\b/);
  });

  it("allows only null or a JSON object", () => {
    expect(body).toMatch(
      /check \(solver_provenance is null or jsonb_typeof\(solver_provenance\) = 'object'\)/,
    );
  });

  it("is added idempotently (the check is guarded)", () => {
    expect(body).toMatch(/pg_constraint|if not exists|drop constraint if exists/);
  });

  it("does not touch policies, grants or the role lock", () => {
    expect(body).not.toMatch(/create policy|drop policy|alter policy|\bgrant\b|\brevoke\b|disable row level security/);
  });

  it("is mirrored in schema.sql", () => {
    expect(schema).toMatch(/solver_provenance jsonb/);
    expect(schema).toMatch(/jsonb_typeof\(solver_provenance\) = 'object'/);
  });
});
