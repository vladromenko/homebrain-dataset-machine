let enabled = false;
let active: AudioBufferSourceNode | null = null;
let context: AudioContext | null = null;
export function enableSpeech() {
  enabled = true; context ||= new AudioContext();
  return context.resume();
}
export async function speak(text: string) {
  if (!enabled || !context || context.state !== 'running') return;
  const response = await fetch('/api/speak', { method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text.slice(0,1800)}) });
  if (!response.ok) throw new Error('Local English speech is unavailable');
  const buffer = await context.decodeAudioData(await response.arrayBuffer());
  const source = context.createBufferSource(); source.buffer=buffer; source.connect(context.destination); source.start(); active = source;
}

export function stopSpeech() {
  try { active?.stop(); } catch {}
  active = null;
}

export function muteSpeech() {
  enabled = false; stopSpeech();
  window.dispatchEvent(new Event('homebrain-mute-speech'));
}
