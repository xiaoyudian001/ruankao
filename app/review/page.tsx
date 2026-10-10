import {requireChatGPTUser} from '../chatgpt-auth';
import {isOwner} from '../../lib/textbook/policy';
import {runtime} from '../../lib/textbook/server';
import ReviewCenter from './review-center';

export const dynamic='force-dynamic';
export default async function ReviewPage(){
  const user=await requireChatGPTUser('/review');
  if(!isOwner(user,runtime().RAG_OWNER_EMAIL??''))return <main className="mx-auto max-w-xl px-6 py-20"><h1 className="text-2xl font-bold">复习中心仅供网站所有者使用</h1><p className="mt-4 text-slate-600">请使用教材问答的同一账号登录。</p><a href="/signout-with-chatgpt?return_to=%2Freview" target="_top" className="mt-6 inline-block text-blue-700 underline">切换账号</a></main>;
  return <ReviewCenter/>;
}
