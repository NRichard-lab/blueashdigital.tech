import { describe, expect, it } from "vitest";
import { SESSION_PROBE_TIMEOUT_MS, createSessionProbeSignal } from "./api";

describe("session probe timeout", () => {
  it("stops the session request well inside the browser connection timeout", async () => {
    expect(SESSION_PROBE_TIMEOUT_MS).toBeLessThanOrEqual(4000);
    const signal = createSessionProbeSignal(20);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(signal.aborted).toBe(true);
  });
});
