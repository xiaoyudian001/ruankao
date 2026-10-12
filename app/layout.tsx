import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "软考 AI 学习助手",
  description: "系统架构设计师备考：教材溯源、案例练习、论文训练与40天复习计划",
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
