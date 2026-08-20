import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import hardCategories from "../hard-categories.json" with { type: "json" };
import contentRiskContract from "../content-risk-contract.json" with { type: "json" };
import {
  CONTENT_BLOCK_THRESHOLDS,
  CONTENT_RISK_ACTIONS,
  CONTENT_RISK_CATEGORIES,
  CONTENT_RISK_CATEGORY_ALIASES,
  CONTENT_RISK_REASON_CODES,
  CONTENT_RISK_SEVERITIES,
  CONTENT_RISK_SIGNAL_SOURCES,
  HARD_CATEGORIES,
  CAPABILITY_LEVELS,
  isAgeBand,
  isCapabilityLevel,
  isPolicyDecisionAction
} from "./types.js";

const kotlinContractSource = readFileSync(
  resolve(
    process.cwd(),
    "apps/mobile/modules/guardian-protection/android/src/main/java/expo/modules/guardianprotection/content/ContentRiskContracts.kt",
  ),
  "utf8",
);

function kotlinEnumValues(name: string): string[] {
  const body = new RegExp(`enum class ${name} \\{([\\s\\S]*?)\\n\\}`, "m").exec(
    kotlinContractSource,
  )?.[1];
  expect(body).toBeDefined();
  return [...(body ?? "").matchAll(/^\s+([A-Z_]+),?$/gm)]
    .map((match) => match[1])
    .filter((value): value is string => value !== undefined);
}

describe("contract type guards", () => {
  it("accept only canonical age bands", () => {
    expect(isAgeBand("PRETEEN")).toBe(true);
    expect(isAgeBand("ADULT")).toBe(false);
  });

  it("accept only canonical capability levels", () => {
    expect(isCapabilityLevel("BEST_EFFORT")).toBe(true);
    expect(isCapabilityLevel("LIMITED")).toBe(true);
    expect(isCapabilityLevel("PARTIAL")).toBe(false);
  });

  it("accept only canonical decision actions", () => {
    expect(isPolicyDecisionAction("ALLOW_WITH_BUDGET")).toBe(true);
    expect(isPolicyDecisionAction("UNKNOWN")).toBe(false);
  });

  it("keeps the exported hard categories aligned with the shared artifact", () => {
    expect(HARD_CATEGORIES).toEqual(hardCategories);
  });

  it("keeps content-risk enums and age defaults aligned with the shared artifact", () => {
    expect(CONTENT_RISK_SIGNAL_SOURCES).toEqual(contentRiskContract.signal_sources);
    expect(CONTENT_RISK_ACTIONS).toEqual(contentRiskContract.actions);
    expect(CONTENT_RISK_SEVERITIES).toEqual(contentRiskContract.severities);
    expect(CONTENT_RISK_CATEGORIES).toEqual(contentRiskContract.categories);
    expect(CONTENT_RISK_CATEGORY_ALIASES).toEqual(contentRiskContract.category_aliases);
    expect(CONTENT_RISK_REASON_CODES).toEqual(contentRiskContract.reason_codes);
    expect(CAPABILITY_LEVELS).toEqual(contentRiskContract.capability_levels);
    expect(CONTENT_BLOCK_THRESHOLDS).toEqual(contentRiskContract.content_block_thresholds);
  });

  it("uses the canonical PRD MVP content taxonomy with legacy aliases", () => {
    expect(CONTENT_RISK_CATEGORIES).toEqual([
      "ADULT_NUDITY",
      "SEXUAL_CONTENT",
      "GROOMING_RISK",
      "BULLYING_HARASSMENT",
      "HATE_EXTREMISM",
      "SELF_HARM_SUICIDE",
      "GRAPHIC_VIOLENCE",
      "VIOLENCE",
      "DRUGS",
      "ALCOHOL_TOBACCO",
      "GAMBLING",
      "WEAPONS",
      "DANGEROUS_CHALLENGE",
      "ANONYMOUS_CHAT",
      "SCAM_FRAUD",
      "MALWARE_PHISHING",
      "STRONG_LANGUAGE",
      "AGE_INAPPROPRIATE",
      "PARENT_CUSTOM_RULE",
      "UNKNOWN",
    ]);
    expect(CONTENT_RISK_CATEGORY_ALIASES).toMatchObject({
      SELF_HARM: "SELF_HARM_SUICIDE",
      ADULT_PORNOGRAPHY: "ADULT_NUDITY",
      MALWARE: "MALWARE_PHISHING",
    });
  });

  it("keeps Kotlin content-risk enums aligned with the shared artifact", () => {
    expect(kotlinEnumValues("SignalSource")).toEqual(contentRiskContract.signal_sources);
    expect(kotlinEnumValues("ContentAction")).toEqual(contentRiskContract.actions);
    expect(kotlinEnumValues("ContentRiskSeverity")).toEqual(contentRiskContract.severities);
    expect(kotlinEnumValues("ContentRiskCategory")).toEqual(contentRiskContract.categories);
    expect(kotlinEnumValues("ContentRiskReasonCode")).toEqual(contentRiskContract.reason_codes);
    expect(kotlinEnumValues("ContentCapabilityLevel")).toEqual(
      contentRiskContract.capability_levels,
    );
  });
});
