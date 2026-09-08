/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./app/**/*.{js,ts,jsx,tsx}",
    "../../libs/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        // Enforce monospace everywhere for the techy command center vibe
        sans: ['"JetBrains Mono"', '"Fira Code"', 'monospace'], 
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      colors: {
        'hud-bg': 'rgba(10, 15, 25, 0.85)',
        'hud-border': '#1e3a8a', // Dark blue border
        'hud-glow': '#3b82f6', // Neon blue glow
        'neon-blue': '#00f0ff', // Cyberpunk bright blue
        'warning-yellow': '#fbbf24', // Yellow for highlights
      }
    },
  },
  // Disable border radius globally to enforce the 0% rounded edges rule
  corePlugins: {
    borderRadius: false,
  },
  plugins: [],
}
