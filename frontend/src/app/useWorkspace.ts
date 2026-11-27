import { useCallback, useEffect, useRef, useState } from 'react';
import { api, lab, type Session, type Task } from '@/lib/api';

export function useOverview() {
  const [overview, setOverview] = useState<any>(null);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    try { setOverview(await api(`${lab}/overview`)); }
    catch (failure) { setOverview(null); setError(String(failure)); }
  }, []);
  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 4000);
    return () => clearInterval(timer);
  }, [refresh]);
  return { overview, error, setError };
}

export function useTasks(project: string, group: string) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const cache = useRef(new Map<string, Task>());
  useEffect(() => setOffset(0), [project, group]);
  useEffect(() => {
    let active = true;
    const query = new URLSearchParams({project_id: project, offset: String(offset), limit: '50'});
    if (group) query.set('group', group);
    api(`${lab}/tasks?${query}`).then(data => {
      if (active) {
        setTasks(data.tasks); setTotal(data.total); setError('');
        data.tasks.forEach((task: Task) => cache.current.set(task.task_id, task));
      }
    }).catch(failure => { if (active) setError(String(failure)); });
    return () => { active = false; };
  }, [project, group, offset]);
  return { tasks, offset, setOffset, total, error, find: (id: string) => cache.current.get(id) };
}

export function useSession() {
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const saved = localStorage.getItem('homebrain-session');
    if (saved) api<Session>(`${lab}/sessions/${saved}`).then(setSession)
      .catch(() => localStorage.removeItem('homebrain-session'));
  }, []);
  useEffect(() => {
    if (!session) return;
    const timer = setInterval(() => api<Session>(`${lab}/sessions/${session.session_id}`)
      .then(setSession).catch(failure => setError(String(failure))), 1500);
    return () => clearInterval(timer);
  }, [session?.session_id]);
  const retain = (value: Session) => {
    localStorage.setItem('homebrain-session', value.session_id);
    setSession(value);
  };
  useEffect(() => {
    const select = (event: Event) => retain((event as CustomEvent).detail);
    window.addEventListener('homebrain-selected-session', select);
    return () => window.removeEventListener('homebrain-selected-session', select);
  }, []);
  return { session, setSession, retain, error };
}

export function useAction(session: Session | null, setSession: (value: Session | null) => void, setError: (value: string) => void) {
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  async function act(action: string, args: any) {
    if (!session || pending.current) return;
    pending.current = true; setBusy(true); setError('');
    try {
      const current = await api<Session>(`${lab}/sessions/${session.session_id}`);
      const result = await api(`${lab}/actions`, {
        action, project_id: current.project_id, session_id: current.session_id,
        target_id: current.task_id, expected_revision: current.revision,
        idempotency_key: crypto.randomUUID(), arguments: args,
      });
      if (['rejected', 'unknown'].includes(result.status)) setError(result.message);
      setSession(await api(`${lab}/sessions/${session.session_id}`));
      if (action === 'next_task') {
        setSession(null); localStorage.removeItem('homebrain-session');
      }
    } catch (failure) { setError(String(failure)); }
    finally { pending.current = false; setBusy(false); }
  }
  return { act, busy };
}
