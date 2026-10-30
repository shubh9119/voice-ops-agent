import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f7ff',
          100: '#e0efff',
          200: '#b9dfff',
          300: '#7cc7ff',
          400: '#36abff',
          500: '#0c8fff',
          600: '#006fea',
          700: '#0058bd',
          800: '#004a9b',
          900: '#003f80',
          950: '#002855',
        },
      },
    },
  },
  plugins: [],
}
export default config
