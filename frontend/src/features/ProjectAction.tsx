import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
const names: Record<string, string> = {
  capture_station: 'Capture current station views', begin_attended_check: 'Begin attended setup check',
  confirm_attended_check: 'Confirm framing, tracking and STOP', readiness: 'Check current readiness',
  confirm_station: 'Confirm witness sightlines', start: 'Prepare this story', start_recording: 'Start native recording',
  finish_recording: 'Finish and save recording', mark: 'Record an observation now', start_mobile: 'Start mobile evidence',
  grant_relocation: 'Grant relocation window', predict: 'Seal the decision', reveal: 'Reveal evaluator outcome',
  close_incomplete: 'Keep incomplete attempt', observe_pilot: 'Confirm observed placement',
  review_pilot: 'Review pilot receipts', review: 'Review admission receipts', refresh: 'Refresh native readback',
  freeze_study: 'Freeze the qualified study plan', reconcile: 'Reconcile native state',
};
const sightlines = ['tank_sees_initial_and_final', 'rosmaster_sees_destinations', 'top_sees_final_relation', 'scene_remains_on_table'];

export function ProjectAction({session, busy, onAction}: any) {
  const actions = session.permitted_actions.filter((name: string) => names[name]
    && !(name === 'start_recording' && session.recording.active) && !(name === 'finish_recording' && !session.recording.active));
  const [chosen, setChosen] = useState('');
  const [values, setValues] = useState<Record<string, any>>({assistance: 'unknown', outcome: 'unknown', observed_change: 'unknown'});
  const preferred = session.recording.active && actions.includes('mark') ? 'mark' : actions[0];
  const action = actions.includes(chosen) ? chosen : preferred;
  const set = (name: string, value: any) => setValues(old => ({...old, [name]: value}));
  const captures = session.project_state.homebrain_operations || [];
  const sha = captures.find((row: any) => row.native_acknowledgement?.views)?.native_acknowledgement.sha256;
  const phase = session.project_state.required_phase || (session.state === 'relocation' ? 'relocation_closed' : 'placement_closed');
  const timing = session.project_state.phase_timing;
  const disabled = busy || !action || (session.pending_work.length > 0 && action !== 'reconcile')
    || (action === 'mark' && session.recording.state !== 'recording')
    || (action === 'grant_relocation' && timing && !timing.ready) || (action === 'freeze_study' && !values.freeze_reviewed);
  return <Card className="project-actions"><div className="list-heading"><h3>Protocol action</h3>
    <select aria-label="Current project action" value={action || ''} onChange={event => setChosen(event.target.value)}>
      {actions.map((name: string) => <option key={name} value={name}>{names[name]}</option>)}
    </select></div>
    <ProtocolFields {...{action, values, set, phase, session, sha}}/>
    {timing && <p className="phase-countdown">
      {timing.hold_seconds > 0 ? `Keep the scene still · ${timing.hold_seconds} s lead-in remaining` : `${timing.seconds_remaining} s left in native capture`}
      · {timing.reason || 'Relocation window ready'}</p>}
    <div className="protocol-footer"><span>Project receipts govern phase progress.</span>
      <Button disabled={disabled} onClick={() => onAction(action, argumentsFor(action, values, phase, sha, session))}>
        {names[action] || 'Awaiting project readback'}</Button>
    </div>
  </Card>;
}

function argumentsFor(action: string, values: any, phase: string, sha: string, session: any) {
  if (action === 'start_recording') return {explicit_user_start: true};
  if (action === 'confirm_attended_check') return {framing_tracking_stop_confirmed: values.attended === true};
  if (action === 'mark') return {phase, assistance: values.assistance, placement_outcome: values.outcome,
    ...(phase === 'relocation_closed' || session.project_state.phase_family === 'F3' ? {observed_change: values.observed_change} : {})};
  if (action === 'reveal') return {outcome: values.terminal || 'unknown', relations_preserved: values.preserved === true};
  if (action === 'observe_pilot') return {outcome: values.outcome, assistance: values.assistance};
  if (action === 'close_incomplete') return {reason: values.reason || 'Operator ended this incomplete attempt'};
  if (action === 'confirm_station') return {...Object.fromEntries(sightlines.map(key => [key, values[key] === true])), framing_receipt_sha256: sha};
  return {};
}

function ProtocolFields({action, values, set, phase, session, sha}: any) {
  if (['mark', 'observe_pilot'].includes(action)) return <ObservationFields {...{action, values, set, phase, session}}/>;
  if (action === 'confirm_attended_check') return <Check label="I observed framing, native leader tracking and the physical STOP procedure in this check."
    checked={values.attended} set={(value: boolean) => set('attended', value)}/>;
  if (action === 'confirm_station') return <div className="protocol-fields">
    {sightlines.map(key => <Check key={key} label={key.replaceAll('_', ' ')} checked={values[key]} set={(value: boolean) => set(key, value)}/>)}
    {!sha && <p>Capture station views first. This confirmation binds to that receipt.</p>}
  </div>;
  if (action === 'reveal') return <>
    <Field label="Evaluator observation" value={values.terminal || 'unknown'} options={['unknown', 'left', 'right', 'surface', 'held', 'outside']}
      set={value => set('terminal', value)}/>
    <Check label="Relation stayed fixed until evaluator reveal." checked={values.preserved} set={(value: boolean) => set('preserved', value)}/>
  </>;
  if (action === 'close_incomplete') return <input aria-label="Reason for incomplete attempt" value={values.reason || ''}
    placeholder="What interrupted this attempt?" onChange={event => set('reason', event.target.value)}/>;
  if (action === 'freeze_study') return <>
    <p>The project requires a current qualified station and four verified development histories per family. Its frozen allocation and model/protocol identity become immutable.</p>
    <Check label="I reviewed the project receipts and am releasing the qualified study plan." checked={values.freeze_reviewed}
      set={(value: boolean) => set('freeze_reviewed', value)}/>
  </>;
  return null;
}

function ObservationFields({action, values, set, phase, session}: any) {
  return <div className="protocol-fields">
    {action === 'mark' && <strong>Observe now: {phase.replaceAll('_', ' ')}</strong>}
    <Field label="Placement outcome" value={values.outcome} options={['unknown', 'placement_succeeded', 'placement_failed']} set={value => set('outcome', value)}/>
    <Field label="Assistance at this event" value={values.assistance}
      options={['unknown', 'none', 'human_hand_assistance', 'human_relocation', 'attended_native_motion']} set={value => set('assistance', value)}/>
    {(phase === 'relocation_closed' || session.project_state.phase_family === 'F3') &&
      <Field label="Directly observed change" value={values.observed_change} options={['unknown', 'confirmed', 'different']} set={value => set('observed_change', value)}/>}
  </div>;
}

function Check({label, checked, set}: any) {
  return <label><input type="checkbox" checked={!!checked} onChange={event => set(event.target.checked)}/> {label}</label>;
}

function Field({label, value, options, set}: {label: string; value: string; options: string[]; set: (value: string) => void}) {
  return <label>{label}<select value={value} onChange={event => set(event.target.value)}>
    {options.map(option => <option key={option} value={option}>{option.replaceAll('_', ' ')}</option>)}
  </select></label>;
}
