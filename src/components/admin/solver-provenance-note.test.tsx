// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import en from "../../../messages/en.json";
import tr from "../../../messages/tr.json";

let messages: Record<string, unknown> = en;

// Real message catalogue with minimal {name} interpolation, so wording and keys are checked.
vi.mock("next-intl", () => ({
  useTranslations: (namespace: string) => (key: string, values: Record<string, string | number> = {}) => {
    const node = [...namespace.split("."), ...key.split(".")].reduce<unknown>(
      (acc, part) => (acc as Record<string, unknown> | undefined)?.[part],
      messages,
    );
    if (typeof node !== "string") throw new Error(`missing message ${namespace}.${key}`);
    return node.replace(/\{(\w+)\}/g, (_m, name) => String(values[name]));
  },
}));

import { SolverProvenanceNote } from "./solver-provenance-note";

afterEach(cleanup);

describe("SolverProvenanceNote", () => {
  it("renders nothing without provenance (old plan, older optimizer)", () => {
    const { container } = render(<SolverProvenanceNote provenance={null} />);
    expect(container.innerHTML).toBe("");
    cleanup();
    const second = render(<SolverProvenanceNote provenance={undefined} />);
    expect(second.container.innerHTML).toBe("");
  });

  it("shows the config source and seed in English", () => {
    render(<SolverProvenanceNote provenance={{ algorithm_used: "ga_split", effective_config_source: "default", effective_seed: 42 }} />);
    expect(screen.getByTestId("solver-provenance").textContent).toContain("Algorithm settings: built-in defaults · seed 42");
  });

  it("shows the config source and seed in Turkish", () => {
    messages = tr;
    render(<SolverProvenanceNote provenance={{ effective_config_source: "request", effective_seed: 7 }} />);
    expect(screen.getByTestId("solver-provenance").textContent).toContain("Algoritma ayarları: istekle gelen ayarlar · tohum 7");
    messages = en;
  });

  it("shows an unknown source raw", () => {
    render(<SolverProvenanceNote provenance={{ effective_config_source: "future-mode" }} />);
    expect(screen.getByTestId("solver-provenance").textContent).toContain("future-mode");
  });

  it("shows the fallback and its reason", () => {
    render(<SolverProvenanceNote provenance={{ algorithm_requested: "e2bso", algorithm_used: "greedy_fallback", fallback_reason: "solver_error" }} />);
    const note = screen.getByTestId("solver-provenance");
    expect(note.textContent).toContain("greedy_fallback");
    expect(note.textContent).toContain("solver_error");
  });

  it("renders nothing when only the algorithm names are known and no fallback happened", () => {
    const { container } = render(<SolverProvenanceNote provenance={{ algorithm_requested: "ga", algorithm_used: "ga" }} />);
    expect(container.innerHTML).toBe("");
  });
});
