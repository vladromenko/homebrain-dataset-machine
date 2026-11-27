import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ControllerReadings } from './ControllerReadings';
import { Simulation } from './Simulation';
import { api, lab } from '@/lib/api';

export function RobotViews({overview}: any) {
  const [robot, setRobot] = useState('so101');
  const capability = overview?.robots.find((row: any) => row.robot_id === robot);
  return <div className="projects"><div className="eyebrow">NATIVE CAPABILITIES</div><h1>Robots & their workspace</h1>
    <div className="robot-tabs">{['so101', 'tank', 'rosmaster'].map(id =>
      <Button key={id} variant={robot === id ? 'default' : 'outline'} onClick={() => setRobot(id)}>{id.toUpperCase()}</Button>)}</div>
    <Tabs defaultValue="control"><TabsList>
      <TabsTrigger value="control">Control</TabsTrigger><TabsTrigger value="sensors">Sensors & models</TabsTrigger>
      <TabsTrigger value="simulation">Simulation</TabsTrigger></TabsList>
      <TabsContent value="control"><Capability robot={robot} capability={capability}/></TabsContent>
      <TabsContent value="sensors"><Sensors robot={robot} capability={capability}/></TabsContent>
      <TabsContent value="simulation"><Simulation key={robot} robot={robot}/></TabsContent>
    </Tabs>
  </div>;
}

function Capability({robot, capability}: any) {
  return <Card className="settings-card"><Badge variant="outline">PHYSICAL · {capability?.native_owner}</Badge>
    <h2>{robot.toUpperCase()}</h2><p>Choose a recording task in Projects to prepare and explicitly enable this robot.</p>
    <p>Inputs: {capability?.inputs.join(' · ')}</p><p>Recorder: {capability?.recorders.join(' · ')}</p>
    <p className="muted">Unsupported: {capability?.unsupported.join(' · ')}</p>
    <details><summary>Advanced native recovery consoles</summary>
      <p><a href="http://homebrain.local:8020" target="_blank" rel="noreferrer">Studio native console</a> ·{' '}
        <a href="http://homebrain.local:8030" target="_blank" rel="noreferrer">Explorer native console</a> ·{' '}
        <a href="http://homebrain.local:8030/fleet/live" target="_blank" rel="noreferrer">Native ROS2 observations</a></p>
      <p>These are the existing local network services with their original access checks.</p>
    </details>
  </Card>;
}

function Sensors({robot, capability}: any) {
  const [hub, setHub] = useState<any>(null);
  useEffect(() => {
    const refresh = () => api(`${lab}/sensors`).then(setHub).catch(error => setHub({error: String(error)}));
    refresh(); const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, []);
  const observed = hub?.data?.robots?.[robot];
  return <div className="sensor-grid"><Card className="settings-card"><h2>Sensor & model provenance</h2>
    {capability?.cameras.map((camera: any) => <p key={camera.role}><strong>{camera.role}</strong> · {camera.source} ·
      {camera.age_ms == null ? ' Freshness readback required' : ` ${Math.round(camera.age_ms)} ms`}</p>)}
    <p>World transform: unknown until measured calibration is supplied.</p>
    <p>{robot === 'tank' ? 'Tank state is a previous command estimate. Wheel odometry is unavailable.' :
      'Measured feedback and command targets retain their native meanings.'}</p>
    <p>MuJoCo geometry: existing native CAD/model. Dynamics: simulated and uncalibrated.</p>
    <details><summary>Configured native profile parameters</summary>
      <p>These settings are configured by the native owner; they are not measured physical/model calibration.</p>
      <pre>{JSON.stringify(capability?.sensors || [], null, 2)}</pre>
    </details>
  </Card><Card className="settings-card"><h2>Namespaced ROS2 observations</h2>
    <p>Read-only · domain 73 · native source clocks · no motor commands</p>
    {observed ? <SensorTable observed={observed}/> : <p>{hub?.error || 'No namespaced observation is currently available for this robot.'}</p>}
    <details><summary>Native diagnostics</summary><pre>{JSON.stringify(hub, null, 2)}</pre></details>
  </Card><ControllerReadings readback={hub?.controller_readbacks?.[robot]}/></div>;
}

function SensorTable({observed}: any) {
  return <table><thead><tr><th>Stream</th><th>Frame</th><th>Age</th></tr></thead>
    <tbody>{Object.entries(observed.ages_s || {}).map(([name, age]: any) => <tr key={name}>
      <td>{name}</td><td>{observed.source_frames?.[name] || 'unknown'}</td>
      <td>{age == null ? 'unavailable' : `${Number(age).toFixed(2)} s${age > .5 ? ' · stale' : ''}`}</td>
    </tr>)}</tbody>
  </table>;
}
