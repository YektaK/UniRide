import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Static guard for QW1 (audit C1 / C1.b). No local Postgres is available in CI,
 * so this only proves the key clauses are present in the migration text. The
 * behavioural proof is supabase/tests/20261009_role_lock.sql, run by the owner.
 */
const root = path.resolve(__dirname, "../..");
const sql = readFileSync(
  path.join(root, "supabase/migrations/20261009_lock_user_role_and_ride_status.sql"),
  "utf8",
);
// Strip comments and collapse whitespace so assertions ignore formatting.
const body = sql
  .replace(/--.*$/gm, "")
  .replace(/\s+/g, " ")
  .toLowerCase();

describe("20261009 lock_user_role_and_ride_status migration", () => {
  it("restricts self-insert on users to role student for authenticated", () => {
    expect(body).toMatch(
      /create policy "users_insert_self" on public\.users for insert to authenticated with check \(auth\.uid\(\) = id and role = 'student'\)/,
    );
  });

  it("gives users_update_own a WITH CHECK", () => {
    expect(body).toMatch(
      /create policy "users_update_own" on public\.users for update to authenticated using \(auth\.uid\(\) = id\) with check \(auth\.uid\(\) = id\)/,
    );
  });

  it("defines prevent_role_change as invoker with empty search_path and no is_admin", () => {
    expect(body).toMatch(/create or replace function public\.prevent_role_change\(\)/);
    const fn = body.split("create or replace function public.prevent_role_change()")[1].split("$$")[0];
    expect(fn).not.toContain("security definer");
    expect(fn).toContain("set search_path = ''");
    expect(body).toContain("auth.role() = 'service_role'");
    expect(body).not.toMatch(/is_admin\s*\(/);
    expect(body).toContain("tg_op = 'insert'");
    expect(body).toContain("new.role is distinct from old.role");
    expect(body).toContain("service_role");
  });

  it("fires the trigger on INSERT or UPDATE OF role", () => {
    expect(body).toMatch(
      /create trigger enforce_no_role_change before insert or update of role on public\.users for each row execute function public\.prevent_role_change\(\)/,
    );
  });

  it("restricts ride_requests insert and update to safe statuses", () => {
    expect(body).toMatch(
      /on public\.ride_requests for insert to authenticated with check \(auth\.uid\(\) = user_id and status in \('pending_admin_approval', 'pending_student_confirmation'\) and vehicle_id is null and actual_pickup_time is null and actual_dropoff_time is null\)/,
    );
    expect(body).toMatch(
      /on public\.ride_requests for update to authenticated using \(auth\.uid\(\) = user_id and status in \('pending_admin_approval', 'pending_student_confirmation', 'confirmed'\)\) with check \(auth\.uid\(\) = user_id and status = 'cancelled_by_student' and vehicle_id is null and actual_pickup_time is null and actual_dropoff_time is null\)/,
    );
  });

  it("only uses status values that exist in schema.sql", () => {
    const schema = readFileSync(path.join(root, "supabase/schema.sql"), "utf8");
    for (const status of [
      "pending_admin_approval",
      "pending_student_confirmation",
      "cancelled_by_student",
    ]) {
      expect(schema).toContain(`'${status}'`);
    }
  });

  it("pins search_path and revokes anon/public on the SECURITY DEFINER RPCs", () => {
    for (const fn of [
      "get_available_drivers()",
      "get_route_plans_with_students(date, text)",
    ]) {
      expect(body).toContain(`alter function public.${fn} set search_path = public`);
      expect(body).toContain(`revoke all on function public.${fn} from public, anon, authenticated`);
    }
  });

  it("aborts if a FOR ALL policy exists on users or ride_requests", () => {
    expect(body).toMatch(/cmd = 'all'[\s\S]*raise exception 'for all policy/);
  });

  it("is re-runnable: policies and trigger are dropped before creation", () => {
    expect(body).toContain("drop trigger if exists enforce_no_role_change on public.users");
    expect(body).toContain('drop policy if exists "users_insert_self" on public.users');
    expect(body).toContain('drop policy if exists "users_update_own" on public.users');
  });
});
