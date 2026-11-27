import { useEffect, useRef, useState } from 'react';
import { lab, type Session } from '@/lib/api';
import { tankKeys, robotKey, typing, standardPad, neutralPad, rosInput } from './controlMappings';
type Send = (value: unknown) => void;
type InputState = { keys: Set<string>; locked: Set<string>; padBlocked: boolean; buttons: Set<number> };
const modal = () => !!document.querySelector('[role="dialog"]');

export function useControl(session: Session | null) {
  const socket = useRef<WebSocket | null>(null); const precision = useRef(true);
  const [epoch, setEpoch] = useState(0);
  const [native, setNative] = useState<any>({}); const [connected, setConnected] = useState(false);
  useEffect(() => {
    if (!session || session.domain !== 'physical') return;
    const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${lab}/control/${session.session_id}`);
    let retry: ReturnType<typeof setTimeout>;
    socket.current = ws; ws.onopen = () => setConnected(true);
    ws.onclose = () => { setConnected(false); retry = setTimeout(() => setEpoch(value => value + 1), 2000); };
    ws.onmessage = event => { const message = JSON.parse(event.data); if (message.data) setNative(message.data); };
    const cleanup = installInputs(ws, session.robot_id, precision);
    return () => { ws.onclose = null; clearTimeout(retry); cleanup(); ws.close(); socket.current = null; setConnected(false); setNative({}); };
  }, [session?.session_id, epoch]);
  function send(packet: unknown) { if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify(packet)); }
  return { native, connected, send, clear: () => socket.current?.dispatchEvent(new Event('homebrain-release')), clearInputs: () => socket.current?.dispatchEvent(new Event('homebrain-clear-inputs')),
    setPrecision: (value: boolean) => { precision.current = value; } };
}

function keyHandler(state: InputState, send: Send, robot: string) {
  return (event: KeyboardEvent, pressed: boolean) => {
    if (!pressed) { state.keys.delete(event.code); state.locked.delete(event.code); }
    if (pressed && (event.code === 'Escape' || (event.code === 'Space' && !typing()))) {
      event.preventDefault(); state.keys.clear(); state.padBlocked = true; send({ kind:'clear' }); return;
    }
    if (pressed && (typing() || modal())) { state.locked.add(event.code); return; }
    if (state.locked.has(event.code)) return;
    if (pressed) state.keys.add(event.code);
    if (!robotKey(event.code, robot)) return;
    event.preventDefault();
    if (robot === 'tank') send({ kind:'key',key:tankKeys[event.code],source:'keyboard:'+event.code,pressed });
  };
}

function focusedInput(state: InputState, send: Send, robot: string, precision: React.RefObject<boolean>) {
  if (document.hidden || !document.hasFocus()) return;
  send({ kind:'heartbeat' });
  const blocked = typing() || modal(); const pad = standardPad();
  if (pad && neutralPad(pad) && !blocked) state.padBlocked = false;
  if (robot === 'rosmaster') send(rosInput(blocked ? new Set() : state.keys, state.padBlocked || blocked ? null : pad, precision.current));
  if (robot === 'rosmaster' && pad && !state.padBlocked && !blocked) presetButtons(state, pad, send);
  if (robot === 'tank' && pad && !state.padBlocked && !blocked) tankPad(pad, send);
  if (pad?.buttons[1]?.pressed && !state.padBlocked && !blocked) { state.keys.clear(); state.padBlocked = true; send({ kind:'clear' }); }
}

function installInputs(ws: WebSocket, robot: string, precision: React.RefObject<boolean>) {
  const state: InputState = { keys:new Set(),locked:new Set(),padBlocked:true,buttons:new Set() };
  const send: Send = value => { if (ws.bufferedAmount > 65536) ws.close();
    else if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(value)); };
  const clear = (release = false) => { state.keys.forEach(key => state.locked.add(key)); state.keys.clear(); state.padBlocked = true; send({ kind:release ? 'clear' : 'clear_inputs' }); };
  const handler = keyHandler(state, send, robot);
  const down = (event: KeyboardEvent) => handler(event,true); const up = (event: KeyboardEvent) => handler(event,false);
  const focus = () => { if (typing() || modal()) clear(); };
  const zero = () => clear();
  ws.addEventListener('homebrain-clear-inputs', zero);
  const loss = () => clear(true);
  ws.addEventListener('homebrain-release', loss); const visibility = () => { if (document.hidden) loss(); };
  const timer = setInterval(() => focusedInput(state,send,robot,precision),160);
  const observer = new MutationObserver(() => { if (modal()) clear(); });
  observer.observe(document.body,{ childList:true,subtree:true });
  window.addEventListener('keydown',down); window.addEventListener('keyup',up); window.addEventListener('blur',loss);
  window.addEventListener('gamepaddisconnected',loss); document.addEventListener('visibilitychange',visibility); document.addEventListener('focusin',focus);
  return () => { ws.removeEventListener('homebrain-clear-inputs', zero); ws.removeEventListener('homebrain-release', loss); clearInterval(timer); observer.disconnect(); loss(); window.removeEventListener('keydown',down); window.removeEventListener('keyup',up); window.removeEventListener('blur',loss); window.removeEventListener('gamepaddisconnected',loss); document.removeEventListener('visibilitychange',visibility); document.removeEventListener('focusin',focus); };
}

function tankPad(pad: Gamepad, send: Send) {
  const [x,y] = pad.axes;
  for (const [key,pressed] of Object.entries({ up:y < -.2,down:y > .2,left:x < -.2,right:x > .2 })) send({ kind:'key',key,source:'gamepad:'+key,pressed });
}

function presetButtons(state: InputState, pad: Gamepad, send: Send) {
  for (const [button, name] of [[0, 'look'], [2, 'carry']] as const) {
    const pressed = pad.buttons[button]?.pressed;
    if (pressed && !state.buttons.has(button)) send({kind: 'native_action', action: 'preset', name});
    if (pressed) state.buttons.add(button); else state.buttons.delete(button);
  }
}
