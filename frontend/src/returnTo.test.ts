import { describe, expect, it } from "vitest";

import { normalizeReturnTo } from "./returnTo";

const ORIGIN = "https://radar.blueashdigital.tech";

describe("normalizeReturnTo", () => {
  it.each([
    ["/", "https://radar.blueashdigital.tech/"],
    ["/jobs", "https://radar.blueashdigital.tech/jobs"],
    ["/jobs?tab=active", "https://radar.blueashdigital.tech/jobs?tab=active"],
    ["https://radar.blueashdigital.tech/jobs", "https://radar.blueashdigital.tech/jobs"],
  ])("accepts an exact Radar UI destination", (value, expected) => {
    expect(normalizeReturnTo(value, ORIGIN)).toBe(expected);
  });

  it.each([
    "https://evil.example.com",
    "http://radar.blueashdigital.tech/",
    "https://radar.blueashdigital.tech.evil.example.com/",
    "https://user@radar.blueashdigital.tech/",
    "//radar.blueashdigital.tech/",
    "javascript:alert(1)",
    "jobs",
    "/api",
    "/api/auth/start",
    "/x/../api/auth/start",
    "/%2e%2e/api",
    "/%252e%252e/api",
    "/jobs%2f%2fevil.example.com",
    "/jobs\\@evil.example.com",
    "https%3A%2F%2Fevil.example.com",
    "https://[::1",
  ])("rejects unsafe, API, or non-canonical destinations", (value) => {
    expect(normalizeReturnTo(value, ORIGIN)).toBeNull();
  });
});
