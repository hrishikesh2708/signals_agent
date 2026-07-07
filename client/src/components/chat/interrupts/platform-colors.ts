export const PLATFORM_COLORS: Record<string, string> = {
  meta_capi:      "#1877F2",
  google_offline: "#EA4335",
  google_dm:      "#FBBC04",
  tiktok:         "#010101",
  snapchat:       "#FFFC00",
  linkedin:       "#0A66C2",
  twitter:        "#1DA1F2",
  bing:           "#008373",
};

export const SOURCE_FIELD_SELECT_CLASS =
  "h-9 flex-1 min-w-0 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 text-sm text-[var(--foreground)] cursor-pointer focus:outline-none focus:ring-1 focus:ring-[var(--primary)] transition-colors";

export const CHANNEL_AVATAR_COLORS: Record<string, string> = {
  meta:           "#1877F2",
  meta_capi:      "#1877F2",
  google:         "#EA4335",
  google_offline: "#EA4335",
  google_dm:      "#FBBC04",
  tiktok:         "#010101",
  snapchat:       "#FFFC00",
  linkedin:       "#0A66C2",
  twitter:        "#1DA1F2",
  bing:           "#008373",
};

// Slugs that use mock connect (either no real creds, or redirect URI not yet registered)
export const MOCK_ONLY_SLUGS = new Set([
  "meta_capi", "meta",
  "google_ads", "google_offline", "google_offline_conversions", "google_customer_match", "google_dm",
  "tiktok", "snapchat", "linkedin", "twitter", "bing",
]);

// Slugs that need extra metadata collected before mock-connecting
export const META_SLUGS = new Set(["meta_capi", "meta"]);
