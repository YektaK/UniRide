import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Static guard for the live-apply migration of public.student_leg_decisions. The 2026-09-29
 * migration was never applied to the live database (read-only check 2026-10-15), so the
 * 20261016b migration brings the live DB to the same contract, hardened (search_path '',
 * pg_catalog-qualified clock_timestamp, SECURITY INVOKER; Supabase advisor lint 0011).
 * No local Postgres exists in CI: this proves the clauses in the SQL text and the mirror in
 * supabase/schema.sql. The migration is applied by the owner.
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

const read = (relative: string) => normalise(readFileSync(path.join(root, relative), "utf8"));
const migrationRelative = "supabase/migrations/20261016b_apply_student_leg_decisions.sql";
const migrationExists = existsSync(path.join(root, migrationRelative));
const body = migrationExists ? read(migrationRelative) : "";
const original = read("supabase/migrations/20260929_create_student_leg_decisions.sql");
const schema = read("supabase/schema.sql");

const tableStatement = (text: string): string => {
  const match = text.match(/create table if not exists public\.student_leg_decisions \(.*?\);/);
  return match ? match[0] : "";
};

const hardenedFunction =
  "create or replace function public.set_student_leg_decided_at() returns trigger " +
  "language plpgsql security invoker set search_path = '' as $$ begin " +
  "if tg_op = 'insert' then new.decided_at := pg_catalog.clock_timestamp(); " +
  "elsif row(new.decision, new.flexibility_minutes) is distinct from row(old.decision, old.flexibility_minutes) " +
  "then new.decided_at := pg_catalog.clock_timestamp(); " +
  "else new.decided_at := old.decided_at; end if; return new; end; $$;";

const triggerStatements =
  "drop trigger if exists student_leg_decisions_set_decided_at on public.student_leg_decisions; " +
  "create trigger student_leg_decisions_set_decided_at before insert or update on public.student_leg_decisions " +
  "for each row execute function public.set_student_leg_decided_at();";

const accessStatements =
  "alter table public.student_leg_decisions enable row level security; " +
  "revoke all on public.student_leg_decisions from anon, authenticated; " +
  "grant select, insert, update, delete on public.student_leg_decisions to service_role;";

describe("20261016b apply_student_leg_decisions migration", () => {
  it("exists, is transactional and sorts after the 20261016 search_path migration", () => {
    expect(migrationExists).toBe(true);
    expect(body).toMatch(/^begin;/);
    expect(body).toMatch(/commit; ?$/);
    expect(migrationRelative.split("/").pop()! > "20261016_update_updated_at_search_path.sql").toBe(true);
  });

  it("creates the table with exactly the 20260929 columns, checks and primary key", () => {
    const expected = tableStatement(original);
    expect(expected).toContain("primary key (user_id, service_date, direction)");
    expect(expected).toContain("check (direction in ('pickup', 'dropoff'))");
    expect(expected).toContain("check (decision in ('confirmed', 'cancelled'))");
    expect(expected).toContain("check (flexibility_minutes between 0 and 1439)");
    expect(tableStatement(body)).toBe(expected);
  });

  it("defines the decided_at trigger function hardened: invoker, empty search_path, qualified clock", () => {
    expect(body).toContain(hardenedFunction);
    expect(body).not.toContain("security definer");
    expect(body).not.toMatch(/[^.]clock_timestamp\(\)/);
    expect(body.match(/search_path = ''/g)).toHaveLength(1);
  });

  it("re-creates the trigger idempotently", () => {
    expect(body).toContain(triggerStatements);
  });

  it("enables RLS, revokes anon/authenticated and grants service_role only", () => {
    expect(body).toContain(accessStatements);
    expect(body).not.toMatch(/create policy|grant [^;]* to (anon|authenticated|public)/);
  });

  it("is idempotent and never destroys data", () => {
    expect(body).not.toMatch(/drop table|truncate|delete from|drop function|\bcascade\b|alter table [^;]* drop/);
    expect(body).not.toMatch(/insert into|update public/);
  });
});

describe("supabase/schema.sql mirrors the live-apply migration", () => {
  it("has the same table, function, trigger and access statements", () => {
    expect(tableStatement(schema)).toBe(tableStatement(body));
    expect(schema).toContain(hardenedFunction);
    expect(schema).toContain(triggerStatements);
    expect(schema).toContain(accessStatements);
  });

  it("no longer contains the unqualified clock_timestamp() version", () => {
    expect(schema).not.toMatch(/[^.]clock_timestamp\(\)/);
  });
});
