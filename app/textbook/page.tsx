import { requireChatGPTUser } from '../chatgpt-auth';
import { runtime } from '../../lib/textbook/server';
import { isOwner } from '../../lib/textbook/policy';
import TextbookChat from './textbook-chat';
import Link from 'next/link';

export const dynamic = 'force-dynamic';
export default async function TextbookPage() {
  const user = await requireChatGPTUser('/textbook');
  if (!isOwner(user,runtime().RAG_OWNER_EMAIL ?? '')) return <main className="mx-auto max-w-xl px-6 py-20"><h1 className="text-2xl font-bold">教材问答仅供网站所有者使用</h1><p className="mt-4 leading-7 text-slate-600">请登录创建此网站的 ChatGPT 账号。</p><a href="/signout-with-chatgpt?return_to=%2Ftextbook" target="_top" className="mt-6 inline-block text-blue-700 underline">切换账号</a><Link href="/" target="_top" prefetch={false} className="ml-6 text-blue-700 underline">返回冲刺台</Link></main>;
  return <TextbookChat ownerId={user.userId}/>;
}
