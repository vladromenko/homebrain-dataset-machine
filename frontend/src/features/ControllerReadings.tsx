import { Card } from '@/components/ui/card';

export function ControllerReadings({readback}: any) {
  const data = readback?.data || {};
  const sample = data.sample || {};
  const rows = [
    ['Measured joint state', data.measured_joints, 'Native measured channels'],
    ['Measured arm positions', data.arm_measured, 'Native measured channels'],
    ['Native arm display', data.arm, 'Native command/display; distinct from measured feedback'],
    ['State vector', sample['observation.state'], sample.state_kind || 'Native state semantics'],
    ['State validity', sample.state_valid, 'Native validity flag'],
    ['Voltage', data.battery?.volts ?? sample.battery_voltage, sample.battery_source || 'Native volts'],
    ['IMU', sample.imu_raw, 'Native raw units'],
    ['TCP', data.tcp, 'Native kinematic estimate'],
  ].filter(([, value]) => value != null && (!Array.isArray(value) || value.length));
  return <Card className="settings-card"><h2>Native controller readings</h2>
    <p>{readback?.source || 'No controller packet has been received in this application session.'}</p>
    {readback?.cache_age_ms != null && <p>Last packet received {(readback.cache_age_ms / 1000).toFixed(1)} s ago.</p>}
    <p className="muted">{readback?.sensor_clock || 'Sensor measurement age is unknown.'} Channel units are retained from the native source.</p>
    {rows.length ? <table><thead><tr><th>Channel</th><th>Value</th><th>Provenance</th></tr></thead>
      <tbody>{rows.map(([name, value, source]) => <tr key={String(name)}>
        <td>{name}</td><td>{JSON.stringify(value)}</td><td>{source}</td>
      </tr>)}</tbody></table> : <p>Measured values are currently unavailable in this native readback.</p>}
  </Card>;
}
