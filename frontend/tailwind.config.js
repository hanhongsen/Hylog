/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      // ========================================
      // 中国传统古典风配色
      // ========================================
      colors: {
        // 宣纸系列（背景）
        xuanzhi: {
          DEFAULT: "#F5EFE0", // 主背景：宣纸底色
          card: "#ECE3CD",    // 卡片底
          dark: "#E0D5B7",    // 深一档（边框/分割）
        },
        // 墨色系列（文字）
        mo: {
          DEFAULT: "#2C2826", // 主文字：浓墨
          light: "#5C544A",   // 次要文字：淡墨
          faint: "#8A8175",   // 辅助文字：极淡墨
        },
        // 朱红系列（强调）
        zhu: {
          DEFAULT: "#B22222", // 印章朱红：主强调色
          dark: "#8B1A1A",    // 深朱
          light: "#D14E4E",   // 浅朱
        },
        // 竹青系列（进度/成功）
        zhuqing: {
          DEFAULT: "#6B8E5A", // 竹青
          dark: "#557349",
        },
        // 茶褐系列（边框/分割）
        cha: {
          DEFAULT: "#8B6F47", // 茶褐
          light: "#A88A66",
        },
        // 淡金系列（点缀/装饰）
        jin: {
          DEFAULT: "#C9A961", // 淡金
          light: "#DDBE7A",
        },
      },
      // ========================================
      // 字体
      // ========================================
      fontFamily: {
        // 宋体（标题/人物名）
        serif: ['"Noto Serif SC"', '"Songti SC"', '"SimSun"', "serif"],
        // 黑体（正文）
        sans: ['"Noto Sans SC"', '"PingFang SC"', '"Microsoft YaHei"', "sans-serif"],
        // 楷体（语录/古文）
        kai: ['"Ma Shan Zheng"', '"KaiTi"', '"楷体"', "cursive"],
      },
      // ========================================
      // 圆角（古典风偏方正，圆角小一点）
      // ========================================
      borderRadius: {
        // 卡片用稍小圆角（更有书卷气）
        card: "6px",
      },
      // ========================================
      // 动画
      // ========================================
      keyframes: {
        // 水墨滴落（AI 思考动画）
        "ink-drop": {
          "0%, 80%, 100%": { transform: "scale(0.5)", opacity: "0.3" },
          "40%": { transform: "scale(1)", opacity: "1" },
        },
        // 印章盖落
        "stamp-down": {
          "0%": { transform: "scale(2) rotate(-15deg)", opacity: "0" },
          "60%": { transform: "scale(0.95) rotate(-3deg)", opacity: "1" },
          "100%": { transform: "scale(1) rotate(0deg)", opacity: "1" },
        },
        // 淡入上滑
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "ink-drop": "ink-drop 1.4s ease-in-out infinite",
        "stamp-down": "stamp-down 0.6s ease-out",
        "fade-up": "fade-up 0.5s ease-out",
      },
    },
  },
  plugins: [],
};
