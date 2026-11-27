import { useState } from 'react';
import { Bot, ChevronLeft, Radio, ShieldCheck, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api, lab, type Task } from '@/lib/api';
import { Workspace } from '@/features/Workspace';
import { Assistant } from '@/features/Assistant';
import { useControl } from '@/features/useControl';
import { RobotViews } from '@/features/RobotViews';
import { Advisories } from '@/features/Advisories';
import { Records } from '@/features/Records';
import { Projects, SettingsView, Navigation } from './Navigation';
import { useAction, useOverview, useSession, useTasks } from './useWorkspace';

export function App() {
  const [page, setPage] = useState('Projects');
  const [chat, setChat] = useState(true);
  const [project, setProject] = useState('demonstrations');
  const [group, setGroup] = useState('');
  const data = useOverview();
  const selected = useSession();
  const { session, setSession } = selected;
  const tasks = useTasks(project, group);
  const control = useControl(page === 'Projects' ? session : null);
  const actions = useAction(session, setSession, data.setError);
  async function select(task: Task) {
    control.clear();
    try { selected.retain(await api(`${lab}/select`, { project_id: project, task_id: task.task_id })); }
    catch (failure) { data.setError(String(failure)); }
  }
  const props = { page, project, group, setGroup, setProject, tasks, session, setSession,
    select, overview: data.overview, control, actions, retain: selected.retain };
  return <div className={`app-shell ${chat ? 'with-chat' : ''}`}>
    <Navigation page={page} connected={!!data.overview} onPage={(value: string) => { control.clear(); setPage(value); }}/>
    <div className="app-body">
      <Header page={page} session={session} control={control} toggleChat={() => setChat(!chat)} setError={data.setError}/>
      <Notice message={data.error || tasks.error || selected.error} dismiss={() => data.setError('')}/>
      <Advisories/><main><Page {...props}/></main><Footer/>
    </div>
    <div className={chat ? 'assistant-slot' : 'assistant-slot assistant-hidden'}>
      <Assistant session={session} onClose={() => setChat(false)}/>
    </div>
  </div>;
}

function Header({ page, session, control, toggleChat, setError }: any) {
  function stop() {
    control.clear(); window.dispatchEvent(new Event('homebrain-stop-simulation'));
    const robots = session ? [session.robot_id] : ['so101', 'tank', 'rosmaster'];
    robots.forEach((robot: string) => api(`${lab}/stop/${robot}`, {}).catch(error => setError(String(error))));
  }
  return <header className="topbar">
    <div><span className="breadcrumb">Workspace</span><span>/</span><strong>{page}</strong></div>
    <div>
      <Badge variant="outline"><Radio size={11}/> LOCAL</Badge>
      <Button variant="ghost" size="icon" aria-label="Toggle assistant"
        onClick={() => { control.clearInputs(); toggleChat(); }}><Bot size={19}/></Button>
      <Button variant="destructive" className="stop" onClick={stop}>
        <Square size={13} fill="currentColor"/> STOP
      </Button>
    </div>
  </header>;
}

function Page(props: any) {
  const { page, session, tasks, overview, control, actions, setSession } = props;
  if (page === 'Robots') return <RobotViews overview={overview}/>;
  if (['Recordings', 'Jobs'].includes(page)) return <Records kind={page} overview={overview}/>;
  if (page === 'Settings') return <SettingsView session={session}/>;
  if (!session) return <Projects {...props}/>;
  return <>
    <Button variant="ghost" size="sm" className="back"
      onClick={() => { control.clear(); setSession(null); }}><ChevronLeft size={14}/> Task queue</Button>
    <Workspace session={session} task={tasks.find(session.task_id)} overview={overview}
      control={control} busy={actions.busy} onAction={actions.act}/>
  </>;
}

function Notice({ message, dismiss }: any) {
  if (!message) return null;
  return <div role="alert" className="notice error">{message}
    <button onClick={dismiss} aria-label="Dismiss message">×</button>
  </div>;
}

function Footer() {
  return <footer className="app-footer"><ShieldCheck size={13}/>
    Native controllers own motion and recording.<span>homebrain.lab.v1</span>
  </footer>;
}
