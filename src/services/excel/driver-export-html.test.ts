import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { exportDriverAssignmentsToPDF, type AssignmentWithDetails } from "./driver-export";
import { escapeHtml } from "@/lib/escape-html";

const PAYLOADS = [
  "<img src=x onerror=alert(1)>",
  '"><script>alert(1)</script>',
  "<script src=//evil></script>",
  "' onmouseover='alert(1)",
  "a & b",
];

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

let html = "";
beforeEach(() => {
  html = "";
  const printWindow = { document: { write: (s: string) => { html += s; }, close: () => {} }, print: () => {}, onload: null };
  vi.stubGlobal("window", { open: () => printWindow });
});
afterEach(() => vi.unstubAllGlobals());

describe("escapeHtml", () => {
  it("escapes & < > \" '", () => {
    expect(escapeHtml(`&<>"'`)).toBe("&amp;&lt;&gt;&quot;&#39;");
  });
  it("leaves plain text alone and treats null/undefined as empty", () => {
    expect(escapeHtml("Ayşe Yılmaz (123)")).toBe("Ayşe Yılmaz (123)");
    expect(escapeHtml(null)).toBe("");
    expect(escapeHtml(undefined)).toBe("");
  });
});

describe("driver PDF export HTML (M8 / P3-07)", () => {
  it.each(PAYLOADS)("escapes the payload %j in vehicle, driver, student name and student number", async (payload) => {
    await exportDriverAssignmentsToPDF([item(payload)], "2026-10-15");

    const escaped = escapeHtml(payload);
    expect(html).toContain(escaped);
    // Whatever is left after removing every escaped payload is the page template only.
    const template = html.split(escaped).join("");
    for (const needle of ["<script", "<img", "onerror", "onmouseover", "alert(1)", "//evil"]) {
      expect(template.toLowerCase(), needle).not.toContain(needle);
    }
    // And the escaped payload itself holds no raw markup characters.
    expect(escaped).not.toMatch(/[<>"']/);
  });

  it("keeps a plain-text name readable and escapes the student-number suffix", async () => {
    const it0 = item("Ayşe");
    (it0.students[0] as unknown as { studentNumber: string }).studentNumber = "<b>1</b>";
    await exportDriverAssignmentsToPDF([it0], "2026-10-15");

    expect(html).toContain("Ayşe (&lt;b&gt;1&lt;/b&gt;)");
    expect(html).not.toContain("<b>1</b>");
  });
});
