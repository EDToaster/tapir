import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  build:{rollupOptions:{input:{
    product:fileURLToPath(new URL('./index.html',import.meta.url)),
    studies:fileURLToPath(new URL('./study.html',import.meta.url))
  }}}
});
