/**
 * MDx Vision Theme
 * Optimized for Vuzix smart glasses and mobile devices
 */

export const colors = {
  // Primary brand colors
  primary: '#00D9A5',      // MDx green
  primaryDark: '#00B389',
  
  // Background colors (dark theme for OLED/Vuzix)
  background: '#0A1628',
  surface: '#1A2744',
  surfaceLight: '#243553',
  
  // Text colors
  text: '#FFFFFF',
  textSecondary: '#8892A6',
  textMuted: '#5C6577',
  
  // Status colors
  success: '#00D9A5',
  warning: '#FFB800',
  error: '#FF4757',
  info: '#3B82F6',
  
  // Border
  border: '#2D3B55',
  
  // Specific UI elements
  cardBackground: '#1A2744',
  inputBackground: '#0F1D32',
  
  // Gradients
  gradientStart: '#00D9A5',
  gradientEnd: '#00B389',
};

export const typography = {
  h1: {
    fontSize: 28,
    fontWeight: '700' as const,
    lineHeight: 36,
  },
  h2: {
    fontSize: 22,
    fontWeight: '600' as const,
    lineHeight: 28,
  },
  h3: {
    fontSize: 18,
    fontWeight: '600' as const,
    lineHeight: 24,
  },
  body: {
    fontSize: 16,
    fontWeight: '400' as const,
    lineHeight: 24,
  },
  bodySmall: {
    fontSize: 14,
    fontWeight: '400' as const,
    lineHeight: 20,
  },
  caption: {
    fontSize: 12,
    fontWeight: '500' as const,
    lineHeight: 16,
  },
  button: {
    fontSize: 16,
    fontWeight: '600' as const,
    lineHeight: 24,
  },
  // Vuzix-specific (larger for AR display)
  vuzixTitle: {
    fontSize: 20,
    fontWeight: '700' as const,
    lineHeight: 28,
  },
  vuzixBody: {
    fontSize: 18,
    fontWeight: '500' as const,
    lineHeight: 26,
  },
  vuzixCaption: {
    fontSize: 16,
    fontWeight: '400' as const,
    lineHeight: 22,
  },
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const borderRadius = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
};

export const shadows = {
  small: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
    elevation: 3,
  },
  medium: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.27,
    shadowRadius: 4.65,
    elevation: 6,
  },
  large: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.37,
    shadowRadius: 7.49,
    elevation: 12,
  },
};
