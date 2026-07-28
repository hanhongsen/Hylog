import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 前端 dev server 跑在 5173（Vite 默认）
    port: 5173,
    // 把所有 /api/* 和 /images/* 请求转发到后端 FastAPI（默认 127.0.0.1:8000）
    // 这样前端代码可以用相对路径 fetch("/api/...")，避免 CORS 和硬编码 host
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/images": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
