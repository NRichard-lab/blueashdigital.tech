import { afterEach, describe, expect, it, vi } from "vitest";
import { AUTH_REQUEST_TIMEOUT_MS, AUTH_UNREACHABLE_MESSAGE, SESSION_PROBE_TIMEOUT_MS, api, createAuthRequestSignal } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("auth request bounds", () => {
  it("allows a sign-in longer than the session probe and still ends a hung request", async () => {
    expect(AUTH_REQUEST_TIMEOUT_MS).toBeGreaterThan(SESSION_PROBE_TIMEOUT_MS);
    expect(AUTH_REQUEST_TIMEOUT_MS).toBeLessThanOrEqual(12000);
    const signal = createAuthRequestSignal(15);
    await new Promise((resolve) => setTimeout(resolve, 40));
    expect(signal.aborted).toBe(true);
  });

  it("reports a timed-out login as unreachable rather than bad credentials", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new DOMException("The operation was aborted.", "TimeoutError")));
    await expect(api.login("person@example.com", "not-a-real-password", null)).rejects.toThrow(AUTH_UNREACHABLE_MESSAGE);
  });

  it("keeps an invalid-credentials response distinct from a network failure", async () => {
    vi.stubGlobal("fetch", async () => new Response(JSON.stringify({ detail: "Invalid username/email or password." }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    }));
    await expect(api.login("person@example.com", "not-a-real-password", "https://radar.blueashdigital.tech/jobs")).rejects.toThrow(
      "Invalid username/email or password.",
    );
  });

  it("uses the same unreachable message for forgot-password and reset timeouts", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new DOMException("The operation was aborted.", "AbortError")));
    await expect(api.requestPasswordReset("person@example.com")).rejects.toThrow(AUTH_UNREACHABLE_MESSAGE);
    await expect(api.completePasswordReset("not-a-real-token", "not-a-real-password")).rejects.toThrow(AUTH_UNREACHABLE_MESSAGE);
    await expect(api.verifyMfa("000000")).rejects.toThrow(AUTH_UNREACHABLE_MESSAGE);
  });
});
