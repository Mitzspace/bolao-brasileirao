module.exports = {
  content: ['./templates/**/*.html'],
  darkMode: 'class',
  theme: { extend: {
    fontFamily: { display: ['"Barlow Condensed"', 'sans-serif'], sans: ['"Manrope"', 'sans-serif'] },
    colors: {
      background: '#121a16', foreground: '#f3f6f4',
      card: {DEFAULT:'#192620', foreground:'#f3f6f4'},
      popover: {DEFAULT:'#192620', foreground:'#f3f6f4'},
      primary: {DEFAULT:'#22c55e', foreground:'#0c2415'},
      secondary: {DEFAULT:'#22332a', foreground:'#e4ece7'},
      muted: {DEFAULT:'#1d2b24', foreground:'#9ab3a5'},
      accent: {DEFAULT:'#f59e0b', foreground:'#171f1a'},
      destructive: {DEFAULT:'#ef4444', foreground:'#ffffff'},
      border:'#293d33', input:'#293d33', ring:'#22c55e'
    },
    boxShadow: {glow:'0 10px 30px -10px rgba(34,197,94,.45)'}
  }}
};
