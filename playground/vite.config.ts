import { defineConfig } from "vite";

export default defineConfig({
  base: "/lsp-python-types/",
  build: {
    target: "es2022",
    chunkSizeWarningLimit: 4000, // Monaco editor is large
  },
});
