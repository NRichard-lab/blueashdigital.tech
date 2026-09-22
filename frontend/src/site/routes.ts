export type MarketingPage = "home" | "reel" | "support" | "privacy" | "terms" | "not-found";
export type AuthPage = "signin" | "forgot-password" | "reset-password";

export type SiteRoute =
  | { kind: "marketing"; page: MarketingPage; focus: string | null }
  | { kind: "auth"; page: AuthPage }
  | { kind: "portal" };

export function normalizePath(pathname: string): string {
  const path = pathname.split("?")[0].split("#")[0] || "/";
  if (path.length > 1 && path.endsWith("/")) return path.slice(0, -1);
  return path;
}

export function resolveRoute(pathname: string): SiteRoute {
  switch (normalizePath(pathname)) {
    case "/":
      return { kind: "marketing", page: "home", focus: null };
    case "/products":
      return { kind: "marketing", page: "home", focus: "products" };
    case "/about":
      return { kind: "marketing", page: "home", focus: "about" };
    case "/development":
      return { kind: "marketing", page: "home", focus: "building" };
    case "/products/blue-ash-reel":
      return { kind: "marketing", page: "reel", focus: null };
    case "/support":
      return { kind: "marketing", page: "support", focus: null };
    case "/privacy":
      return { kind: "marketing", page: "privacy", focus: null };
    case "/terms":
      return { kind: "marketing", page: "terms", focus: null };
    case "/signin":
      return { kind: "auth", page: "signin" };
    case "/forgot-password":
      return { kind: "auth", page: "forgot-password" };
    case "/reset-password":
      return { kind: "auth", page: "reset-password" };
    case "/portal":
      return { kind: "portal" };
    default:
      return { kind: "marketing", page: "not-found", focus: null };
  }
}

export function signInPath(search: string): string {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  if (!params.get("returnTo")) return "/signin";
  return `/signin?${params.toString()}`;
}

export function shouldRedirectHomeToSignIn(pathname: string, search: string): boolean {
  if (normalizePath(pathname) !== "/") return false;
  return new URLSearchParams(search.startsWith("?") ? search.slice(1) : search).has("returnTo");
}

export function navigationAfterSessionCheck(input: {
  pathname: string;
  search: string;
  authenticated: boolean;
  returnTo: string | null;
}): string | null {
  if (input.authenticated && input.returnTo) return input.returnTo;
  if (!input.authenticated && shouldRedirectHomeToSignIn(input.pathname, input.search)) {
    return signInPath(input.search);
  }
  const route = resolveRoute(input.pathname);
  if (!input.authenticated && route.kind === "portal") return "/signin";
  if (input.authenticated && route.kind === "auth" && route.page !== "reset-password") return "/portal";
  return null;
}
