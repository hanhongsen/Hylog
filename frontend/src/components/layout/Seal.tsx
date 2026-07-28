/**
 * 朱红印章 Logo
 *
 * SVG 实现，无图片依赖。用于落地页 Hero、Header 等位置。
 *
 * 设计：
 * - 朱红方框（#B22222）+ 宣纸色描边
 * - 中央竖排 "嗨老己" 三字（篆体感）
 * - 略带倾斜（-2deg），模拟手盖印章
 *
 * 用法：
 *   <Seal size={80} />            // 简单正方形印章
 *   <Seal size={80} text="嗨" />  // 单字印章
 */

type SealProps = {
  /** 印章尺寸（正方形边长，px） */
  size?: number;
  /** 印章内文字，默认 "嗨老己" 三字竖排 */
  text?: string;
  /** 是否带盖落动画 */
  animated?: boolean;
  className?: string;
};

export default function Seal({
  size = 64,
  text = "嗨老己",
  animated = false,
  className = "",
}: SealProps) {
  // 根据字数计算字号
  const charCount = text.length;
  const fontSize = charCount <= 1 ? size * 0.6 : size * (0.5 / Math.sqrt(charCount));

  return (
    <div
      className={`inline-block ${animated ? "animate-stamp-down" : ""} ${className}`}
      style={{ width: size, height: size }}
    >
      <svg
        viewBox="0 0 100 100"
        width={size}
        height={size}
        style={{ transform: "rotate(-2deg)" }}
      >
        {/* 外框 */}
        <rect x="4" y="4" width="92" height="92" rx="6" fill="#B22222" />
        {/* 内描边 */}
        <rect
          x="10"
          y="10"
          width="80"
          height="80"
          rx="3"
          fill="none"
          stroke="#F5EFE0"
          strokeWidth="2.5"
        />
        {/* 文字（竖排，居中） */}
        {charCount === 1 ? (
          <text
            x="50"
            y={50 + fontSize * 0.35}
            textAnchor="middle"
            fontSize={fontSize}
            fontFamily="'Noto Serif SC', 'Songti SC', 'SimSun', serif"
            fontWeight="900"
            fill="#F5EFE0"
          >
            {text}
          </text>
        ) : (
          <text
            x="50"
            y="50"
            textAnchor="middle"
            fontSize={fontSize}
            fontFamily="'Noto Serif SC', 'Songti SC', 'SimSun', serif"
            fontWeight="900"
            fill="#F5EFE0"
            style={{
              writingMode: "vertical-rl",
              textOrientation: "upright",
              letterSpacing: "0.1em",
            }}
            dominantBaseline="central"
          >
            {text}
          </text>
        )}
      </svg>
    </div>
  );
}
