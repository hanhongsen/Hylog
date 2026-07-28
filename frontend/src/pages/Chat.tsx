/**
 * 对话页（主战场）
 *
 * 布局：
 *   ┌──────────────────────────────────────────┐
 *   │ Header                                    │
 *   ├──────────────────────────┬───────────────┤
 *   │                          │  侧栏          │
 *   │   ChatWindow             │  · OCEAN 雷达  │
 *   │   （消息流 + 输入）        │  · 进度面板    │
 *   │                          │  · 重置按钮     │
 *   └──────────────────────────┴───────────────┘
 *
 * 移动端：侧栏折叠到底部抽屉（或隐藏，仅留消息流）。
 *
 * 进入此页面前，store 必须已有 session（Landing 已调 startSession），
 * 否则重定向回首页。
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/layout/Header";
import ChatWindow from "../components/chat/ChatWindow";
import OceanRadar from "../components/insight/OceanRadar";
import ProgressPanel from "../components/insight/ProgressPanel";
import { useSessionStore } from "../store/session";

export default function Chat() {
  const navigate = useNavigate();
  const sessionId = useSessionStore((s) => s.sessionId);
  const ocean = useSessionStore((s) => s.ocean);
  const progress = useSessionStore((s) => s.progress);
  const resetSession = useSessionStore((s) => s.resetSession);

  // 移动端侧栏显隐
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // 无 session → 回首页（直接 startSession 失败、或用户直接敲 /chat）
  useEffect(() => {
    if (!sessionId) {
      navigate("/", { replace: true });
    }
  }, [sessionId, navigate]);

  if (!sessionId) return null;

  const handleReset = () => {
    if (
      window.confirm(
        "确定要重新开始吗？当前对话记录将不会被保留。",
      )
    ) {
      resetSession();
      navigate("/", { replace: true });
    }
  };

  return (
    <div className="h-screen h-dvh flex flex-col">
      <Header
        rightSlot={
          <div className="flex items-center gap-2">
            {/* 移动端：展开侧栏 */}
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden btn-outline px-3 py-1.5 text-xs"
              aria-label="查看画像"
            >
              画像
            </button>
            <button
              onClick={handleReset}
              className="btn-outline px-3 py-1.5 text-xs"
            >
              重新开始
            </button>
          </div>
        }
      />

      {/* 主体：左聊天 + 右侧栏 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 聊天区 */}
        <main className="flex-1 min-w-0">
          <ChatWindow />
        </main>

        {/* 侧栏（桌面端） */}
        <aside className="hidden lg:flex w-80 flex-shrink-0 border-l border-cha/20 bg-xuanzhi/60">
          <SidebarContent
            ocean={ocean}
            progress={progress}
          />
        </aside>
      </div>

      {/* 移动端抽屉 */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          {/* 遮罩 */}
          <div
            className="absolute inset-0 bg-mo/40 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
          {/* 抽屉面板 */}
          <div className="relative ml-auto w-80 max-w-[85vw] h-full bg-xuanzhi border-l border-cha/30 overflow-y-auto scrollbar-ink animate-fade-up">
            <div className="flex justify-end p-3">
              <button
                onClick={() => setSidebarOpen(false)}
                className="text-mo-light hover:text-zhu text-xl leading-none"
                aria-label="关闭"
              >
                ×
              </button>
            </div>
            <SidebarContent ocean={ocean} progress={progress} />
          </div>
        </div>
      )}
    </div>
  );
}

/** 侧栏内容（桌面侧栏和移动端抽屉共用） */
function SidebarContent({
  ocean,
  progress,
}: {
  ocean: ReturnType<typeof useSessionStore.getState>["ocean"];
  progress: ReturnType<typeof useSessionStore.getState>["progress"];
}) {
  return (
    <div className="flex-1 p-5 space-y-6 overflow-y-auto scrollbar-ink">
      {/* OCEAN 雷达 */}
      <section>
        <h3 className="section-title text-base !my-3">人格画像</h3>
        <div className="card-ink p-3">
          <OceanRadar ocean={ocean} height={220} />
        </div>
        <p className="text-xs text-mo-faint mt-2 text-center">
          每一次回答，画像都会更新
        </p>
      </section>

      {/* 进度 */}
      <section>
        <h3 className="section-title text-base !my-3">对话进度</h3>
        <div className="card-ink p-4">
          <ProgressPanel progress={progress} />
        </div>
      </section>
    </div>
  );
}
