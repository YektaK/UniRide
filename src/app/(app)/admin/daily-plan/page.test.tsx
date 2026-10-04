// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  blockedResponse,
  emptyDayResponse,
  indeterminateResponse,
  readyResponse,
  shortageResponse,
} from "@/services/daily-plan-fixtures";
import type { DudulluPreviewResponse } from "@/services/dudullu-preview-response";
import trMessages from "../../../../../messages/tr.json";

const mocks = vi.hoisted(() => ({
  run: vi.fn(),
}));


// Real Turkish copy, so the tests assert what the admin actually reads.
vi.mock("next-intl", () => ({
  useTranslations: (namespace: string) => (key: string, values?: Record<string, string | number>) => {
    const path = `${namespace}.${key}`.split(".");
    let node: unknown = trMessages;
    for (const segment of path) {
      node = typeof node === "object" && node !== null ? (node as Record<string, unknown>)[segment] : undefined;
    }
    if (typeof node !== "string") throw new Error(`missing message ${path.join(".")}`);
    return node.replace(/\{(\w+)\}/g, (_match, name: string) => String(values?.[name] ?? `{${name}}`));
  },
}));

vi.mock("@/lib/admin-api", () => ({
  adminApi: { preview: { run: mocks.run } },
  DailyPlanRequestError: class DailyPlanRequestError extends Error {
    constructor(public readonly kind: string) {
      super(`Daily plan request failed: ${kind}`);
    }
  },
}));

import DailyPlanPage from "./page";
import { DailyPlanRequestError } from "@/lib/admin-api";

const runButton = () => screen.getByRole("button", { name: "Planı oluştur" });
const setDate = (value: string) => fireEvent.change(screen.getByLabelText("Tarih"), { target: { value } });

async function generate(response: DudulluPreviewResponse) {
  mocks.run.mockResolvedValue(response);
  render(<DailyPlanPage />);
  setDate("2026-10-05");
  fireEvent.click(runButton());
  await screen.findByTestId("status-banner");
}

