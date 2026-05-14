/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'lakeshore-blue': '#1e40af',
        'lakeshore-teal': '#14b8a6',
      }
    },
  },
  plugins: [],
}