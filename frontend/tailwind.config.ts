import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Design tokens CTec
        carbon: {
          DEFAULT: '#0D0D10', // carbon black
          900: '#0D0D10',
          800: '#131318',
          700: '#1A1A21',
          600: '#24242D',
          500: '#31313C',
        },
        electric: {
          DEFAULT: '#1B4FFF', // electric blue accent
          soft: '#3D67FF',
          dim: '#1536A8',
        },
      },
      fontFamily: {
        display: ['var(--font-space-grotesk)', 'system-ui', 'sans-serif'],
        body: ['var(--font-inter-tight)', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config
