import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Static guard for the time_matrix.updated_at migration (audit M4, DECISION_LOG T09).
 * No local Postgres exists in CI, so this proves the key clauses are present in the SQL text
 * and mirrored in supabase/schema.sql. The migration is applied by the lead after review.
 */
const root = path.resolve(__dirname, "../..");
const normalise = (text: string) =>
  text
    .replace(/--.*$/gm, "")
    .replace(/\s+/g, " ")
    .replace(/\( /g, "(")
    .replace(/ \)/g, ")")
    .trim()
    .toLowerCase();

const migrationPath = path.join(root, "supabase/migrations/20261015_time_matrix_updated_at.sql");
const body = existsSync(migrationPath) ? normalise(readFileSync(migrationPath, "utf8")) : "";
const schema = normalise(readFileSync(path.join(root, "supabase/schema.sql"), "utf8"));

describe("20261015 time_matrix_updated_at migration", () => {
  it("exists and is transactional", () => {
    expect(body).not.toBe("");
    expect(body).toMatch(/^begin;/);
    expect(body).toMatch(/commit; ?$/);
  });

  it("adds the column idempotently, backfills from created_at, then sets NOT NULL and the default", () => {
    const add = body.indexOf("alter table public.time_matrix add column if not exists updated_at timestamptz;");
    const backfill = body.indexOf(
      "update public.time_matrix set updated_at = coalesce(created_at, now()) where updated_at is null;",
    );
    const constrain = body.indexOf(
      "alter table public.time_matrix alter column updated_at set default now(), alter column updated_at set not null;",
    );
    expect(add).toBeGreaterThanOrEqual(0);
    // the history must be backfilled BEFORE the constraint, and the default must not stamp old rows
    expect(backfill).toBeGreaterThan(add);
    expect(constrain).toBeGreaterThan(backfill);
  });

  it("creates a security invoker trigger function with an empty search_path", () => {
    expect(body).toMatch(
      /create or replace function public\.set_time_matrix_updated_at\(\) returns trigger language plpgsql security invoker set search_path = ''/,
    );
    expect(body).toContain("new.updated_at := pg_catalog.now();");
    expect(body).not.toContain("security definer");
  });

  it("installs a BEFORE UPDATE row trigger idempotently", () => {
    expect(body).toContain("drop trigger if exists time_matrix_set_updated_at on public.time_matrix;");
    expect(body).toContain(
      "create trigger time_matrix_set_updated_at before update on public.time_matrix for each row execute function public.set_time_matrix_updated_at();",
    );
  });

  it("changes no policy, grant or arc value", () => {
    expect(body).not.toMatch(/create policy|drop policy|grant |revoke |set duration_minutes/);
  });
});

describe("supabase/schema.sql mirrors the migration", () => {
  it("declares the column on time_matrix", () => {
    expect(schema).toMatch(/create table if not exists time_matrix \([^;]*updated_at timestamptz not null default now\(\)/);
  });

  it("declares the same function and trigger", () => {
    expect(schema).toMatch(
      /create or replace function public\.set_time_matrix_updated_at\(\) returns trigger language plpgsql security invoker set search_path = ''/,
    );
    expect(schema).toContain(
      "create trigger time_matrix_set_updated_at before update on public.time_matrix for each row execute function public.set_time_matrix_updated_at();",
    );
  });
});
