import { useEffect, useRef, useState } from 'react';
import { api, lab } from '@/lib/api';

export function useSimulation(robot: string, kind: string) {
  const [state, setState] = useState<any>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const owner = useRef(`homebrain-sim-${crypto.randomUUID()}`);
  const owned = useRef(false);
  const target = useRef<number[] | null>(null);
  const holding = useRef(false);
  const call = (command: string, arguments_: any = {}) => api(`${lab}/simulation/${kind}`, {command, arguments: {operator: owner.current, ...arguments_}});
  useEffect(() => installSimulation({kind, owner, owned, target, holding, setState, setError}), [kind, robot]);
  async function command(name: string) {
    setBusy(true); setError('');
    try {
      let result;
      if (name === 'start') {
        await call('start'); await call('claim'); owned.current = true;
        result = kind === 'individual'
          ? await call('profile', {profile: robot === 'so101' ? 'so101_pick_place_sim' : `${robot}_dock_sim`})
          : await call('select', {agent: robot});
      } else if (name === 'pause') {
        result = await call('release'); owned.current = false;
      } else result = await call(name, {seed: 0});
      if (name === 'close') owned.current = false;
      if (result.owner !== owner.current) owned.current = false;
      setState(result);
    } catch (failure) { setError(String(failure)); }
    finally { setBusy(false); }
  }
  function setTarget(index: number, value: number, initial: number[]) {
    const values = [...(target.current || initial)]; values[index] = value; target.current = values;
  }
  return {state, error, busy, command, owned: owned.current, holding, setTarget, target};
}

function installSimulation({kind, owner, owned, target, holding, setState, setError}: any) {
  const call = (command: string, values: any = {}) => api(`${lab}/simulation/${kind}`, {command, arguments: {operator: owner.current, ...values}});
  const stop = () => {
    holding.current = false; target.current = null;
    if (owned.current) { owned.current = false; call('release').catch(() => {}); }
  };
  let inFlight = false;
  const timer = setInterval(async () => {
    if (document.hidden || !document.hasFocus() || inFlight) return;
    inFlight = true;
    try {
      const value = owned.current
        ? await call(holding.current && target.current ? 'target' : 'heartbeat', target.current && holding.current ? {target: target.current} : {})
        : await api(`${lab}/simulation/${kind}`);
      setState(value);
      if (owned.current && value.owner !== owner.current) stop();
    } catch (failure) {
      if (owned.current) { stop(); setError(String(failure)); }
    } finally { inFlight = false; }
  }, 400);
  const visibility = () => { if (document.hidden) stop(); };
  const focus = () => {if (document.activeElement?.closest('.assistant-slot') || document.querySelector('[role=dialog]')) stop();};
  const observer = new MutationObserver(focus);
  observer.observe(document.body, {childList: true, subtree: true});
  document.addEventListener('focusin', focus);
  window.addEventListener('homebrain-stop-simulation', stop);
  window.addEventListener('blur', stop); document.addEventListener('visibilitychange', visibility);
  return () => {
    clearInterval(timer); observer.disconnect(); document.removeEventListener('focusin', focus); stop(); window.removeEventListener('homebrain-stop-simulation', stop); window.removeEventListener('blur', stop);
    document.removeEventListener('visibilitychange', visibility);
  };
}
