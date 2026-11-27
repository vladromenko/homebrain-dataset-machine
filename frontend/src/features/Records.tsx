import { useEffect, useState } from 'react';
import { api, lab } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ReplayCatalog } from './ReplayViewer';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export function Records({kind, overview}: any) {
  const [catalog, setCatalog] = useState<any>(null);
  const [error, setError] = useState('');
  useEffect(() => {api(`${lab}/catalog`).then(setCatalog).catch(failure => setError(String(failure)));}, [kind]);
  const studio = catalog?.studio || overview?.native.studio.data || {};
  const explorer = catalog?.explorer || {};
  const jobs = [...(studio.jobs || []).map((row: any) => ({...row, source: 'Studio'})),
    ...(explorer.jobs || []).map((row: any) => ({...row, source: 'Explorer'}))];
  return <div className="projects"><div className="eyebrow">NATIVE CATALOG</div>
    <h1>{kind === 'Jobs' ? 'Exports, training & evaluation' : 'Recordings & evidence'}</h1>
    <p className="muted">Native identifiers and artifacts stay in their original stores.</p>
    {error && <p role="alert">{error}</p>}
    {kind === 'Jobs' ? <Jobs jobs={jobs}/> : <>
      <Datasets datasets={studio.datasets || []}/><ExplorerEpisodes episodes={explorer.episodes || []}/><ReplayCatalog/>
    </>}
  </div>;
}

function Jobs({jobs}: any) {
  return <div className="task-list">{jobs.slice(0, 40).map((row: any) => <Card className="task-row" key={row.id}>
    <div><h3>{row.kind || row.name || row.profile}</h3><p>{row.source} · {row.id}</p><p>{row.message || row.error}</p></div>
    <Badge variant="secondary">{row.state || row.status}</Badge>
  </Card>)}</div>;
}

function Datasets({datasets}: any) {
  const [selected, setSelected] = useState<string | null>(null);
  return <>
    <div className="list-heading"><h2>Studio datasets</h2><span>{datasets.length} native datasets</span></div>
    <div className="task-list">{datasets.map((row: any) => <Card className="task-row" key={row.dataset_id}>
      <div><h3>{row.name}</h3><p>{row.dataset_id} · {row.episodes} saved · {row.source}</p></div>
      <Badge variant="outline">{row.camera_mode}</Badge>
      <Button variant="outline" onClick={() => setSelected(row.dataset_id)}>Browse episodes</Button>
    </Card>)}</div>
    <Dialog open={!!selected} onOpenChange={value => {if (!value) setSelected(null);}}>
      <DialogContent className="evidence-dialog"><DialogHeader><DialogTitle>Native episodes</DialogTitle></DialogHeader>
        {selected && <StudioEpisodes dataset={selected}/>}
      </DialogContent>
    </Dialog>
  </>;
}

function StudioEpisodes({dataset}: {dataset: string}) {
  const [episodes, setEpisodes] = useState<any[]>([]);
  const [message, setMessage] = useState('');
  useEffect(() => {api(`${lab}/datasets/${dataset}/episodes`).then(setEpisodes).catch(error => setMessage(String(error)));}, [dataset]);
  async function inspect(id: string) {
    try {
      const session = await api(`${lab}/inspect`, {dataset_id: dataset, episode_id: id});
      window.dispatchEvent(new CustomEvent('homebrain-selected-session', {detail: session}));
      setMessage('Selected this native episode for the assistant. No control was enabled.');
    } catch (error) {setMessage(String(error));}
  }
  return <div className="native-episodes">{message && <p role="status">{message}</p>}
    {episodes.map(row => <Card className="task-row" key={row.id}><div><h3>{row.id}</h3>
      <p>{row.metadata?.status || 'unknown'} · {row.storage} · {row.metadata?.source}</p>
      <p>{row.metadata?.reason || row.metadata?.stop_reason}</p></div>
      <Button variant="outline" onClick={() => inspect(row.id)}>Ask about this episode</Button>
    </Card>)}
  </div>;
}

function ExplorerEpisodes({episodes}: any) {
  return <><div className="list-heading"><h2>Explorer episodes</h2><span>Raw save ≠ admission</span></div>
    <div className="task-list">{episodes.slice(0, 30).map((row: any) => <Card className="task-row" key={row.id}>
      <div><h3>{row.profile}</h3><p>{row.id} · {row.frames} frames · {row.category}</p></div>
      <Badge variant="secondary">{row.outcome || 'unknown'}</Badge>
    </Card>)}</div>
  </>;
}
