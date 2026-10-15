import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Static guard for the update_updated_at_column search_path migration (Supabase advisor lint
 * 0011 function_search_path_mutable). No local Postgres exists in CI, so this proves the key
 * clauses are present in the SQL text and mirrored in supabase/schema.sql. The migration is
 * applied by the lead after review.
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

const migrationPath = path.join(root, "supabase/migrations/20261016_update_updated_at_search_path.sql");
const body = existsSync(migrationPath) ? normalise(readFileSync(migrationPath, "utf8")) : "";
const schema = normalise(readFileSync(path.join(root, "supabase/schema.sql"), "utf8"));

const definition =
  /create or replace function public\.update_updated_at_column\(\) returns trigger language plpgsql security invoker set search_path = '' as \$\$ begin new\.updated_at := pg_catalog\.now\(\); return new; end; \$\$;/;

describe("20261016 update_updated_at_search_path migration", () => {
  it("exists and is transactional", () => {
    expect(body).not.toBe("");
    expect(body).toMatch(/^begin;/);
    expect(body).toMatch(/commit; ?$/);
  });

  it("redefines the function with an empty search_path and a pg_catalog-qualified now()", () => {
    expect(body).toMatch(definition);
  });

  it("keeps the signature and the dependent triggers: no DROP FUNCTION, no trigger re-creation", () => {
    expect(body).not.toMatch(/drop function/);
    expect(body).not.toMatch(/drop trigger|create trigger/);
    expect(body).not.toMatch(/\bcascade\b/);
    expect(body.match(/create or replace function/g)).toHaveLength(1);
  });

  it("stays SECURITY INVOKER and changes no policy or grant", () => {
    expect(body).not.toContain("security definer");
    expect(body).not.toMatch(/create policy|drop policy|grant |revoke /);
  });
});

describe("supabase/schema.sql mirrors the migration", () => {
  it("defines the function with the hardened body", () => {
    expect(schema).toMatch(definition);
  });

  it("no longer contains the unqualified NOW() version", () => {
    expect(schema).not.toMatch(/function update_updated_at_column\(\) returns trigger as/);
    expect(schema).not.toContain("new.updated_at = now();");
  });

  it("still wires the eight triggers to the function", () => {
    const uses = schema.match(/execute function (public\.)?update_updated_at_column\(\)/g) ?? [];
    expect(uses).toHaveLength(8);
  });
});
