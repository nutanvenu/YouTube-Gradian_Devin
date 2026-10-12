const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;

export const PLAY_GATE_SCRIPT = `
(function () {
  if (window.__guardianGate) return;
  window.__guardianGate = true;
  window.__guardianHold = true;
  window.__guardianAllowed = {};
  var reported = false;
  function currentId() {
    var match = /[?&]v=([A-Za-z0-9_-]{11})/.exec(location.search)
      || /\\/(?:shorts|live|embed)\\/([A-Za-z0-9_-]{11})/.exec(location.pathname)
      || (/(^|\\.)youtu\\.be$/.test(location.hostname) ? /^\\/([A-Za-z0-9_-]{11})/.exec(location.pathname) : null);
    return match ? match[1] : null;
  }
  function permitted() {
    var id = currentId();
    return id && !window.__guardianHold && !(window.__guardianSettings || {}).youtube_paused
      && window.__guardianAllowed[id] > Date.now();
  }
  document.addEventListener("play", function (event) {
    if (!permitted() && event.target && event.target.pause) event.target.pause();
  }, true);
  setInterval(function () {
    if (permitted()) { reported = false; return; }
    document.querySelectorAll("video").forEach(function (video) { if (!video.paused) video.pause(); });
    if (currentId() && !reported && !window.__guardianHold) {
      reported = true;
      window.__guardianHold = true;
      window.ReactNativeWebView.postMessage(JSON.stringify({ type: "lease-expired" }));
    }
  }, 100);
})();
true;
`;

export function videoIdFromUrl(href: string): string | null {
  let url: URL;
  try {
    url = new URL(href);
  } catch {
    return null;
  }
  const host = url.hostname.toLowerCase();
  if (host === "youtu.be" || host.endsWith(".youtu.be")) return matchId(url.pathname.slice(1));
  if (host !== "youtube.com" && !host.endsWith(".youtube.com")) return null;
  if (url.pathname === "/watch") return matchId(url.searchParams.get("v"));
  const shorts = /^\/(shorts|embed|live)\/([^/?#]+)/.exec(url.pathname);
  return shorts ? matchId(shorts[2]) : null;
}

function matchId(value: string | null | undefined): string | null {
  return value && VIDEO_ID.test(value) ? value : null;
}

const NAVIGABLE_HOSTS = ["youtube.com", "youtu.be", "accounts.google.com", "consent.google.com"];

export function isAllowedYouTubeNavigation(href: string): boolean {
  if (href === "about:blank") return true;
  let url: URL;
  try {
    url = new URL(href);
  } catch {
    return false;
  }
  if (url.protocol !== "https:") return false;
  const host = url.hostname.toLowerCase();
  return NAVIGABLE_HOSTS.some((allowed) => host === allowed || host.endsWith(`.${allowed}`));
}
