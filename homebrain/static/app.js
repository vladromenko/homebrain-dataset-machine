const $ = id => document.getElementById(id);
let project='smart-swarm', speaking=null, recording=null, media=null, browserCamera=null, frameTimer=null, pollTimer=null, discardRecording=false, speechVersion=0, handsfreeVersion=0;
async function api(path,body,method='POST') {
  const response=await fetch(path,{method:body===undefined?'GET':method,headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok) throw new Error((await response.text()).slice(0,300));
  return response.json();
}
function message(role,text='') {
  const welcome=document.querySelector('.welcome'); if(welcome) welcome.remove();
  const item=document.createElement('div');item.className='message '+role;item.textContent=text;$('messages').append(item);return item;
}
async function login() {
  try{await api('/api/login',{token:$('token').value});location.hash='';await initialize();}
  catch(error){$('login-error').textContent='Unable to authenticate. Check your private access token.';}
}
async function initialize() {
  const data=await api('/api/status?project='+project);
  $('login').hidden=true;$('application').hidden=false;renderStatus(data);
  const history=await api('/api/history');if(history.length){$('messages').replaceChildren();history.forEach(h=>message(h.role,h.text));}
  if(!pollTimer) pollTimer=setInterval(refresh,5000);refreshCamera();
}
async function refresh() {try{renderStatus(await api('/api/status?project='+project));refreshCamera();await refreshEvents();}catch(error){$('activity').textContent='Connection interrupted · retrying';}}
async function refreshEvents(){if($('active-session').checked){const rows=await api('/api/events');$('events').replaceChildren();for(const row of rows){const item=document.createElement('div');item.textContent=row.text;const button=document.createElement('button');button.textContent='Acknowledge';button.onclick=()=>api('/api/events/'+row.id+'/acknowledge',{});item.append(button);$('events').append(item);if($('spoken').checked&&!sessionStorage.getItem(row.id)){sessionStorage.setItem(row.id,'spoken');await speak(row.text);}}}}
function refreshCamera() {$('camera').src='/api/camera.jpg?t='+Date.now();}
function renderStatus(data) {
  const camera=data.camera,scene=camera.scene,mic=data.microphones,r=data.resources;const selection=$('project').value;$('project').replaceChildren(...data.projects.map(p=>new Option(p,p)));$('project').value=project;
  $('camera-state').textContent=camera.state;$('resolution').textContent=(scene.resolution||[]).join(' × ')+' · '+(camera.source||'waiting');
  $('camera-guidance').textContent=scene.guidance||scene.status;$('geometry').textContent=scene.geometry_valid?'Verified':'Unavailable';$('markers').textContent=(scene.markers||[]).length+' visible';
  $('mic-state').textContent=mic.state;const selected=$('mic-select').value;
  $('mic-select').replaceChildren(...mic.devices.map(d=>new Option(d.name,d.id)));if(selected)$('mic-select').value=selected;
  $('memory-number').textContent=r.available_gb;$('memory-bar').style.width=(r.available_gb/r.total_gb*100)+'%';$('model').textContent=r.model+' · '+(r.gpu_layers?'GPU':'CPU');
  const native=data.project.live.data;$('recording').textContent=native.recording?.active?'Active · inference yields':data.project.live.unavailable?'Unavailable':'Idle';
  const activeTraining=(native.jobs||[]).filter(j=>j.kind==='train'&&['running','starting'].includes(j.state));$('training').textContent=activeTraining.length?activeTraining.map(j=>j.state).join(', '):'No active training in native response';$('admissions').textContent=String(data.project.intake.data?.counts?.accepted_motor??'Unavailable')+' · historical pilot';$('status-detail').textContent=JSON.stringify({readiness:data.readiness,project:data.project},null,2);$('instruction').textContent=data.guidance?.instruction||'No project recording card is available.';
}
async function send(text) {
  if(!text.trim())return;message('user',text);$('message').value='';$('send').disabled=true;$('activity').textContent='Reading tools and sources…';
  const item=message('assistant');let result='';
  try {
    const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,project,session:'operator'})});
    if(!response.ok)throw new Error('Chat unavailable: '+response.status);
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
    while(true){const part=await reader.read();if(part.done){return await finish();}buffer+=decoder.decode(part.value,{stream:true});const lines=buffer.split('\n');buffer=lines.pop();for(const line of lines){if(line){const event=JSON.parse(line);if(event.role){$('activity').textContent=event.role+' · interpreting sources';}if(event.project){project=event.project;$('project').value=project;}result+=event.token||event.text||'';item.textContent=result;item.dataset.kind=event.kind?'Project record / tool result':'AI interpretation · verify against sources';if(event.sources?.length){const cite=document.createElement('small');cite.className='source';cite.textContent='Sources: ';event.sources.forEach(source=>{const link=document.createElement('a');link.href='/api/source?path='+encodeURIComponent(source.path);link.target='_blank';link.rel='noopener';link.textContent=source.path.split('/').pop()+' ';cite.append(link);});item.append(cite);}}}$('messages').scrollTop=$('messages').scrollHeight;}
  } catch(error){item.textContent+='\n'+error.message;await finish();}
  async function finish(){$('send').disabled=false;$('activity').textContent='Ready when you are';if($('spoken').checked&&result)await speak(result);}
}
async function speak(text) {
  stopSpeech();const version=speechVersion;const response=await fetch('/api/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text.slice(0,1800),speed:Number($('speed').value)})});
  if(response.ok&&version===speechVersion){const url=URL.createObjectURL(await response.blob());speaking=new Audio(url);speaking.volume=Number($('volume').value);speaking.onended=()=>URL.revokeObjectURL(url);await speaking.play().catch(()=>{$('transcript').textContent='Click a voice control to permit browser audio playback.';});}
}
function stopSpeech(){speechVersion++;if(speaking){speaking.pause();speaking=null;}}
async function browserMic() {
  if(recording){recording.stop();$('browser-mic').textContent='◉ Mac push-to-talk';return;}
  stopSpeech();discardRecording=false;media=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false});
  const chunks=[];recording=new MediaRecorder(media);recording.ondataavailable=event=>chunks.push(event.data);
  recording.onstop=async()=>{media.getTracks().forEach(t=>t.stop());recording=null;if(discardRecording){discardRecording=false;return;}const response=await fetch('/api/transcribe',{method:'POST',body:new Blob(chunks)});const result=await response.json();$('transcript').textContent=result.text||'No speech detected';if(result.text)await send(result.text);};
  recording.start();const currentRecording=recording;$('browser-mic').textContent='■ Finish speaking';setTimeout(()=>{if(recording===currentRecording){recording.stop();$('browser-mic').textContent='◉ Mac push-to-talk';}},20000);
}
async function localMic(){stopSpeech();$('transcript').textContent='Listening to the authorized C920 for 8 seconds…';const result=await api('/api/microphone/capture',{});$('transcript').textContent=result.text||'No speech detected';if(result.text)await send(result.text);}
async function useBrowserCamera(){
  if(browserCamera){clearInterval(frameTimer);browserCamera.getTracks().forEach(t=>t.stop());browserCamera=null;$('browser-camera').textContent='Use Mac overview camera';return;}
  browserCamera=await navigator.mediaDevices.getUserMedia({video:{width:1280,height:720,frameRate:5},audio:false});const video=document.createElement('video');video.srcObject=browserCamera;await video.play();
  const canvas=document.createElement('canvas');canvas.width=1280;canvas.height=720;frameTimer=setInterval(()=>{canvas.getContext('2d').drawImage(video,0,0,1280,720);canvas.toBlob(blob=>fetch('/api/browser-frame',{method:'POST',headers:{'X-Captured-At':String(Date.now())},body:blob}),'image/jpeg',.75);},1000);$('browser-camera').textContent='Stop Mac camera';
}
async function memories(){const rows=await api('/api/memory');$('memories').replaceChildren();for(const row of rows){const div=document.createElement('div');div.textContent=row.scope+': '+row.text+' · unverified';const button=document.createElement('button');button.textContent='Confirm removal';button.onclick=async()=>{await api('/api/memory/'+row.id+'?confirmed=true',{},'DELETE');await memories();};div.append(button);$('memories').append(div);}}
function safe(action){return async(...args)=>{try{await action(...args);}catch(error){$('transcript').textContent=error.message;}};}
$('connect').onclick=login;$('chat-form').onsubmit=event=>{event.preventDefault();send($('message').value);};
$('message').onkeydown=event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send($('message').value);}};
document.querySelectorAll('[data-prompt]').forEach(button=>button.onclick=()=>send(button.dataset.prompt));
$('project').onchange=()=>{project=$('project').value;message('assistant','Switched to '+project+'. Tools will use this project.');refresh();};
$('browser-mic').onclick=safe(browserMic);$('local-mic').onclick=safe(localMic);$('browser-camera').onclick=safe(useBrowserCamera);
$('authorize').onclick=safe(async()=>{await api('/api/microphone/authorize',{device:$('mic-select').value,confirmed:true});refresh();});
$('mute').onclick=safe(async()=>{$('handsfree').checked=false;await api('/api/microphone/mute',{});if(recording){discardRecording=true;recording.stop();}refresh();});
$('repeat').onclick=()=>send('Repeat the previous instruction.');$('pause').onclick=()=>send('pause');$('next-card').onclick=()=>send('What should I record next?');$('next-step').onclick=()=>send('next instruction');$('stop-speech').onclick=stopSpeech;
$('camera').onload=()=>{$('camera-empty').hidden=true;};$('camera').onerror=()=>{$('camera-empty').hidden=false;};
$('memory-open').onclick=safe(async()=>{await memories();$('memory-dialog').showModal();});$('memory-close').onclick=()=>$('memory-dialog').close();
$('memory-save').onclick=safe(async()=>{await api('/api/memory',{scope:$('memory-scope').value,text:$('memory-text').value,confirmed:true});$('memory-text').value='';await memories();});
$('memory-export').onclick=safe(async()=>{const data=await api('/api/export');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download='homebrain-memory.json';a.click();URL.revokeObjectURL(a.href);});
if(location.hash.startsWith('#token=')){$('token').value=decodeURIComponent(location.hash.slice(7));login();}else{initialize().catch(()=>{});}

$('active-session').onchange=safe(async()=>{await api('/api/session/active',{confirmed:$('active-session').checked});});

$('volume').oninput=()=>{if(speaking)speaking.volume=Number($('volume').value);};

async function handsFree(version){
  stopSpeech();
  while($('handsfree').checked&&version===handsfreeVersion){
    try{
      const result=await api('/api/microphone/capture',{});
      if($('handsfree').checked&&version===handsfreeVersion&&result.wake_command){$('transcript').textContent=result.text;await send(result.wake_command);}
      while($('handsfree').checked&&speaking&&!speaking.paused&&!speaking.ended){await new Promise(resolve=>setTimeout(resolve,200));}
    }catch(error){$('transcript').textContent='Hands-free recovering: '+error.message;await new Promise(resolve=>setTimeout(resolve,2000));}
  }
}
$('handsfree').onchange=()=>{handsfreeVersion++;if($('handsfree').checked)handsFree(handsfreeVersion);else api('/api/microphone/mute',{}).catch(()=>{});};
