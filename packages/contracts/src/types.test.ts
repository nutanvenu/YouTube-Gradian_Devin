import { describe, expect, it } from "vitest";
import { isAgeBand, isCapabilityLevel, isPolicyDecisionAction } from "./types.js";

describe("contract type guards", () => {
  it("accept only canonical age bands", () => {
    expect(isAgeBand("PRETEEN")).toBe(true);
    expect(isAgeBand("ADULT")).toBe(false);
  });

  it("accept only canonical capability levels", () => {
    expect(isCapabilityLevel("BEST_EFFORT")).toBe(true);
    expect(isCapabilityLevel("PARTIAL")).toBe(false);
  });

  it("accept only canonical decision actions", () => {
    expect(isPolicyDecisionAction("ALLOW_WITH_BUDGET")).toBe(true);
    expect(isPolicyDecisionAction("UNKNOWN")).toBe(false);
  });
});
