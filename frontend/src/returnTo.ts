const OPPORTUNITY_RADAR_PATH = "/OpportunityRadar";
const DANGEROUS_ENCODING = /%(?:00|0a|0d|2f|5c)/i;

export function normalizeReturnTo(value: string | null, siteOrigin = window.location.origin): string | null {
  if (!value) return null;
  const candidate = value.trim();
  if (!candidate || candidate.length > 2048 || /[\u0000-\u001f\\]/.test(candidate) || DANGEROUS_ENCODING.test(candidate)) return null;
  if ((!candidate.startsWith("/") && !/^https?:\/\//i.test(candidate)) || candidate.startsWith("//")) return null;
  try {
    const parsed = new URL(candidate, siteOrigin);
    if (parsed.origin !== siteOrigin || parsed.username || parsed.password) return null;
    if (parsed.pathname !== OPPORTUNITY_RADAR_PATH && !parsed.pathname.startsWith(`${OPPORTUNITY_RADAR_PATH}/`)) return null;
    return `${parsed.pathname}${parsed.search}`;
  } catch {
    return null;
  }
}
