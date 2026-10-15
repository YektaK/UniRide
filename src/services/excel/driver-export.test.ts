import { beforeEach, describe, expect, it, vi } from "vitest";
import * as XLSX from "xlsx";

// Capture the workbook instead of touching the file system.
const { written } = vi.hoisted(() => ({ written: [] as Array<{ wb: unknown; filename: string }> }));
vi.mock("xlsx", async (importOriginal) => {
  const actual = await importOriginal<typeof import("xlsx")>();
  const patched = { ...actual, writeFile: (wb: unknown, filename: string) => { written.push({ wb, filename }); } };
  return { ...patched, default: patched };
});

import { exportDriverAssignmentsToExcel, type AssignmentWithDetails } from "./driver-export";

const PAYLOADS = ["=1+1", "+1+1", "-2+3", "@SUM(A1)", "=HYPERLINK(\"http://evil\",\"x\")", "=cmd|' /C calc'!A0"];

const item = (payload: string): AssignmentWithDetails => ({
  assignment: {
    date: "2026-10-15",
    pickupTime: "2026-10-15T07:00:00Z",
    estimatedDropoffTime: "2026-10-15T08:00:00Z",
    status: "scheduled",
  },
  vehicle: { name: payload, plateNumber: payload, type: "van", seatingCapacity: 4, wheelchairCapacity: 1 },
  driver: { name: payload, email: payload },
  students: [{ name: payload, studentNumber: payload, email: payload, homeAddress: payload }],
} as unknown as AssignmentWithDetails);

beforeEach(() => { written.length = 0; });

describe("driver assignment XLSX export (formula injection)", () => {
  it("SheetJS json_to_sheet stores strings that start with = + - @ as plain string cells, never as formulas", async () => {
    await exportDriverAssignmentsToExcel(PAYLOADS.map(item), "2026-10-15");
    expect(written).toHaveLength(1);

    // Round trip through the real xlsx writer/reader: what a spreadsheet app would load.
    const bytes = XLSX.write(written[0].wb as XLSX.WorkBook, { bookType: "xlsx", type: "array" });
    const reread = XLSX.read(bytes, { type: "array" });
    expect(reread.SheetNames).toEqual(["Görevlendirmeler", "Öğrenci Detayları"]);

    let checked = 0;
    for (const sheetName of reread.SheetNames) {
      const sheet = reread.Sheets[sheetName];
      for (const address of Object.keys(sheet).filter((k) => !k.startsWith("!"))) {
        const cell = sheet[address] as XLSX.CellObject;
        expect(cell.f, `${sheetName}!${address} must not carry a formula`).toBeUndefined();
        if (typeof cell.v === "string" && /^[=+\-@]/.test(cell.v)) {
          expect(cell.t).toBe("s");
          checked += 1;
        }
      }
    }
    expect(checked).toBeGreaterThan(0);
  });
});
