import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { speak } from '@/lib/speech';

export function Advisories() {
  const [events, setEvents] = useState<any[]>([]);
  const spoken = useRef(new Set<string>());
  useEffect(() => {
    const refresh = async () => {
      try {
        const pending = await api<any[]>('/api/events'); setEvents(pending);
        const event = pending[0];
        if (event && !spoken.current.has(event.id)) {
          spoken.current.add(event.id); await speak(event.text);
        }
      } catch {}
    };
    refresh(); const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, []);
  const event = events[0];
  if (!event) return null;
  return <div role="status" className="notice warning advisory">{event.text}
    <button aria-label="Acknowledge advisory" onClick={async () => {
      await api(`/api/events/${event.id}/acknowledge`, {}); setEvents(rows => rows.filter(row => row.id !== event.id));
    }}>Dismiss</button>
  </div>;
}
