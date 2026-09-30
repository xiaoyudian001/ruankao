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
