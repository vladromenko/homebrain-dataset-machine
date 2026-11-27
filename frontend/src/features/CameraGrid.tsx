import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { CameraTile } from '@/components/CameraTile';

function identity(source: string, fallback: string) {
  if (!source.includes('/')) return { robot:fallback,role:source };
  const [robot,role] = source.split('/');
  return { robot:robot.replace(/-\d+$/,''),role };
}
export function CameraGrid({ session, task }: any) {
  const sources = (task?.camera_roles || ['top','wrist']).map((role: string) => identity(role,session.robot_id));
  const multiple = sources.some((source: any) => source.robot !== session.robot_id);
  const [chosen,setChosen] = useState<string | null>(null);
  const mobilePhase = ['mobile_lead_in','relocation','settled_capture','pending_reveal'].includes(session.state);
  const group = chosen || (mobilePhase ? 'witness' : 'arm');
  const visible = multiple ? sources.filter((source: any) => group === 'arm' ? source.robot==='so101' : source.robot!=='so101') : sources;
  return <section>{multiple && <div className="camera-view-tabs"><Button size="sm" variant={group==='arm' ? 'secondary':'ghost'} onClick={() => setChosen('arm')}>Arm views</Button><Button size="sm" variant={group==='witness' ? 'secondary':'ghost'} onClick={() => setChosen('witness')}>Witness views</Button><span>Preview selection never changes recording inputs.</span></div>}<div className="camera-grid">{visible.map((source: any) => <CameraTile key={source.robot+'/'+source.role} robot={source.robot} role={source.role} recordingState={session.recording.state || session.recording.phase || "not recording"}/>)}</div></section>;
}
