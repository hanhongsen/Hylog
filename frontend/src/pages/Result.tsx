/**
 * 结果页
 *
 * 展示用户与历史人物的匹配结果：
 *   ┌──────────────────────────────────────┐
 *   │  印章 + "你的画像已成形"               │
 *   ├──────────────────────────────────────┤
 *   │  人物卡片：                            │
 *   │   · 姓名（竖排）/朝代/相似度            │
 *   │   · 简介 / 关键词 / 标签               │
 *   │   · 语录（楷体）                       │
 *   │   · 双 OCEAN 雷达对比                  │
 *   ├──────────────────────────────────────┤
 *   │  详细字段：                            │
 *   │   · 经典场景 / 趣味冷知识               │
 *   │   · 性格建议 / 相关书籍                │
 *   ├──────────────────────────────────────┤
 *   │  操作：再测一次 / 返回首页              │
 *   └──────────────────────────────────────┘
 *
 * 数据来源：store.result（由对话结束 / Chat 页跳转前填入）。
 * 如果用户直接访问 /result 但没有结果，尝试用 sessionId 拉取，
 * 仍失败则回首页。
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/layout/Header";
import OceanRadar from "../components/insight/OceanRadar";
import { useSessionStore } from "../store/session";
import * as api from "../api/client";
import type { MatchResultInfo } from "../api/types";
import { getOceanLevel } from "../lib/constants";

export default function Result() {
  const navigate = useNavigate();
  const sessionId = useSessionStore((s) => s.sessionId);
  const userOcean = useSessionStore((s) => s.ocean);
  const storedResult = useSessionStore((s) => s.result);
  const resetSession = useSessionStore((s) => s.resetSession);

  const [result, setResult] = useState<MatchResultInfo | null>(storedResult);
  const [loading, setLoading] = useState(!storedResult);
  const [error, setError] = useState<string | null>(null);

  // 若 store 里没有结果，尝试从后端拉取
  useEffect(() => {
    if (storedResult) {
      setResult(storedResult);
      setLoading(false);
      return;
    }
    if (!sessionId) {
      navigate("/", { replace: true });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const r = await api.getResult(sessionId);
        if (!cancelled) {
          setResult(r);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        const msg =
          err instanceof Error ? err.message : "无法加载结果，请稍后重试";
        setError(msg);
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId, storedResult, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-mo-light animate-pulse font-serif">
          正在勾勒你的画像…
        </p>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen flex flex-col">
        <Header showHomeLink />
        <main className="flex-1 flex items-center justify-center px-6">
          <div className="max-w-md text-center">
            <p className="text-zhu-dark mb-4">{error || "暂无匹配结果"}</p>
            <button onClick={() => navigate("/")} className="btn-outline">
              返回首页
            </button>
          </div>
        </main>
      </div>
    );
  }

  const character = result.character;
  const similarity = Math.round(result.similarity_percent);

  const handleRestart = () => {
    resetSession();
    navigate("/", { replace: true });
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header showHomeLink />

      <main className="flex-1 px-4 sm:px-6 py-8">
        <div className="max-w-4xl mx-auto">
          {/* ---------- 顶部标题 ---------- */}
          <div className="text-center mb-8 animate-fade-up">
            <p className="text-jin font-serif tracking-[0.3em] text-sm mb-2">
              · 画 像 已 成 ·
            </p>
            <h1 className="font-serif text-3xl sm:text-4xl text-mo font-bold tracking-wider">
              你最像的历史人物是
            </h1>
          </div>

          {/* ---------- 人物卡片 ---------- */}
          <div className="card-ink overflow-hidden mb-8 animate-fade-up">
            <div className="grid md:grid-cols-[200px_1fr] gap-0">
              {/* 左：姓名 + 朝代 + 相似度（竖排姓名在桌面端） */}
              <div className="bg-gradient-to-br from-zhu/5 to-jin/10 p-6 md:p-8 border-b md:border-b-0 md:border-r border-cha/20 flex flex-col items-center justify-center text-center">
                {/* 头像占位（朱红印章风） */}
                <div className="w-24 h-24 rounded-card bg-zhu/10 border-2 border-zhu/40 flex items-center justify-center mb-4">
                  <span className="font-serif text-4xl text-zhu font-bold">
                    {character.name.charAt(0)}
                  </span>
                </div>
                <h2 className="font-serif text-3xl text-mo font-bold tracking-wider mb-1">
                  {character.name}
                </h2>
                <p className="text-mo-light text-sm mb-4">{character.era}</p>
                <div className="inline-flex flex-col items-center">
                  <span className="text-xs text-mo-faint mb-1">相似度</span>
                  <span className="font-serif text-3xl text-zhu font-bold tabular-nums">
                    {similarity}
                    <span className="text-base align-top">%</span>
                  </span>
                </div>
              </div>

              {/* 右：简介 + 关键词 + 标签 */}
              <div className="p-6 md:p-8">
                {/* 性格关键词 */}
                {character.personality_keyword && (
                  <div className="mb-4">
                    <span className="inline-block bg-jin/15 text-cha px-3 py-1 rounded-sm text-sm font-serif">
                      「{character.personality_keyword}」
                    </span>
                  </div>
                )}

                {/* 简介 */}
                <p className="text-mo leading-relaxed mb-4">
                  {character.description}
                </p>

                {/* 标签 */}
                {character.tags?.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {character.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-xs text-mo-light bg-xuanzhi-dark/60 px-2 py-0.5 rounded-sm"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* 语录 */}
            {character.quote && (
              <div className="border-t border-cha/20 px-6 md:px-8 py-5 bg-xuanzhi/40">
                <p className="font-kai text-lg text-mo text-center leading-relaxed">
                  「{character.quote}」
                </p>
                <p className="text-right text-sm text-mo-faint mt-1">
                  —— {character.name}
                </p>
              </div>
            )}
          </div>

          {/* ---------- 双 OCEAN 雷达对比 ---------- */}
          <section className="mb-8 animate-fade-up">
            <h3 className="section-title">人格画像对比</h3>
            <div className="card-ink p-4 sm:p-6">
              <OceanRadar
                ocean={userOcean}
                compareOcean={character.ocean_vector}
                compareName={character.name}
                height={320}
              />
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-5 gap-2">
                {(["O", "C", "E", "A", "N"] as const).map((key) => {
                  const level = getOceanLevel(userOcean[key]);
                  return (
                    <div
                      key={key}
                      className="text-center bg-xuanzhi/50 rounded-sm py-2"
                    >
                      <p className="text-xs text-mo-faint">{key}</p>
                      <p className="font-serif text-sm" style={{ color: level.color }}>
                        {level.label}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>

          {/* ---------- 详细字段 ---------- */}
          <div className="space-y-6 mb-8">
            {character.classic_events && (
              <DetailSection title="经典场景" content={character.classic_events} />
            )}
            {character.fun_facts && (
              <DetailSection title="趣味冷知识" content={character.fun_facts} />
            )}
            {character.advice && (
              <DetailSection title="给你的建议" content={character.advice} accent />
            )}
            {character.related_books && (
              <DetailSection title="延伸阅读" content={character.related_books} />
            )}
          </div>

          {/* ---------- 操作 ---------- */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center pt-4 border-t border-cha/20">
            <button onClick={handleRestart} className="btn-zhu px-8 py-3">
              再测一次
            </button>
            <button
              onClick={() => navigate("/")}
              className="btn-outline px-8 py-3"
            >
              返回首页
            </button>
          </div>
        </div>
      </main>

      <footer className="border-t border-cha/20 py-6 px-6 text-center text-xs text-mo-faint">
        <p>© Hylog · 认识真实的自己</p>
      </footer>
    </div>
  );
}

/** 详细字段分区（带标题分隔线） */
function DetailSection({
  title,
  content,
  accent = false,
}: {
  title: string;
  content: string;
  accent?: boolean;
}) {
  return (
    <section className="animate-fade-up">
      <h3 className="section-title">{title}</h3>
      <div
        className={`card-ink p-5 ${
          accent ? "border-l-4 border-l-zhu/50" : ""
        }`}
      >
        <p className="text-mo-light leading-relaxed whitespace-pre-wrap">
          {content}
        </p>
      </div>
    </section>
  );
}
