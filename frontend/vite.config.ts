import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [react()],
  base: '/static/interface/',
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  build: {
    outDir: '../static/interface',
    emptyOutDir: true,
    manifest: true,
    rollupOptions: { input: 'src/main.tsx' },
  },
});
