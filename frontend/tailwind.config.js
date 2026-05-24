/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        finance: {
          bg: '#0d1117',
          card: '#161b22',
          border: '#30363d',
          muted: '#8b949e',
          text: '#e6edf3',
          green: '#3fb950',
          red: '#f85149',
          amber: '#d29922',
        },
      },
      boxShadow: {
        panel: '0 18px 50px rgba(0, 0, 0, 0.28)',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
};
