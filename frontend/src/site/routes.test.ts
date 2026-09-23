import { describe, expect, it } from "vitest";
import { navigationAfterSessionCheck, normalizePath, resolveRoute, sessionPresentation, shouldRedirectHomeToSignIn, signInPath } from "./routes";

describe("public site routes", () => {
  it("normalizes a trailing slash", () => {
    expect(normalizePath("/products/blue-ash-reel/")).toBe("/products/blue-ash-reel");
    expect(normalizePath("/")).toBe("/");
  });

  it("keeps the corporate homepage separate from the portal", () => {
    expect(resolveRoute("/")).toEqual({ kind: "marketing", page: "home", focus: null });
    expect(resolveRoute("/portal")).toEqual({ kind: "portal" });
  });

  it("maps company sections and the first product", () => {
    expect(resolveRoute("/products")).toEqual({ kind: "marketing", page: "home", focus: "products" });
    expect(resolveRoute("/about")).toEqual({ kind: "marketing", page: "home", focus: "about" });
    expect(resolveRoute("/development")).toEqual({ kind: "marketing", page: "home", focus: "building" });
    expect(resolveRoute("/products/blue-ash-reel")).toEqual({ kind: "marketing", page: "reel", focus: null });
    expect(resolveRoute("/support")).toEqual({ kind: "marketing", page: "support", focus: null });
    expect(resolveRoute("/privacy")).toEqual({ kind: "marketing", page: "privacy", focus: null });
    expect(resolveRoute("/terms")).toEqual({ kind: "marketing", page: "terms", focus: null });
    expect(resolveRoute("/privacy/")).toEqual({ kind: "marketing", page: "privacy", focus: null });
  });

  it("preserves the existing authentication paths", () => {
    expect(resolveRoute("/signin")).toEqual({ kind: "auth", page: "signin" });
    expect(resolveRoute("/forgot-password")).toEqual({ kind: "auth", page: "forgot-password" });
    expect(resolveRoute("/reset-password")).toEqual({ kind: "auth", page: "reset-password" });
  });

  it("sends an unknown path to the corporate not-found page", () => {
    expect(resolveRoute("/OpportunityRadar")).toEqual({ kind: "marketing", page: "not-found", focus: null });
  });

  it("moves a homepage returnTo link onto the sign-in route", () => {
    expect(shouldRedirectHomeToSignIn("/", "?returnTo=https%3A%2F%2Fradar.blueashdigital.tech%2F")).toBe(true);
    expect(signInPath("?returnTo=https%3A%2F%2Fradar.blueashdigital.tech%2F")).toBe(
      "/signin?returnTo=https%3A%2F%2Fradar.blueashdigital.tech%2F",
    );
    expect(signInPath("")).toBe("/signin");
    expect(shouldRedirectHomeToSignIn("/signin", "?returnTo=https%3A%2F%2Fradar.blueashdigital.tech%2F")).toBe(false);
  });

  it("keeps session redirects on the existing authentication contract", () => {
    const radar = "https://radar.blueashdigital.tech/jobs";
    expect(navigationAfterSessionCheck({
      pathname: "/",
      search: `?returnTo=${encodeURIComponent(radar)}`,
      authenticated: true,
      returnTo: radar,
    })).toBe(radar);
    expect(navigationAfterSessionCheck({
      pathname: "/",
      search: "?returnTo=https%3A%2F%2Fevil.example",
      authenticated: false,
      returnTo: null,
    })).toBe("/signin?returnTo=https%3A%2F%2Fevil.example");
    expect(navigationAfterSessionCheck({
      pathname: "/signin",
      search: "?returnTo=https%3A%2F%2Fevil.example",
      authenticated: false,
      returnTo: null,
    })).toBeNull();
    expect(navigationAfterSessionCheck({
      pathname: "/portal",
      search: "",
      authenticated: false,
      returnTo: null,
    })).toBe("/signin");
    expect(navigationAfterSessionCheck({
      pathname: "/signin",
      search: "",
      authenticated: true,
      returnTo: null,
    })).toBe("/portal");
    expect(navigationAfterSessionCheck({
      pathname: "/forgot-password",
      search: "",
      authenticated: true,
      returnTo: null,
    })).toBe("/portal");
    expect(navigationAfterSessionCheck({
      pathname: "/reset-password",
      search: "?token=abc",
      authenticated: true,
      returnTo: null,
    })).toBeNull();
    expect(navigationAfterSessionCheck({
      pathname: "/",
      search: "",
      authenticated: false,
      returnTo: null,
    })).toBeNull();
    expect(navigationAfterSessionCheck({
      pathname: "/",
      search: "",
      authenticated: true,
      returnTo: null,
    })).toBeNull();
  });

  it("shows sign-in immediately and does not probe public pages", () => {
    expect(sessionPresentation("/signin", "")).toBe("immediate");
    expect(sessionPresentation("/forgot-password", "")).toBe("immediate");
    expect(sessionPresentation("/reset-password", "?token=abc")).toBe("immediate");
    expect(sessionPresentation("/", "")).toBe("public");
    expect(sessionPresentation("/products", "")).toBe("public");
    expect(sessionPresentation("/products/blue-ash-reel", "")).toBe("public");
    expect(sessionPresentation("/about", "")).toBe("public");
    expect(sessionPresentation("/development", "")).toBe("public");
    expect(sessionPresentation("/support", "")).toBe("public");
    expect(sessionPresentation("/privacy", "")).toBe("public");
    expect(sessionPresentation("/terms", "")).toBe("public");
    expect(sessionPresentation("/missing", "")).toBe("public");
    expect(sessionPresentation("/portal", "")).toBe("gated");
    expect(sessionPresentation("/", "?returnTo=https%3A%2F%2Fradar.blueashdigital.tech%2Fjobs")).toBe("gated");
  });
});
