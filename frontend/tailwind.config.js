/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // User-confirmed clean color palette
        'app-bg': '#000000',
        'surface': '#1a1a1a',
        'surface-hover': '#222222',
        'border': '#2a2a2a',
        'border-hover': '#3a3a3a',
        'accent-cyan': '#c2f4ff',
        'accent-purple': '#c6c0ff',
        'accent-mint': '#b1ffc2',
        'text-primary': '#ffffff',
        'text-secondary': '#808080',
        'text-tertiary': '#4a4a4a',
        'profit': '#b1ffc2',
        'loss': '#f87171',
        // Legacy compatibility
        terminal: {
          bg: '#000000',
          surface: '#1a1a1a',
          border: '#2a2a2a',
          'text-primary': '#ffffff',
          'text-secondary': '#808080',
        },
      },
      fontFamily: {
        sans: ['Banana Grotesk', 'Inter', 'system-ui', 'sans-serif'],
        display: ['Banana Grotesk', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['Azeret Mono', 'JetBrains Mono', 'Consolas', 'monospace'],
      },
      fontFeatureSettings: {
        'tabular': '"tnum"',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.4s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
