/**
 * 落地页 / （首页）
 *
 * 居中 Hero：印章 Logo + 大标题"嗨，老己" + slogan
 * 简介：通过对话认识自己，匹配历史名人
 * 主 CTA："开始你的旅程" → 调 POST /api/sessions，成功后跳 /chat
 */

import { useNavigate } from "react-router-dom";
import { useState } from "react";
import Seal from "../components/layout/Seal";
import { useSessionStore } from "../store/session";
import { BRAND_NAME, BRAND_SLOGAN, BRAND_TAGLINE } from "../lib/constants";

export default function Landing() {
  const navigate = useNavigate();
  const startSession = useSessionStore((s) => s.startSession);
  const loading = useSessionStore((s) => s.loading);
  const error = useSessionStore((s) => s.error);
  const [hasExistingSession] = useState(
    !!localStorage.getItem("hylog:session_id"),
  );

  const handleStart = async () => {
    // 先清掉旧会话状态（用户主动开始新测试）
    useSessionStore.getState().resetSession();
    const ok = await startSession();
    if (ok) {
      navigate("/chat");
    }
  };

  const handleContinue = async () => {
    const sid = localStorage.getItem("hylog:session_id");
    if (sid) {
      await useSessionStore.getState().resumeSession(sid);
      navigate("/chat");
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* 主体内容居中 */}
      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="max-w-2xl w-full text-center animate-fade-up">
          {/* 印章 Logo */}
          <div className="flex justify-center mb-8">
            <Seal size={96} text="嗨老己" animated />
          </div>

          {/* 大标题 */}
          <h1 className="font-serif text-6xl sm:text-7xl font-bold text-mo tracking-[0.15em] mb-4">
            {BRAND_NAME}
          </h1>

          {/* slogan */}
          <p className="font-serif text-zhu text-lg tracking-widest mb-2">
            {BRAND_SLOGAN}
          </p>
          <p className="text-mo-light text-base mb-12">{BRAND_TAGLINE}</p>

          {/* 简介 */}
          <div className="card-ink p-8 mb-10 text-left">
            <p className="text-mo leading-relaxed mb-4">
              这是一场关于「认识自己」的对话。
            </p>
            <p className="text-mo-light leading-relaxed mb-4">
              接下来的几轮问答里，没有标准答案——跟着真实想法回答就好。
              我会逐渐勾勒出你的人格画像，OCEAN
              五维的轮廓会在每一次回答后清晰一点点。
            </p>
            <p className="text-mo-light leading-relaxed">
              最后，我会为你找到历史上和你最像的那个人——
              <span className="text-zhu font-medium">也许是一位帝王</span>，
              <span className="text-zhu font-medium">也许是一位诗人</span>，
              <span className="text-zhu font-medium">也许是一位将军</span>。
            </p>
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="mb-6 p-4 rounded-card bg-zhu/10 border border-zhu/30 text-zhu-dark text-sm">
              {error.detail}
            </div>
          )}

          {/* 主 CTA */}
          <button
            onClick={handleStart}
            disabled={loading}
            className="btn-zhu text-lg px-10 py-3.5 w-full sm:w-auto"
          >
            {loading ? "正在准备..." : "开始你的旅程"}
          </button>

          {/* 继续上次测试 */}
          {hasExistingSession && !loading && (
            <button
              onClick={handleContinue}
              className="block mx-auto mt-4 text-sm text-mo-light hover:text-zhu transition-colors underline-offset-4 hover:underline font-serif"
            >
              继续上一次未完成的测试 →
            </button>
          )}
        </div>
      </main>

      {/* 脚注 */}
      <footer className="border-t border-cha/20 py-6 px-6">
        <div className="max-w-2xl mx-auto text-center text-xs text-mo-faint">
          <p className="mb-1">
            基于 OCEAN 五维人格模型 · 11 维问题探索 · 余弦相似度匹配
          </p>
          <p>© Hylog · 认识真实的自己</p>
        </div>
      </footer>
    </div>
  );
}
