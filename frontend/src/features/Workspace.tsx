import { useState } from 'react';
import { ArrowRight, CheckCircle2, Circle, LoaderCircle, SlidersHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { NativeControl } from './NativeControl';
import { ProjectAction } from './ProjectAction';
import { RecordingStatus } from './RecordingStatus';
import { CameraGrid } from './CameraGrid';
import { type Session, type Task } from '@/lib/api';
const labels: Record<string, string> = {
  prepare_session: 'Prepare session', enable_control: 'Enable control', start_recording: 'Start recording',
  finish_recording: 'Finish recording', confirm_outcome: 'Confirm outcome', next_task: 'Next task',
  retry_validation: 'Retry validation', reconcile: 'Reconcile native state',
};

export function Workspace({ session, task, control, busy, onAction }: any) {
  return <div className="workspace">
    <div className="section-heading"><div>
      <div className="eyebrow">{session.project_id === 'smart-swarm' ? 'SMART SWARM' : 'DEVELOPMENT COLLECTION'}</div>
      <h1>{task?.title || session.task_id}</h1>
    </div><Diagnostics session={session}/></div>
    <Journey session={session}/>
    <Card className="instruction"><div><span className="eyebrow">CURRENT INSTRUCTION</span>
      <h2>{session.instruction}</h2>
      <p>{session.robot_id.toUpperCase()} · {task?.control_profile || 'Project native profile'} ·
        {control.connected ? ' Browser control link connected' : ' Control link disconnected'}</p>
    </div></Card>
    {!!session.blockers.length && <div role="alert" className="notice warning">
      {session.blockers.join(' · ')}{session.recovery && <p>{session.recovery}</p>}
    </div>}
    <ViewpointReview session={session} onAction={onAction} busy={busy}/>
    <RecordingStatus session={session}/><CameraGrid session={session} task={task}/>
    <div className="workspace-bottom"><Setup task={task}/><ControlCard session={session} control={control}/></div>
    {session.project_id === 'smart-swarm' ? <>
      <Button variant="outline" disabled={busy || !control.connected || !!session.recording.active || !!session.pending_work.length}
        onClick={() => onAction('enable_control', {})}>Enable native control</Button>
      <ProjectAction session={session} busy={busy} onAction={onAction}/>
    </> : <Actions key={session.session_id} session={session} busy={busy} onAction={onAction}/>}
  </div>;
}

function Journey({ session }: any) {
  const phases = ['Prepare', 'Control', 'Record', 'Save', 'Review'];
  const stages: Record<string, number> = {selected: 0, prepared: 1, enabled: 2, starting: 2, recording: 2,
    saving: 3, checking: 3, saved: 4, needs_review: 4, reviewed: 4, complete: 4};
  const index = stages[session.state] ?? 0;
  return <div className="journey">{phases.map((phase, i) =>
    <span key={phase} className={i <= index ? 'done' : ''}>
      {i < index ? <CheckCircle2 size={15}/> : <Circle size={15}/>} {phase}
    </span>)}<Badge variant="secondary">{session.state.replaceAll('_', ' ')}</Badge>
  </div>;
}

function ControlCard({session, control}: any) {
  return <Card className="control-card"><span className="eyebrow">HUMAN CONTROL TARGET</span>
    <h3>{session.robot_id.toUpperCase()}</h3>
    <p>{session.robot_id === 'so101' ? 'Native leader → follower. Enable explicitly before moving the leader.' :
      'Use the keyboard or connected gamepad. Keep this view focused.'}</p>
    <NativeControl robot={session.robot_id} control={control}/>
  </Card>;
}

function Actions({session, busy, onAction}: any) {
  const [outcome, setOutcome] = useState('unknown');
  const [assisted, setAssisted] = useState(false);
  const primary = session.permitted_actions.find((action: string) => action !== 'retry_validation') || session.permitted_actions[0];
  const arguments_ = primary === 'confirm_outcome' ? {outcome, assisted} : {outcome: outcome === 'unknown' ? 'aborted' : outcome, assisted};
  return <div className="action-bar"><div>
    <strong>{session.receipts.length ? 'Native evidence retained' : 'Local native recording'}</strong>
    <small>{session.native_ids.episode_id || 'Raw save and scientific acceptance are separate.'}</small>
  </div>
    {['finish_recording', 'confirm_outcome'].includes(primary) && <div className="outcome">
      <select aria-label="Observed outcome" value={outcome} onChange={event => setOutcome(event.target.value)}>
        <option value="unknown">Unknown outcome</option><option value="success">Observed success</option><option value="failure">Observed failure</option>
      </select><label><input type="checkbox" checked={assisted} onChange={event => setAssisted(event.target.checked)}/> Assisted</label>
    </div>}
    {primary ? <Button size="lg" disabled={busy} onClick={() => onAction(primary, arguments_)}>
      {busy ? <LoaderCircle className="spin" size={16}/> : <ArrowRight size={16}/>} {labels[primary] || primary.replaceAll('_', ' ')}
    </Button> : <span className="pending"><LoaderCircle className="spin" size={17}/> Waiting for native readback</span>}
  </div>;
}

function Setup({ task }: {task?: Task}) {
  return <Card className="setup-card"><span className="eyebrow">SCENE SETUP</span>
    {task?.setup_media?.length ? <img className="project-setup-media"
      src={`/api/lab/v1/project-media/${task.project_id}/${task.setup_media[0]}`} alt="Project station setup"/> : <LayoutGuide/>}
    <p className="muted">Layout guide · positions require attended verification</p>
    <ul>{task?.setup.map((step, i) => <li key={i}>{step}</li>)}</ul>
  </Card>;
}

function LayoutGuide() {
  return <div className="setup-diagram" aria-label="Workspace setup diagram">
    <div className="diagram-camera">TOP VIEW ↓</div><div className="diagram-object">Object</div>
    <div className="diagram-target">Target</div><div className="diagram-arm">Native robot workspace</div>
  </div>;
}

function Diagnostics({ session }: {session: Session}) {
  return <Dialog><DialogTrigger asChild><Button variant="outline" size="sm"><SlidersHorizontal size={14}/> Evidence</Button></DialogTrigger>
    <DialogContent className="evidence-dialog"><DialogHeader><DialogTitle>Native evidence & recovery</DialogTitle></DialogHeader>
      <p>Session revision {session.revision}. Receipts retain native ownership and provenance.</p>
      <pre>{JSON.stringify({native_ids: session.native_ids, readiness: session.readiness, recording: session.recording,
        receipts: session.receipts, pending: session.pending_work}, null, 2)}</pre>
    </DialogContent>
  </Dialog>;
}

function ViewpointReview({session, onAction, busy}: any) {
  const [checked, setChecked] = useState(false);
  const geometry = session.project_state.overview_geometry || {};
  if (!geometry.requires_recheck || geometry.generic_reviewed_revision === geometry.revision) return null;
  return <Card className="settings-card"><h3>Workspace references need recheck</h3>
    <p>Spatial assumptions were invalidated. Keep pickup, release, target and fixed references visible.</p>
    {session.project_id === 'smart-swarm' ? <p>Finish and retain an interrupted attempt, then capture and confirm the station again.</p> : <>
      <label><input type="checkbox" checked={checked} onChange={event => setChecked(event.target.checked)}/>
        I checked the current camera framing.</label>
      <Button disabled={!checked || busy} onClick={() => onAction('review_viewpoint', {framing_checked: true})}>Confirm reframed view</Button>
    </>}
  </Card>;
}
