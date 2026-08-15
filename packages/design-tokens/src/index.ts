export const colors = {
  light: {
    background: "#F7F8FA",
    surface: "#FFFFFF",
    elevatedSurface: "#FFFFFF",
    text: "#18202A",
    secondaryText: "#5D6875",
    border: "#DCE1E7",
    primary: "#2457D6",
    primaryText: "#FFFFFF",
    danger: "#B3261E",
    warning: "#996000",
    success: "#1B7F4B",
  },
  dark: {
    background: "#111418",
    surface: "#1A1F25",
    elevatedSurface: "#242A32",
    text: "#F3F5F7",
    secondaryText: "#B4BDC8",
    border: "#39424D",
    primary: "#9BB7FF",
    primaryText: "#101A33",
    danger: "#FFB4AB",
    warning: "#F6C667",
    success: "#8ED5AA",
  },
} as const;

export const protectionStateColors = {
  PROTECTED: { light: "#1B7F4B", dark: "#8ED5AA" },
  DEGRADED: { light: "#996000", dark: "#F6C667" },
  UNKNOWN: { light: "#5D6875", dark: "#B4BDC8" },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

export const radii = {
  sm: 8,
  md: 14,
  lg: 22,
  pill: 999,
} as const;

export const typography = {
  title: { fontSize: 32, lineHeight: 40, fontWeight: "700" as const },
  heading: { fontSize: 24, lineHeight: 32, fontWeight: "700" as const },
  body: { fontSize: 17, lineHeight: 25, fontWeight: "400" as const },
  bodyEmphasis: { fontSize: 17, lineHeight: 25, fontWeight: "600" as const },
  label: { fontSize: 15, lineHeight: 20, fontWeight: "600" as const },
  caption: { fontSize: 13, lineHeight: 18, fontWeight: "400" as const },
} as const;

export const motion = {
  fast: 150,
  standard: 250,
  deliberate: 400,
} as const;

export const touchTarget = {
  minimum: 44,
} as const;
