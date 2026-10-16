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
    // Duas entradas: a gestão (login) e a página pública de consulta, que não carrega o código do admin.
    rollupOptions: { input: { main: 'src/main.tsx', publico: 'src/publico/main.tsx' } },
  },
});
