import { defineConfig } from "vite";

export default defineConfig({
  base: "/lsp-python-types/",
  publicDir: "wasm",
  build: {
    target: "es2022",
    chunkSizeWarningLimit: 4000, // Monaco editor is large
  },
});
