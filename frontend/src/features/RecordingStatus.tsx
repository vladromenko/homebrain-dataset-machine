import { Badge } from '@/components/ui/badge';
export function RecordingStatus({ session }: any) {
  const native=session.recording || {};
  const elapsed=native.episode_elapsed_s;
  const timer=typeof elapsed==='number' ? `${Math.floor(elapsed/60).toString().padStart(2,'0')}:${Math.floor(elapsed%60).toString().padStart(2,'0')}` : '—';
  return <div className="recording-status"><Badge variant={native.state==='recording' || native.phase==='recording' ? 'default':'outline'}>{native.state || native.phase || 'No native recording bound'}</Badge><strong>{timer}</strong><span>{native.frames_written ?? native.frames ?? 0} native frames</span><span>Input target: {session.robot_id.toUpperCase()}</span></div>;
}
