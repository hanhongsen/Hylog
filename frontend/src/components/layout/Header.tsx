/**
 * 通用顶部 Header
 *
 * 显示印章 Logo + 品牌名 + 可选的右侧操作区（如"重新开始"按钮）。
 */

import { Link } from "react-router-dom";
import Seal from "./Seal";
import { BRAND_NAME } from "../../lib/constants";

type HeaderProps = {
  /** 右侧操作区（通常是按钮） */
  rightSlot?: React.ReactNode;
  /** 是否显示回到首页链接 */
  showHomeLink?: boolean;
};

export default function Header({ rightSlot, showHomeLink = false }: HeaderProps) {
  return (
    <header className="border-b border-cha/20 bg-xuanzhi/80 backdrop-blur-sm">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
        {/* 左：Logo + 品牌名 */}
        <Link
          to="/"
          className="flex items-center gap-3 group"
          onClick={(e) => {
            // 如果是 showHomeLink 模式，允许跳转；否则点击 Logo 也回首页
          }}
        >
          <Seal size={36} text="嗨" />
          <div className="flex flex-col leading-tight">
            <span className="font-serif text-mo text-lg font-bold tracking-wider group-hover:text-zhu transition-colors">
              {BRAND_NAME}
            </span>
            <span className="text-[10px] text-mo-faint tracking-widest font-sans">
              HYLOG
            </span>
          </div>
        </Link>

        {/* 右：操作区 */}
        <div className="flex items-center gap-3">
          {showHomeLink && (
            <Link
              to="/"
              className="text-sm text-mo-light hover:text-zhu transition-colors font-serif"
            >
              ← 返回首页
            </Link>
          )}
          {rightSlot}
        </div>
      </div>
    </header>
  );
}
