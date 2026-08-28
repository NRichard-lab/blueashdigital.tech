const DEFAULT_RADAR_ORIGIN = "https://radar.blueashdigital.tech";
const DANGEROUS_ENCODING = /%(?:0[0-9a-f]|1[0-9a-f]|7f|25|2e|2f|5c)/i;

export function normalizeReturnTo(value: string | null, radarOrigin = import.meta.env.VITE_RADAR_PUBLIC_ORIGIN ?? DEFAULT_RADAR_ORIGIN): string | null {
  if (!value) return null;
  const candidate = value.trim();
  if (!candidate || candidate.length > 2048 || /[\u0000-\u001f\u007f\\]/.test(candidate) || DANGEROUS_ENCODING.test(candidate)) return null;
  if ((!candidate.startsWith("/") && !/^https?:\/\//i.test(candidate)) || candidate.startsWith("//")) return null;
  try {
    const expectedOrigin = new URL(radarOrigin).origin;
    const rawPath = /^https?:\/\//i.test(candidate) ? new URL(candidate).pathname : candidate.split("?", 1)[0];
    if (rawPath.split("/").some((segment) => segment === "." || segment === "..")) return null;
    const parsed = new URL(candidate, `${expectedOrigin}/`);
    if (parsed.origin !== expectedOrigin || parsed.username || parsed.password || parsed.hash) return null;
    if (parsed.pathname === "/api" || parsed.pathname.startsWith("/api/")) return null;
    return `${expectedOrigin}${parsed.pathname}${parsed.search}`;
  } catch {
    return null;
  }
}
