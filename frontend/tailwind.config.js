/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Custom color scheme per plan.md
        primary: {
          DEFAULT: '#3B82F6', // blue
          light: '#60A5FA',
          dark: '#2563EB',
        },
        success: {
          DEFAULT: '#10B981', // green
          light: '#34D399',
          dark: '#059669',
        },
        warning: {
          DEFAULT: '#F59E0B', // orange
          light: '#FBBF24',
          dark: '#D97706',
        },
        error: {
          DEFAULT: '#EF4444', // red
          light: '#F87171',
          dark: '#DC2626',
        },
      },
      animation: {
        'pulse-slow': 'pulse 1s ease-in-out',
      },
    },
  },
  plugins: [],
}
