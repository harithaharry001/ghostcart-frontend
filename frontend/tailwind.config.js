/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // AWS-Inspired Professional color scheme
        primary: {
          DEFAULT: '#FF9900', // AWS Orange
          light: '#FFAC31',
          dark: '#EC7211',
          50: '#FFF8F0',
          100: '#FFEFD6',
        },
        secondary: {
          DEFAULT: '#232F3E', // AWS Dark Navy
          light: '#37475A',
          dark: '#161E2D',
          50: '#F5F6F7',
          100: '#E8EAED',
        },
        accent: {
          DEFAULT: '#146EB4', // AWS Blue
          light: '#1F8DD6',
          dark: '#0F5B94',
          cyan: '#00A8E1',
          teal: '#16191F',
        },
        success: {
          DEFAULT: '#1D8102', // Professional Green
          light: '#2EA043',
          dark: '#146B00',
          50: '#F0FDF4',
          100: '#DCFCE7',
        },
        warning: {
          DEFAULT: '#F59E0B', // Amber
          light: '#FBBF24',
          dark: '#D97706',
          50: '#FFFBEB',
          100: '#FEF3C7',
        },
        error: {
          DEFAULT: '#D13212', // AWS Red
          light: '#E74C3C',
          dark: '#A82A0C',
          50: '#FEF2F2',
          100: '#FEE2E2',
        },
        dark: {
          DEFAULT: '#232F3E', // AWS Dark
          light: '#37475A',
          lighter: '#4A5F7F',
          50: '#F8FAFC',
          100: '#F1F5F9',
        },
        neutral: {
          50: '#FAFAFA',
          100: '#F5F5F5',
          200: '#E5E5E5',
          300: '#D4D4D4',
          400: '#A3A3A3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
        }
      },
      fontFamily: {
        sans: ['Inter', 'Amazon Ember', 'Helvetica Neue', 'sans-serif'],
        display: ['Inter', 'Amazon Ember', 'sans-serif'],
        mono: ['JetBrains Mono', 'Courier New', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'pulse-subtle': 'pulseSubtle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
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
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.8' },
        },
      },
      boxShadow: {
        'soft': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        'medium': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'large': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'xl': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        'aws': '0 2px 4px 0 rgba(0,28,36,.5)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
