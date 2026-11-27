import { useEffect, useState } from 'react';
import { api, lab } from '@/lib/api';

export function Progress({project}: {project: string}) {
  const [progress, setProgress] = useState<any>(null);
  useEffect(() => {
    const refresh = () => api(`${lab}/progress?project_id=${encodeURIComponent(project)}`).then(setProgress).catch(() => setProgress(null));
    refresh(); const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, [project]);
  if (!progress) return null;
  const counters = [['Attempts', progress.attempts], ['Raw saves', progress.saved_raw],
    ['Technical checks passed', progress.technically_valid], ['Admitted stories', progress.admitted_story],
    ['Assisted', progress.assisted], ['Incomplete', progress.incomplete]];
  return <section className="progress-counters" aria-label="Evidence counters">
    {counters.map(([label, value]) => <div key={label}><strong>{value}</strong><span>{label}</span></div>)}
    <p>{progress.scope}. {Object.entries(progress.denominators || {}).map(([key, count]) => `${key.replaceAll('_', ' ')}: ${count}`).join(' · ')}</p>
  </section>;
}
