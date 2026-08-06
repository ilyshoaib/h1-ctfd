const { resolve } = require("path");
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import copy from "rollup-plugin-copy";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // In development we emit stable (non-hashed) filenames so the live Vite
  // watcher overwrites assets in place. This keeps CTFd's cached manifest
  // valid across rebuilds — edit + hard-refresh is all that's needed.
  // Production keeps content hashes for cache-busting.
  const dev = mode === "development";
  const entryNames = dev ? "assets/[name].js" : "assets/[name].[hash].js";
  const assetNames = dev ? "assets/[name].[ext]" : "assets/[name].[hash].[ext]";

  return {
  plugins: [vue()],
  resolve: {
    alias: {
      "~": resolve(__dirname, "./node_modules/"),
    },
  },
  build: {
    manifest: true,
    outDir: "static",
    rollupOptions: {
      plugins: [
        copy({
          targets: [
            // https://github.com/vitejs/vite/issues/1618#issuecomment-764579557
            {
              src: "./node_modules/@fortawesome/fontawesome-free/webfonts/**/*",
              dest: "static/webfonts",
            },
            {
              src: "./node_modules/@fontsource/lato/files/**/*400*-normal*",
              dest: "static/webfonts",
            },
            {
              src: "./node_modules/@fontsource/lato/files/**/*700*-normal*",
              dest: "static/webfonts",
            },
            {
              src: "./node_modules/@fontsource/raleway/files/**/*400*-normal*",
              dest: "static/webfonts",
            },
            {
              src: "./assets/img/**",
              dest: "static/img",
            },
            {
              src: "./assets/sounds/**",
              dest: "static/sounds",
            },
          ],
          hook: "writeBundle",
        }),
      ],
      output: {
        entryFileNames: entryNames,
        chunkFileNames: entryNames,
        assetFileNames: assetNames,
        manualChunks: {
          echarts: ["echarts", "zrender"],
        },
      },
      input: {
        index: resolve(__dirname, "assets/js/index.js"),
        page: resolve(__dirname, "assets/js/page.js"),
        setup: resolve(__dirname, "assets/js/setup.js"),
        settings: resolve(__dirname, "assets/js/settings.js"),
        challenges: resolve(__dirname, "assets/js/challenges.js"),
        scoreboard: resolve(__dirname, "assets/js/scoreboard.js"),
        notifications: resolve(__dirname, "assets/js/notifications.js"),
        teams_public: resolve(__dirname, "assets/js/teams/public.js"),
        teams_private: resolve(__dirname, "assets/js/teams/private.js"),
        teams_list: resolve(__dirname, "assets/js/teams/list.js"),
        users_public: resolve(__dirname, "assets/js/users/public.js"),
        users_private: resolve(__dirname, "assets/js/users/private.js"),
        users_list: resolve(__dirname, "assets/js/users/list.js"),
        main: resolve(__dirname, "assets/scss/main.scss"),
        color_mode_switcher: resolve(__dirname, "assets/js/color_mode_switcher.js"),
      },
    },
  },
  };
});
