import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "软考 40 天冲刺",
  description: "系统架构设计师复习监督、每日打卡与资料题库管理",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
