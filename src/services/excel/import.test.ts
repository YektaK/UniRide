import * as XLSX from "xlsx";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/database", () => ({
  createSchedule: vi.fn(),
  getScheduleByUserId: vi.fn(),
  getUsers: vi.fn(),
  updateScheduleEntries: vi.fn(),
  updateUser: vi.fn(),
}));

import { parseExcelFile } from "./import";

class TestFileReader {
  result: ArrayBuffer | null = null;
  onload: ((event: ProgressEvent<FileReader>) => void) | null = null;
  onerror: (() => void) | null = null;

  readAsArrayBuffer(file: File) {
    void file.arrayBuffer().then((result) => {
      this.result = result;
      this.onload?.({ target: this } as unknown as ProgressEvent<FileReader>);
    }).catch(() => this.onerror?.());
  }
}

function spreadsheet(rows: unknown[][]): File {
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(rows), "Schedules");
  const bytes = XLSX.write(workbook, { bookType: "xlsx", type: "array" });

  return { arrayBuffer: async () => bytes } as File;
}

describe("parseExcelFile", () => {
  beforeEach(() => {
    vi.stubGlobal("FileReader", TestFileReader);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("normalizes D.Kampus to Dudullu and excludes Davutpaşa", async () => {
    const rows = await parseExcelFile(spreadsheet([
      ["studentNumber", "day", "courseCode", "startTime", "endTime", "location"],
      ["100", "monday", "CS101", "09:00", "10:00", "D.Kampus"],
      ["101", "monday", "CS102", "11:00", "12:00", "Davutpaşa"],
    ]));

    expect(rows).toEqual([{
      studentNumber: "100",
      day: "monday",
      courseCode: "CS101",
      startTime: "09:00",
      endTime: "10:00",
      location: "Dudullu",
    }]);
  });
});
