import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite ejecuta React durante el desarrollo y genera la versión final con npm run build.
export default defineConfig({ plugins: [react()] });
