/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#fdf2f8',
          100: '#fce7f3',
          200: '#fbcfe8',
          300: '#f9a8d4',
          400: '#f472b6',
          500: '#ec4899',
          600: '#db2777',
          700: '#be185d',
          800: '#9d174d',
          900: '#831843',
        },
        sidebar: {
          DEFAULT: '#1a1a2e',
          light: '#252542',
          accent: '#3d3d5c',
        },
        accent: {
          coral: '#ff6b6b',
          peach: '#ffa07a',
          mint: '#98d8c8',
          lavender: '#b8b8ff',
        }
      },
      backgroundImage: {
        'gradient-card': 'linear-gradient(135deg, #ff6b9d 0%, #ffa07a 50%, #ffd93d 100%)',
        'gradient-pink': 'linear-gradient(135deg, #ff6b9d 0%, #c44569 100%)',
        'gradient-orange': 'linear-gradient(135deg, #ffa07a 0%, #ff6b6b 100%)',
        'gradient-purple': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'gradient-blue': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
      },
      boxShadow: {
        'card': '0 4px 20px -2px rgba(0, 0, 0, 0.06)',
        'card-hover': '0 8px 30px -4px rgba(0, 0, 0, 0.1)',
        'glow-pink': '0 10px 40px -10px rgba(236, 72, 153, 0.4)',
        'glow-orange': '0 10px 40px -10px rgba(255, 107, 107, 0.4)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
