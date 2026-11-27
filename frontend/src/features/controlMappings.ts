// Mappings mirror the installed Explorer native console; transport retains native limits.
const rosKeys: Record<string, [number, number, number]> = { KeyW:[0,0,1],KeyS:[0,0,-1],KeyA:[0,1,1],KeyD:[0,1,-1],KeyQ:[0,2,1],KeyE:[0,2,-1],KeyI:[1,0,1],KeyK:[1,0,-1],KeyJ:[1,1,1],KeyL:[1,1,-1],KeyR:[1,2,1],KeyF:[1,2,-1],ArrowUp:[1,0,1],ArrowDown:[1,0,-1],ArrowLeft:[1,1,1],ArrowRight:[1,1,-1] };
export const tankKeys: Record<string, string> = { KeyW:'up',KeyS:'down',KeyA:'left',KeyD:'right',ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right' };
export const robotKey = (code: string, robot: string) => robot === 'tank' ? !!tankKeys[code] : code in rosKeys || ['Comma','Period','BracketLeft','BracketRight','KeyN','KeyM'].includes(code);
export const typing = () => { const element = document.activeElement as HTMLElement | null; return !!element && (['INPUT','TEXTAREA','SELECT'].includes(element.tagName) || element.isContentEditable); };
export const standardPad = () => Array.from(navigator.getGamepads?.() || []).find(pad => pad?.mapping === 'standard') || null;
export const neutralPad = (pad: Gamepad) => pad.axes.every(value => Math.abs(value) < .12) && pad.buttons.every(button => !button.pressed && button.value < .12);

export function rosInput(keys: Set<string>, pad: Gamepad | null, precision: boolean) {
  const axes = [[0,0,0],[0,0,0]];
  for (const key of keys) { const mapping = rosKeys[key]; if (mapping) axes[mapping[0]][mapping[1]] += mapping[2]; }
  let pitch = Number(keys.has('Period'))-Number(keys.has('Comma'));
  const roll = Number(keys.has('BracketRight'))-Number(keys.has('BracketLeft'));
  let grip = Number(keys.has('KeyM'))-Number(keys.has('KeyN'));
  if (pad) {
    const axis = (index: number) => Math.abs(pad.axes[index] || 0) < .12 ? 0 : pad.axes[index];
    const button = (index: number) => Number(pad.buttons[index]?.pressed || false);
    axes[0][0] -= axis(1); axes[0][1] -= axis(0); axes[0][2] += button(4)-button(5);
    axes[1][1] -= axis(2); axes[1][0] -= axis(3); axes[1][2] += button(12)-button(13);
    pitch += button(15)-button(14); grip += (pad.buttons[7]?.value || 0)-(pad.buttons[6]?.value || 0);
  }
  const cap = (value: number) => Math.max(-1, Math.min(1, value));
  return { kind:'input',drive:axes[0].map(cap),arm:axes[1].map(cap),pitch:cap(pitch),roll:cap(roll),grip:cap(grip),slow:precision || keys.has('ShiftLeft') || keys.has('ShiftRight') };
}
