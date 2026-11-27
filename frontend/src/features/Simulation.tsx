import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useSimulation } from './useSimulation';

export function Simulation({robot}: {robot: string}) {
  const [kind, setKind] = useState('individual');
  const sim = useSimulation(robot, kind);
  const state = sim.state;
  return <Card className="settings-card simulation">
    <div className="list-heading"><Badge variant="secondary">SIMULATION ONLY</Badge>
      <select value={kind} onChange={event => setKind(event.target.value)} aria-label="Simulation world">
        <option value="individual">Individual robot</option><option value="shared">Shared world</option>
      </select></div>
    <h2>Native MuJoCo · {robot.toUpperCase()}</h2>
    <p>Existing models and worker. Dynamics are not hardware calibrated. Shared-world recording is unsupported.</p>
    {state?.rgb && <img className="simulation-frame" src={`data:image/jpeg;base64,${state.rgb}`} alt="Native simulated view"/>}
    <SimulationActions sim={sim} kind={kind}/>
    <Targets sim={sim} kind={kind} robot={robot}/>
    {sim.error && <p role="alert">{sim.error}</p>}
    <p className="muted">Control releases on focus loss. Open simulation again to reclaim it. Simulated evidence is separate from physical data.</p>
  </Card>;
}

function SimulationActions({sim, kind}: any) {
  const actions = ['start', 'pause', 'reset', 'demonstrate', ...(kind === 'individual' ? ['record', 'finish'] : ['snapshot', 'restore']), 'close'];
  const names: Record<string, string> = {start: 'Open simulation', pause: 'Release control', close: 'Close simulation'};
  return <div className="robot-tabs">{actions.map(action =>
    <Button key={action} variant={action === 'start' ? 'default' : 'outline'}
      disabled={sim.busy || (action !== 'start' && action !== 'close' && !sim.owned)} onClick={() => sim.command(action)}>
      {names[action] || action.charAt(0).toUpperCase() + action.slice(1)}
    </Button>)}</div>;
}

function Targets({sim, kind, robot}: any) {
  const state = sim.state;
  const view = kind === 'individual' ? state : state?.world?.robots?.[robot];
  const limits = view?.limits;
  if (!limits || !sim.owned || state?.requested_profile) return null;
  const initial = kind === 'individual' ? state.target : robot === 'so101' ? view.observation : limits[0].map(() => 0);
  return <div className="sim-targets"><h3>Manual model targets</h3>
    <p>Adjust a channel and hold Apply targets. Releasing pauses input after the native timeout.</p>
    {limits[0].map((low: number, index: number) => <label key={index}>Channel {index + 1}
      <input type="range" min={low} max={limits[1][index]} step={(limits[1][index] - low) / 200}
        defaultValue={initial?.[index] ?? 0} onChange={event => sim.setTarget(index, Number(event.target.value), initial)}/>
    </label>)}
    <Button onPointerDown={() => {sim.target.current ||= initial; sim.holding.current = true;}}
      onPointerUp={() => {sim.holding.current = false;}} onPointerLeave={() => {sim.holding.current = false;}}>
      Hold to apply targets
    </Button>
  </div>;
}
