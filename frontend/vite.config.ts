// frontend/vite.config.ts

import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load .env files based on the mode (development, production)
  // located in the project root (process.cwd()). '' means load all variables,
  // not just those prefixed with VITE_
  const env = loadEnv(mode, process.cwd(), '');

  // Determine the API proxy target:
  // 1. Use VITE_API_PROXY_TARGET if it's set (e.g., in docker-compose.yml)
  // 2. Default to 'http://localhost:8000' for local development outside Docker
  const proxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000';

  // Optional: Log the target being used for easier debugging
  console.log(`[vite.config.ts] Mode: ${mode}`);
  console.log(`[vite.config.ts] VITE_API_PROXY_TARGET from env: ${env.VITE_API_PROXY_TARGET}`);
  console.log(`[vite.config.ts] Using API proxy target: ${proxyTarget}`);

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      // Bind to 0.0.0.0 to allow access from outside the container (if needed)
      // and ensures it works within Docker network
      host: '0.0.0.0',
      // Default Vite port, but can be explicit
      port: 3000,
      // HMR (Hot Module Replacement) configuration can sometimes be needed
      // in complex Docker setups, uncomment if HMR breaks.
      // hmr: {
      //   clientPort: 3000,
      // },
      proxy: {
        '/api': {
          target: proxyTarget, // Use the dynamically determined target
          changeOrigin: true, // Recommended for virtual hosted sites
          rewrite: (path) => path.replace(/^\/api/, ''), // Remove /api prefix
        },
      },
    },
  }
})