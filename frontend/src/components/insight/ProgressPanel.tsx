/**
 * 对话进度面板
 *
 * 显示在侧栏中，实时展示：
 * - 当前轮次 / 最小收敛轮次 / 最大轮次
 * - 维度覆盖率（如 "8/11"）
 * - 收敛状态指示
 * - 可视化进度条
 */

import type { ProgressInfo } from "../../api/types";

type ProgressPanelProps = {
  progress: ProgressInfo | null;
};

export default function ProgressPanel({ progress }: ProgressPanelProps) {
  if (!progress) {
    return (
      <div className="text-center text-mo/50 text-sm py-6">
        等待对话开始…
      </div>
    );
  }

  const { turn, min_rounds, max_rounds, dimension_coverage, converged } =
    progress;

  // 计算进度百分比（以 min_rounds 为 100% 基准）
  const pct = Math.min(100, Math.round((turn / min_rounds) * 100));

  return (
    <div className="space-y-4">
      {/* 收敛状态 */}
      {converged && (
        <div className="flex items-center gap-2 text-zhu text-sm font-medium">
          <span className="inline-block w-2 h-2 rounded-full bg-zhu animate-pulse" />
          人格画像已收敛
        </div>
      )}

      {/* 进度条 */}
      <div>
        <div className="flex justify-between text-sm text-mo/70 mb-1">
          <span>对话轮次</span>
          <span className="font-mono">
            {turn} / {min_rounds}
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-mo/10 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{
              width: `${pct}%`,
              backgroundColor: converged ? "#6B8E5A" : "#B22222",
            }}
          />
        </div>
        <p className="text-xs text-mo/40 mt-1">
          最大 {max_rounds} 轮
        </p>
      </div>

      {/* 维度覆盖率 */}
      <div className="flex justify-between text-sm">
        <span className="text-mo/70">维度覆盖</span>
        <span className="font-mono text-mo">{dimension_coverage}</span>
      </div>

      {/* 解读文字 */}
      <p className="text-xs text-mo/50 leading-relaxed">
        {converged
          ? "已收集足够信息，可以结束对话查看结果。"
          : turn < min_rounds
            ? `还需约 ${min_rounds - turn} 轮对话以充分了解你的人格特质。`
            : "已达最低收敛轮次，继续对话可让画像更精准。"}
      </p>
    </div>
  );
}
