/**
 * Google Analytics (GA4), loaded only after explicit cookie consent.
 *
 * gtag is never injected until the user opts in, so no analytics cookies are
 * set for visitors who have not consented. Consent choice is persisted in
 * localStorage.
 */

const GA_ID = import.meta.env.VITE_GA_MEASUREMENT_ID;
const CONSENT_KEY = "analytics-consent";

type ConsentValue = "granted" | "denied";

let loaded = false;

export function analyticsAvailable(): boolean {
  return Boolean(GA_ID);
}

export function getStoredConsent(): ConsentValue | null {
  try {
    const value = localStorage.getItem(CONSENT_KEY);
    return value === "granted" || value === "denied" ? value : null;
  } catch {
    return null;
  }
}

function storeConsent(value: ConsentValue): void {
  try {
    localStorage.setItem(CONSENT_KEY, value);
  } catch {
    // Ignore storage failures (private mode, etc.) — consent just won't persist.
  }
}

function loadGtag(): void {
  if (loaded || !GA_ID) return;
  loaded = true;

  const script = document.createElement("script");
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
  document.head.appendChild(script);

  window.dataLayer = window.dataLayer || [];
  // gtag MUST push the `arguments` object itself, not a rest-param array.
  // GA4's gtag.js only processes command pushes that are Arguments objects;
  // a plain array is silently ignored (no /g/collect hits fire).
  window.gtag = function gtag() {
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer.push(arguments);
  };
  window.gtag("js", new Date());
  // We control page_view manually to support client-side routing.
  window.gtag("config", GA_ID, { send_page_view: false });
}

/** Load analytics if the user has already granted consent in a previous visit. */
export function initAnalytics(): void {
  if (!GA_ID) return;
  if (getStoredConsent() === "granted") {
    loadGtag();
  }
}

export function grantConsent(): void {
  storeConsent("granted");
  loadGtag();
  trackPageView(window.location.pathname + window.location.search);
}

export function denyConsent(): void {
  storeConsent("denied");
}

export function trackPageView(path: string): void {
  if (!loaded || !window.gtag || !GA_ID) return;
  window.gtag("event", "page_view", { page_path: path });
}
