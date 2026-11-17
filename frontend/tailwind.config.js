/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        control: {
          bg: '#0A0F1D',       // Dark control room navy
          panel: '#111827',    // Card / surface navy
          border: '#1F2937',   // Slate border
          highlight: '#374151',
          accent: '#3B82F6',   // Control blue
          alert: '#EF4444',    // Fault red
          warning: '#F59E0B',  // Amber caution
          success: '#10B981',  // Safe green
          text: '#F3F4F6',
          muted: '#9CA3AF'
        }
      }
    },
  },
  plugins: [],
}
