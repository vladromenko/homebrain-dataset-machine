import { useEffect, useRef, useState } from 'react';
import { Expand, Square, VideoOff } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { api, lab } from '@/lib/api';

export function CameraTile({robot, role, recordingState}: {robot: string; role: string; recordingState: string}) {
  const frame = useNativeFrame(robot, role);
  const [focused, setFocused] = useState(false);
  const label = role === 'top' ? 'Workspace · top' : role === 'wrist' ? 'Gripper · wrist' : 'Robot · front';
  return <section className="camera-tile">
    <div className="camera-head"><span>{label}</span><Badge variant="outline">{robot.toUpperCase()} · LIVE</Badge>
      <Button variant="ghost" size="icon" aria-label={`Focus ${robot} ${role} camera`}
        onClick={() => setFocused(true)}><Expand size={14}/></Button>
    </div><CameraImage {...frame} label={`${robot} ${role}`}/>
    <footer><span className={frame.failed ? 'status-dot warning' : 'status-dot'}/>
      {frame.failed ? 'Unavailable / stale' : 'Native shared view'}<span>{frame.age === null ? 'Age unavailable' : `${Math.round(frame.age)} ms`}</span>
    </footer>
    <Dialog open={focused} onOpenChange={setFocused}><DialogContent className="camera-focus-dialog">
      <DialogHeader><DialogTitle>{robot.toUpperCase()} · {label} · {recordingState.replaceAll('_', ' ')}</DialogTitle></DialogHeader>
      <Button variant="destructive" onClick={() => api(`${lab}/stop/${robot}`, {})}><Square size={13}/> STOP {robot.toUpperCase()}</Button>
      <CameraImage {...frame} label={`${robot} ${role}`}/>
      <p className="muted">Native source pixels · {frame.age === null ? 'age unavailable' : `${Math.round(frame.age)} ms at fetch`} · {recordingState}</p>
    </DialogContent></Dialog>
  </section>;
}

function useNativeFrame(robot: string, role: string) {
  const [source, setSource] = useState('');
  const [age, setAge] = useState<number | null>(null);
  const [failed, setFailed] = useState(true);
  const current = useRef('');
  useEffect(() => {
    let active = true, pending = false;
    const refresh = async () => {
      if (document.hidden || pending) return;
      pending = true;
      try {
        const response = await fetch(`${lab}/frame/${robot}/${role}`, {credentials: 'same-origin'});
        if (!response.ok) throw new Error('Native frame unavailable');
        const blob = await response.blob();
        if (active) {
          const next = URL.createObjectURL(blob);
          if (current.current) URL.revokeObjectURL(current.current);
          current.current = next; setSource(next);
          setAge(Number(response.headers.get('X-Frame-Age-Ms'))); setFailed(false);
        }
      } catch { if (active) setFailed(true); }
      finally { pending = false; }
    };
    refresh(); const timer = setInterval(refresh, 1000);
    return () => {active = false; clearInterval(timer); if (current.current) URL.revokeObjectURL(current.current);};
  }, [robot, role]);
  return {source, age, failed};
}

function CameraImage({source, failed, label}: {source: string; failed: boolean; label: string}) {
  return <div className="camera-image">{source && <img src={source} alt={label}/>}
    {failed && <div className="camera-unavailable"><VideoOff size={23}/><span>View unavailable</span>
      <small>Native source disconnected or stale. Check its connection.</small></div>}
  </div>;
}
