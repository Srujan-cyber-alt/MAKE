/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        make: {
          bg: '#0a0a0f',
          surface: '#111118',
          surfaceHover: '#1a1a24',
          border: '#2a2a3a',
          accent: '#6c5ce7',
          accentHover: '#5a4bd1',
          text: '#e2e2f0',
          muted: '#8888a0',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
