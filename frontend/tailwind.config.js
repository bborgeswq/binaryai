/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Primary background layers
        canvas: {
          DEFAULT: '#0a0b0d',
          elevated: '#111214',
          overlay: '#18191c',
        },
        // Surface colors
        surface: {
          DEFAULT: '#1c1d21',
          hover: '#232429',
          active: '#2a2b30',
          border: '#2e3035',
        },
        // Text hierarchy
        ink: {
          DEFAULT: '#f4f4f5',
          secondary: '#a1a1aa',
          tertiary: '#71717a',
          faint: '#52525b',
        },
        // Accent - Electric Teal
        accent: {
          DEFAULT: '#14b8a6',
          hover: '#0d9488',
          muted: 'rgba(20, 184, 166, 0.15)',
          glow: 'rgba(20, 184, 166, 0.4)',
        },
        // Semantic
        profit: {
          DEFAULT: '#22c55e',
          muted: 'rgba(34, 197, 94, 0.15)',
        },
        loss: {
          DEFAULT: '#ef4444',
          muted: 'rgba(239, 68, 68, 0.15)',
        },
        warning: {
          DEFAULT: '#f59e0b',
          muted: 'rgba(245, 158, 11, 0.15)',
        },
      },
      fontFamily: {
        display: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Space Grotesk', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '1rem' }],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'ticker': 'ticker 20s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(20, 184, 166, 0)' },
          '50%': { boxShadow: '0 0 20px 0 rgba(20, 184, 166, 0.3)' },
        },
        ticker: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
      },
      backgroundImage: {
        'grid-pattern': `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%232e3035' fill-opacity='0.3'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
}
