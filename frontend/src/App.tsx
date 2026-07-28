/**
 * 应用根组件
 *
 * 配置 React Router：
 *   /         → 落地页（Hero + 开始测试）
 *   /chat     → 对话页（聊天窗口 + 侧栏雷达/进度）
 *   /result   → 结果页（人物匹配卡片 + 双雷达 + 详细字段）
 *   *         → 重定向到 /
 *
 * 用 BrowserRouter（Vite dev 和生产 Nginx 都用相对路径，无需 hash）。
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Landing from "./pages/Landing";
import Chat from "./pages/Chat";
import Result from "./pages/Result";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/result" element={<Result />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
