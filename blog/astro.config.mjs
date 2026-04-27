// @ts-check
import { defineConfig } from "astro/config";
import { urlToVidTag } from "./src/utils";

import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  site: "https://example.com",

  markdown: {
    remarkPlugins: [urlToVidTag],
  },

  vite: {
    plugins: [tailwindcss()],
  },
});