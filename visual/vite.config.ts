import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";
import { fileURLToPath } from "node:url";

// Shared data lives one level up in /data, so both Duncan's code and this app use the same files.
const dataDir = fileURLToPath(new URL("../data", import.meta.url));

export default defineConfig({
  // viteSingleFile bundles everything (code + data) into dist/index.html,
  // so the built page opens offline by double-clicking it.
  plugins: [react(), viteSingleFile()],
  base: "./",
  resolve: { alias: { "@data": dataDir } },
  server: { fs: { allow: [".", dataDir] } },
});
