import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  root: path.resolve(__dirname, "pages-entry"),
  base: "./",
  publicDir: path.resolve(__dirname, "public"),
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname) } },
  build: {
    outDir: path.resolve(__dirname, "dist-pages"),
    emptyOutDir: true,
  },
});
