import { describe, expect, it } from "vitest";

import { normalizeReturnTo } from "./returnTo";

const ORIGIN = "https://blueashdigital.tech";

describe("normalizeReturnTo", () => {
  it.each([
    ["/OpportunityRadar", "/OpportunityRadar"],
    ["/OpportunityRadar/jobs", "/OpportunityRadar/jobs"],
    ["/OpportunityRadar/utilities?tab=email", "/OpportunityRadar/utilities?tab=email"],
    ["https://blueashdigital.tech/OpportunityRadar/jobs", "/OpportunityRadar/jobs"],
  ])("accepts a canonical Opportunity Radar destination", (value, expected) => {
    expect(normalizeReturnTo(value, ORIGIN)).toBe(expected);
  });

  it.each([
    "https://evil.example.com",
    "//evil.example.com/OpportunityRadar",
    "javascript:alert(1)",
    "OpportunityRadar",
    "/opportunityradar",
    "/OpportunityRadar%2f%2fevil.example.com",
    "/OpportunityRadar\\@evil.example.com",
    "https%3A%2F%2Fevil.example.com",
  ])("rejects unsafe or non-canonical destinations", (value) => {
    expect(normalizeReturnTo(value, ORIGIN)).toBeNull();
  });
});
