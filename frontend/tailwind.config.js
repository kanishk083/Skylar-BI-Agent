/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        skylark: {
          orange:  "#E05A28",
          "orange-hover": "#C44E20",
          "orange-light": "#FDF0EA",
          "orange-muted": "#F4C9B4",
          dark:    "#1A0D06",
          sidebar: "#1E1008",
          brown:   "#3D1F0D",
          "brown-2": "#5A3020",
          cream:   "#FDF8F5",
          border:  "#EDE0D8",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      keyframes: {
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%":       { opacity: "0" },
        },
        fadeIn: {
          from: { opacity: "0", transform: "translateY(6px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        slideIn: {
          from: { opacity: "0", transform: "translateX(-8px)" },
          to:   { opacity: "1", transform: "translateX(0)" },
        },
      },
      animation: {
        blink:    "blink 1s step-end infinite",
        "fade-in":  "fadeIn 0.25s ease-out",
        "slide-in": "slideIn 0.2s ease-out",
      },
    },
  },
  plugins: [],
};
