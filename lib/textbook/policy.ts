export function isOwner(user: { email: string } | null, owner: string): boolean {
  return Boolean(owner && user && user.email.toLowerCase() === owner.toLowerCase());
}

export function bridgeAuthorized(header: string | null, secret: string): boolean {
  if (!secret || !header?.startsWith('Bearer ')) return false;
  const value = header.slice(7);
  if (value.length !== secret.length) return false;
  let diff = 0;
  for (let i = 0; i < secret.length; i++) diff |= value.charCodeAt(i) ^ secret.charCodeAt(i);
  return diff === 0;
}

export function bridgeOnline(state: { last_seen: number; ready: number } | null, now: number): boolean {
  return Boolean(state?.ready === 1 && now - state.last_seen <= 45 && now >= state.last_seen);
}

export function validQuestion(value: unknown): string {
  if (typeof value !== 'string' || !value.trim() || value.trim().length > 2000) {
    throw new Error('请输入 1～2000 字的问题。');
  }
  return value.trim();
}

export function cleanAnswer(value: string): string {
  return value.replace(/<think\b[^>]*>[\s\S]*?(?:<\/think\s*>|$)/gi, '').trim();
}

export const validId = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9-]{36}$/i.test(value);

export const RETRIEVAL_MODES = { default: '当前问答', complete: '完整检索实验' } as const;
export type RetrievalMode = keyof typeof RETRIEVAL_MODES;
export function validRetrievalMode(value: unknown): RetrievalMode {
  if (value == null) return 'default';
  if (typeof value !== 'string' || !Object.hasOwn(RETRIEVAL_MODES,value)) throw new Error('检索模式无效。');
  return value as RetrievalMode;
}
export function availableRetrievalModes(state: {last_seen:number;ready:number;modes?:string}|null,time:number): RetrievalMode[] {
  if (!bridgeOnline(state,time)) return [];
  try {
    const modes:unknown=JSON.parse(state?.modes??'["default"]');
    if (!Array.isArray(modes)) return ['default'];
    return (Object.keys(RETRIEVAL_MODES) as RetrievalMode[]).filter(mode=>modes.includes(mode));
  } catch { return ['default']; }
}
export function sameJobRequest(prior:{question:string;retrieval_mode:string;session_id:string},question:string,mode:RetrievalMode,session:unknown):boolean {
  return prior.question===question && prior.retrieval_mode===mode && (session==null || session===prior.session_id);
}
