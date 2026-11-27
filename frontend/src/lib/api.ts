export async function api<T = any>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, { credentials: 'same-origin',
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new Error(response.status === 401 ? 'Open Homebrain from your Mac icon to reconnect securely.' : data.detail || data.error || 'Request failed');
  return data;
}
export const lab = '/api/lab/v1';
export type { SessionSnapshot as Session, TaskCard as Task } from './generated';
