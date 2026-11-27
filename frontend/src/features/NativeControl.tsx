import { useState } from 'react';
import { Button } from '@/components/ui/button';

export function NativeControl({robot, control}: any) {
  return <div className="native-control">
    <strong>{control.connected ? 'Direct native input connected' : 'Native input disconnected'}</strong>
    {robot === 'so101' ? <p>Use the calibrated physical leader arm. Native control owns joint limits, tracking and torque.</p> :
      robot === 'tank' ? <p>WASD / arrows or a standard gamepad. Reverse arcs and speed limits use the native Tank controller.</p> :
      <RosmasterControl control={control}/>}
    <p className="muted">Escape clears control. Return the gamepad to neutral after focus loss. Native calibration remains authoritative.</p>
  </div>;
}

function RosmasterControl({control}: any) {
  const [precision, setPrecision] = useState(true);
  const send = (action: string, values: any = {}) => control.send({kind: 'native_action', action, ...values});
  return <>
    <p>WASD + Q/E: base · IJKL/RF or arrows: arm · , . [ ]: wrist · N/M: gripper.</p>
    <div className="native-controls">
      <Button variant="outline" size="sm" onClick={() => send('arm_mode', {mode: 'cartesian'})}>Cartesian arm</Button>
      <Button variant="outline" size="sm" onClick={() => send('arm_mode', {mode: 'joint'})}>Joint arm</Button>
      <Button variant="outline" size="sm" onClick={() => send('leader')}>Connect leader</Button>
      <Button variant="outline" size="sm" onClick={() => send('mirror', {on: true})}>Enable mirror</Button>
      <Button variant="outline" size="sm" onClick={() => send('mirror', {on: false})}>Stop mirror</Button>
      <Button variant="outline" size="sm" onClick={() => {setPrecision(!precision); control.setPrecision(!precision);}}>
        {precision ? 'Precision speed' : 'Normal speed'}</Button>
    </div>
    <p className="muted">Gamepad: left stick base, shoulders yaw, right stick arm, D-pad height/pitch, triggers gripper, B stops.</p>
  </>;
}
