/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: '#FAFAF8',
          subtle: '#F4F4F0',
          dark: '#141413',
        },
        surface: {
          DEFAULT: '#FFFFFF',
          muted: '#F8F8F5',
          border: '#E7E7E1',
          hover: '#F1F1EB',
        },
        ink: {
          primary: '#141413',
          secondary: '#555450',
          muted: '#7E7D77',
          faint: '#A6A59E',
        },
        accent: {
          blue: '#1D4ED8',
          'blue-subtle': '#EFF6FF',
          'blue-border': '#BFDBFE',
          peach: '#F97316',
          'peach-subtle': '#FFF7ED',
          'peach-border': '#FED7AA',
          emerald: '#059669',
          'emerald-subtle': '#ECFDF5',
        }
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.03)',
        floating: '0 10px 30px -10px rgba(0, 0, 0, 0.07), 0 4px 6px -2px rgba(0, 0, 0, 0.03)',
        preview: '0 20px 40px -15px rgba(20, 20, 19, 0.08), 0 0 0 1px rgba(20, 20, 19, 0.05)',
      },
      letterSpacing: {
        tightest: '-0.035em',
        tighter: '-0.025em',
        tight: '-0.015em',
      }
    },
  },
  plugins: [],
}
