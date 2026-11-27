import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';

export function MemorySettings({session}: any) {
  const [records, setRecords] = useState<any[]>([]);
  const [text, setText] = useState('');
  const [projectOnly, setProjectOnly] = useState(false);
  const [correction, setCorrection] = useState<number | null>(null);
  const [message, setMessage] = useState('');
  useEffect(() => {api('/api/lab/v1/memory').then(setRecords).catch(error => setMessage(String(error)));}, []);
  async function save() {
    try {
      await api('/api/memory', {scope: projectOnly ? 'project' : 'preference', text, confirmed: true,
        project_id: projectOnly ? session?.project_id : null, supersedes: correction});
      setRecords(await api('/api/lab/v1/memory')); setText(''); setCorrection(null);
      setMessage('Operator-confirmed memory saved. Live native state takes precedence.');
    } catch (error) {setMessage(String(error));}
  }
  return <Card className="settings-card"><h2>Assistant memory</h2>
    <p>Save a preference or correct a procedure. Corrections supersede older evidence with an audit trail.</p>
    <textarea aria-label="Memory text" maxLength={2000} value={text} onChange={event => setText(event.target.value)}/>
    <label><input type="checkbox" checked={projectOnly} disabled={!session} onChange={event => setProjectOnly(event.target.checked)}/> Selected project only</label>{' '}
    <Button disabled={!text.trim()} onClick={save}>{correction ? 'Save correction' : 'Save confirmed memory'}</Button>
    {message && <p role="status">{message}</p>}
    <div className="native-episodes">{records.slice(0, 20).map(row => <div key={row.id}>
      <p>{row.text}</p><small>{row.project_id || 'Lab'} · {row.verification || 'unverified'} · {row.superseded_by ? 'superseded' : row.expires && row.expires < Date.now()/1000 ? 'expired' : 'current'} · {row.source}</small>{' '}
      <Button variant="ghost" size="sm" onClick={() => {setText(row.text); setCorrection(row.id); setProjectOnly(!!row.project_id);}}>Correct</Button>
    </div>)}</div>
  </Card>;
}
