/**
 * OCEAN 五维雷达图
 *
 * 用 recharts 的 RadarChart 实现。
 * 两种用法：
 * 1. 单一数据（对话页侧栏）：只显示用户的当前 OCEAN
 * 2. 双数据对比（结果页）：用户实线 + 人物虚线，直观看出"像在哪、不像在哪"
 */

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import type { OceanVector } from "../../api/types";
import { OCEAN_KEYS, OCEAN_LABELS } from "../../lib/constants";

type OceanRadarProps = {
  /** 用户的 OCEAN 分数 */
  ocean: OceanVector;
  /** 可选：对比人物（结果页双雷达） */
  compareOcean?: OceanVector;
  /** 对比人物的名称（用于 Legend） */
  compareName?: string;
  /** 图表尺寸（宽度自适应，height 固定） */
  height?: number;
};

/** 把 OceanVector 转成 recharts 需要的数据格式 */
function toChartData(ocean: OceanVector, compare?: OceanVector) {
  return OCEAN_KEYS.map((key) => ({
    dimension: OCEAN_LABELS[key],
    你: Number((ocean[key] * 100).toFixed(0)),
    ...(compare ? { [compare ? "对比" : ""]: Number((compare[key] * 100).toFixed(0)) } : {}),
  }));
}

export default function OceanRadar({
  ocean,
  compareOcean,
  compareName,
  height = 240,
}: OceanRadarProps) {
  const data = toChartData(ocean, compareOcean);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
        <PolarGrid stroke="#8B6F47" strokeOpacity={0.3} />
        <PolarAngleAxis
          dataKey="dimension"
          tick={{
            fontSize: 12,
            fill: "#2C2826",
            fontFamily: "'Noto Sans SC', sans-serif",
          }}
        />
        <PolarRadiusAxis
          domain={[0, 100]}
          tick={false}
          axisLine={false}
          tickCount={5}
        />

        {/* 用户的 OCEAN（朱红实线填充） */}
        <Radar
          name="你"
          dataKey="你"
          stroke="#B22222"
          strokeWidth={2}
          fill="#B22222"
          fillOpacity={0.25}
          isAnimationActive
          animationDuration={500}
        />

        {/* 对比人物的 OCEAN（茶褐虚线） */}
        {compareOcean && (
          <Radar
            name={compareName || "对比人物"}
            dataKey="对比"
            stroke="#8B6F47"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            fill="#8B6F47"
            fillOpacity={0.08}
            isAnimationActive
            animationDuration={500}
          />
        )}

        {compareOcean && <Legend wrapperStyle={{ fontSize: 12, fontFamily: "'Noto Sans SC', sans-serif" }} />}
        <Tooltip
          contentStyle={{
            backgroundColor: "#ECE3CD",
            border: "1px solid rgba(139, 111, 71, 0.3)",
            borderRadius: "6px",
            fontSize: 12,
            fontFamily: "'Noto Sans SC', sans-serif",
          }}
          labelStyle={{ color: "#2C2826", fontWeight: 500 }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