describe("DailyPlanPage", () => {
  afterEach(cleanup);

  beforeEach(() => {
    mocks.run.mockReset();
  });

  it("starts with the demo defaults and an initial prompt", () => {
    render(<DailyPlanPage />);

    expect(screen.getByRole("heading", { name: "Günlük Plan" })).toBeTruthy();
    expect((screen.getByLabelText("Tarih") as HTMLInputElement).value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(screen.getByRole("switch", { name: "Öğrenci onaylarını varsay (demo)" }).getAttribute("aria-checked")).toBe("true");
    expect(screen.getByRole("switch", { name: "Sanal filo (gereken araç)" }).getAttribute("aria-checked")).toBe("true");
    expect(screen.getByText(/Bir tarih seçip/)).toBeTruthy();
    expect(mocks.run).not.toHaveBeenCalled();
  });

  it("sends assume_confirmed and virtual by default", async () => {
    await generate(readyResponse());

    expect(mocks.run).toHaveBeenCalledTimes(1);
    expect(mocks.run).toHaveBeenCalledWith("2026-10-05", {
      admissionMode: "assume_confirmed",
      fleetMode: "virtual",
    });
  });

  it("sends recorded and live when both switches are turned off", async () => {
    mocks.run.mockResolvedValue(readyResponse());
    render(<DailyPlanPage />);
    setDate("2026-10-05");
    fireEvent.click(screen.getByRole("switch", { name: "Öğrenci onaylarını varsay (demo)" }));
    fireEvent.click(screen.getByRole("switch", { name: "Sanal filo (gereken araç)" }));
    expect(screen.getByText(/Mevcut filo: yalnızca/)).toBeTruthy();
    fireEvent.click(runButton());
    await screen.findByTestId("status-banner");

    expect(mocks.run).toHaveBeenCalledWith("2026-10-05", {
      admissionMode: "recorded",
      fleetMode: "live",
    });
  });

  it("does not run for an invalid date", () => {
    render(<DailyPlanPage />);
    setDate("2026-02-30");

    expect((runButton() as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(runButton());
    expect(mocks.run).not.toHaveBeenCalled();
  });

  it("shows loading, then the vehicle count, a wave and its stops", async () => {
    let resolve: (value: DudulluPreviewResponse) => void = () => undefined;
    mocks.run.mockReturnValue(new Promise<DudulluPreviewResponse>((done) => { resolve = done; }));
    render(<DailyPlanPage />);
    setDate("2026-10-05");
    fireEvent.click(runButton());

    expect(await screen.findByTestId("plan-loading")).toBeTruthy();
    expect(screen.getByText(/Plan hazırlanıyor\. Çözücü/)).toBeTruthy();
    const busy = screen.getByRole("button", { name: "Plan hazırlanıyor..." }) as HTMLButtonElement;
    expect(busy.disabled).toBe(true);

    resolve(readyResponse());
    await screen.findByTestId("status-banner");

    expect(screen.queryByTestId("plan-loading")).toBeNull();
    const needed = screen.getByTestId("card-needed-vehicles");
    expect(within(needed).getByText("Bu rotalar için gereken araç")).toBeTruthy();
    expect(within(needed).getByTestId("needed-vehicles-value").textContent).toBe("2");
    expect(within(needed).queryByText("en fazla")).toBeNull();
    expect(screen.getByText("Önizleme hazır")).toBeTruthy();

    expect(screen.getByRole("heading", { name: "Sabah toplama" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Akşam bırakma" })).toBeTruthy();
    expect(screen.getByText("08:45 varış — Toplama")).toBeTruthy();
    expect(screen.getByText("17:00 çıkış — Bırakma")).toBeTruthy();
    expect(screen.getByText("2 rota · 3 öğrenci · 1 Sw · 2 So")).toBeTruthy();
    expect(screen.getAllByText("So1 Öğrenci").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sw2 Öğrenci").length).toBeGreaterThan(0);
    expect(screen.getAllByText("08:28").length).toBeGreaterThan(0);

    const fleet = screen.getByTestId("card-fleet");
    expect(within(fleet).getByText("Mevcut filo")).toBeTruthy();
    expect(within(fleet).getByText("1 araç eksik")).toBeTruthy();

    const rows = screen.getAllByTestId("vehicle-row");
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getByText("Araç 1")).toBeTruthy();
  });

  it("always shows the non-publishable banner and offers no publish or save action", async () => {
    await generate(readyResponse());

    const banner = screen.getByTestId("preview-banner");
    expect(within(banner).getByText("Önizleme — yayınlanamaz, varsayımsal")).toBeTruthy();
    expect(within(banner).getByText("Öğrenci onayları varsayıldı.")).toBeTruthy();
    expect(within(banner).getByText(/Sanal filo kullanıldı: 4 Sw \/ 10 So/)).toBeTruthy();
    const buttons = screen.getAllByRole("button").map((button) => button.textContent ?? "");
    expect(buttons.filter((text) => /yayınla|kaydet|onayla|ata\b/i.test(text))).toEqual([]);
  });

  it("uses the plain banner title when the response is not hypothetical", async () => {
    await generate(shortageResponse());

    const banner = screen.getByTestId("preview-banner");
    expect(within(banner).getByText("Önizleme — yayınlanamaz")).toBeTruthy();
    expect(within(banner).queryByText(/varsayımsal/)).toBeNull();
  });

  it("marks an unproven vehicle count with the 'en fazla' badge", async () => {
    await generate(indeterminateResponse());

    const needed = screen.getByTestId("card-needed-vehicles");
    expect(within(needed).getByText("en fazla")).toBeTruthy();
    expect(within(needed).getByTestId("needed-vehicles-value").textContent).toBe("3");
    expect(within(needed).getByText(/daha az araç mümkün olabilir/)).toBeTruthy();
    expect(screen.getByText("Sonuç kesin değil")).toBeTruthy();
    expect(screen.getByText(/Gösterilen araç sayısı en fazla değerdir/)).toBeTruthy();
  });

  it("shows a shortage without a vehicle count", async () => {
    await generate(shortageResponse());

    expect(screen.getByText("Araç yetersiz")).toBeTruthy();
    const needed = screen.getByTestId("card-needed-vehicles");
    expect(within(needed).getByTestId("needed-vehicles-value").textContent).toBe("—");
    expect(within(needed).getByText("Bu rotalar için en az 2 araç gerekir.")).toBeTruthy();
    expect(screen.getByText("Mevcut filo bu rotalar için yetersiz.")).toBeTruthy();
    expect(screen.getByText(/Bu sonuçta araç ataması yok/)).toBeTruthy();
    expect(screen.queryAllByTestId("vehicle-row")).toHaveLength(0);
  });

  it("shows blocked data with plain Turkish reasons and no waves", async () => {
    await generate(blockedResponse(["MATRIX_UNAVAILABLE", "SCHEDULE_DATA_INVALID"]));

    expect(screen.getByText("Plan oluşturulamadı: veri veya hizmet sorunu")).toBeTruthy();
    expect(screen.getByText(/Seyahat süresi matrisi alınamadı veya eksik/)).toBeTruthy();
    expect(screen.getByText("Ders programı veya öğrenci kaydı verisi geçersiz.")).toBeTruthy();
    expect(screen.queryAllByTestId("wave-card")).toHaveLength(0);
    expect(screen.queryByTestId("vehicle-schedule")).toBeNull();
  });

  it("explains an unknown reason code instead of hiding it", async () => {
    await generate(blockedResponse(["BRAND_NEW_CODE"]));

    expect(screen.getByText("Bilinmeyen durum kodu. Teknik ekibe bildirin. (BRAND_NEW_CODE)")).toBeTruthy();
  });

  it("shows the empty-day state", async () => {
    await generate(emptyDayResponse());

    expect(screen.getByTestId("empty-day")).toBeTruthy();
    expect(screen.getByText("Bu gün için planlanacak sefer yok")).toBeTruthy();
    expect(screen.queryByTestId("card-needed-vehicles")).toBeNull();
  });

  it.each([
    ["unavailable", /Önizleme hizmeti şu anda kullanılamıyor/],
    ["authorization", /Yönetici oturumu doğrulanamadı/],
    ["timeout", /zaman aşımına uğradı/],
    ["invalidResponse", /beklenmeyen bir yanıt/],
  ])("shows the %s error state and allows a retry", async (kind, message) => {
    mocks.run.mockRejectedValueOnce(new DailyPlanRequestError(kind as never));
    render(<DailyPlanPage />);
    setDate("2026-10-05");
    fireEvent.click(runButton());

    const alert = await screen.findByTestId("plan-error");
    expect(within(alert).getByText("Plan oluşturulamadı")).toBeTruthy();
    expect(within(alert).getByText(message)).toBeTruthy();
    expect(screen.queryByTestId("status-banner")).toBeNull();

    mocks.run.mockResolvedValueOnce(readyResponse());
    fireEvent.click(runButton());
    await screen.findByTestId("status-banner");
    expect(screen.queryByTestId("plan-error")).toBeNull();
  });

  it("treats an unexpected failure as an unavailable service", async () => {
    mocks.run.mockRejectedValueOnce(new Error("boom"));
    render(<DailyPlanPage />);
    fireEvent.click(runButton());

    const alert = await screen.findByTestId("plan-error");
    expect(within(alert).getByText(/Önizleme hizmeti şu anda kullanılamıyor/)).toBeTruthy();
  });

  it("blocks a second run while a request is in flight", async () => {
    let resolveFirst: (value: DudulluPreviewResponse) => void = () => undefined;
    mocks.run
      .mockReturnValueOnce(new Promise<DudulluPreviewResponse>((done) => { resolveFirst = done; }))
      .mockResolvedValueOnce(emptyDayResponse());
    render(<DailyPlanPage />);
    fireEvent.click(runButton());
    await screen.findByTestId("plan-loading");
    // The button is disabled while loading, so a second run cannot start.
    const busy = screen.getByRole("button", { name: "Plan hazırlanıyor..." }) as HTMLButtonElement;
    expect(busy.disabled).toBe(true);
    fireEvent.click(busy);
    expect(mocks.run).toHaveBeenCalledTimes(1);

    resolveFirst(readyResponse());
    await waitFor(() => expect(screen.getByTestId("card-needed-vehicles")).toBeTruthy());
  });

  it("never renders anything but location-code labels, even if names leak into ids", async () => {
    const response = readyResponse();
    const leaked = "Ayşe Yılmaz";
    response.occurrenceLabels = { "occ-a": leaked };
    response.jobs[0].result.routes[0].student_ids = [leaked];
    response.jobs[0].intervals[0].occurrenceIds = [leaked];
    response.assignments[0].occurrenceIds = [leaked];
    await generate(response);

    expect(document.body.textContent).not.toContain("Ayşe");
    expect(document.body.textContent).not.toContain("Yılmaz");
    expect(screen.getAllByText("So1 Öğrenci").length).toBeGreaterThan(0);
  });

  it("shows the known limitations on demand", async () => {
    render(<DailyPlanPage />);

    expect(screen.queryByText(/optimal değildir/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Bilinen sınırlamalar/ }));
    expect(await screen.findByText(/Çözücü rotaları optimal değildir/)).toBeTruthy();
    expect(screen.getByText(/H2, H4/)).toBeTruthy();
    expect(screen.getByText(/Araç sayısı yalnızca bu sabit rotalar için hesaplanır/)).toBeTruthy();
  });
});
