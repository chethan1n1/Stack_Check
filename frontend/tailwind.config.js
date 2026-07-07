/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        neutral: {
          250: "#d4d4d8", // light-grey text/border
          350: "#a3a3a3", // secondary text
          450: "#737373", // muted description
          550: "#525252", // line ticks
          650: "#404040", // dark-grey panel
          750: "#262626", // space-grey border
          850: "#1c1c1e", // Apple space-grey bg
        },
        emerald: {
          450: "#30d158", // iOS Emerald green
        },
        amber: {
          450: "#ff9f0a", // iOS Amber orange
        },
        rose: {
          450: "#ff453a", // iOS Rose red
        },
        brand: {
          dark: "#0F172A",      
          primary: "#1E293B",   
          accent: "#3B82F6",    
          emerald: "#10B981",   
          light: "#F8FAFC",     
          border: "#E2E8F0"     
        }
      },
      fontFamily: {
        sans: ["Inter", "Roboto", "sans-serif"],
      }
    },
  },
  plugins: [],
}
