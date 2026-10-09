import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Static guard for the route_plans read lock (audit C1.d) and M21 (drop-all loop).
 * No local Postgres exists in CI, so this proves the key clauses are present in the
 * SQL text. Behavioural proof: supabase/tests/20261010_route_plans_read_lock.sql
 * (BEGIN ... ROLLBACK, run by the owner after applying the migration).
 */
const root = path.resolve(__dirname, "../..");
const migrationPath = path.join(root, "supabase/migrations/20261010_route_plans_read_lock.sql");
const normalise = (text: string) =>
  text
    .replace(/--.*$/gm, "")
    .replace(/\s+/g, " ")
    .replace(/\( /g, "(")
    .replace(/ \)/g, ")")
    .trim()
    .toLowerCase();

const body = existsSync(migrationPath) ? normalise(readFileSync(migrationPath, "utf8")) : "";
const legacy = normalise(readFileSync(path.join(root, "supabase/rls_policies.sql"), "utf8"));

describe("20261010 route_plans_read_lock migration", () => {
  it("exists and is transactional", () => {
    expect(body).not.toBe("");
    expect(body).toMatch(/^begin;/);
    expect(body).toMatch(/commit; ?$/);
  });

  it("replaces the public read policy with a driver/admin authenticated one", () => {
    expect(body).toContain('drop policy if exists "drivers can read route_plans" on public.route_plans');
    expect(body).toMatch(
      /create policy "drivers can read route_plans" on public\.route_plans for select to authenticated using \(status in \('confirmed', 'active', 'completed'\) and exists \(select 1 from public\.users u where u\.id = auth\.uid\(\) and u\.role in \('driver', 'admin'\)\)\)/,
    );
  });

  it.each(["route_plans", "sandbox_scenarios"])("limits the admin ALL policy on %s to authenticated with WITH CHECK", (table) => {
    const re = new RegExp(
      String.raw`create policy "admins can crud ${table}" on public\.${table} for all to authenticated using \(exists \(select 1 from public\.users u where u\.id = auth\.uid\(\) and u\.role = 'admin'\)\) with check \(exists \(select 1 from public\.users u where u\.id = auth\.uid\(\) and u\.role = 'admin'\)\)`,
    );
    expect(body).toMatch(re);
  });

  it.each([
    ["admin_settings_select_all", "admin_settings"],
    ["routes_select_all", "routes"],
    ["vehicles_select_all", "vehicles"],
  ])("moves %s to authenticated with an unchanged qual", (policy, table) => {
    expect(body).toContain(
      `create policy "${policy}" on public.${table} for select to authenticated using (auth.uid() is not null)`,
    );
  });

  it("has a closing guard that aborts on public/anon policies before commit", () => {
    const guardAt = body.indexOf("from pg_policies");
    expect(guardAt).toBeGreaterThan(-1);
    const guard = body.slice(guardAt, body.lastIndexOf("commit;"));
    expect(guard).toContain("&& array['public', 'anon']");
    expect(guard).toContain("raise exception");
  });

  it("never grants to anon or public", () => {
    expect(body).not.toMatch(/to (anon|public)\b/);
    expect(body).not.toContain("using (true)");
  });
});

describe("supabase/rls_policies.sql (M21 retired)", () => {
  it("no longer drops every public policy", () => {
    expect(legacy).not.toMatch(/from pg_policies/);
    expect(legacy).not.toMatch(/drop policy if exists "' \|\|/);
  });

  it("starts with the abort guard as the first statement after begin", () => {
    expect(legacy).toMatch(
      /^begin; do \$\$ begin raise exception 'supabase\/rls_policies\.sql is a legacy reference/,
    );
  });

  it("has no executable statement after the guard except commit", () => {
    const afterGuard = legacy.split("end $$;")[1];
    expect(afterGuard.trim()).toBe("commit;");
  });
});
