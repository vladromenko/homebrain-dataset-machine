import { Boxes, Camera, CircleHelp, FolderOpen, Layers3, Settings, Workflow, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { VoiceSettings } from '@/features/VoiceSettings';
import { type Session, type Task } from '@/lib/api';

export function Navigation({ page, onPage, connected }: any) {
  const items = [[FolderOpen, 'Projects'], [Boxes, 'Robots'], [Camera, 'Recordings'], [Workflow, 'Jobs']] as const;
  return <nav className="sidebar">
    <a className="brand" href="/lab"><span><Layers3 size={21}/></span><div>homebrain<small>LAB WORKSPACE</small></div></a>
    <div className="nav-label">LABORATORY</div>
    {items.map(([Icon, title]) => <button className={page === title ? 'active' : ''}
      key={title} onClick={() => onPage(title)}><Icon size={17}/>{title}</button>)}
    <div className="sidebar-bottom">
      <div className="local-note"><span className={`status-dot ${connected ? '' : 'warning'}`}/>
        {connected ? 'Homebrain connected' : 'Connecting to Homebrain'}<small>Private · local connection</small></div>
      <button onClick={() => onPage('Settings')}><Settings size={17}/> Settings</button>
      <a href="https://github.com/vladromenko/homebrain-dataset-machine" target="_blank" rel="noreferrer">
        <CircleHelp size={17}/> Documentation</a>
    </div>
  </nav>;
}

export function Projects(props: any) {
  const { overview, project, tasks, select, retain } = props;
  const resumes = overview?.sessions.filter((row: Session) => row.project_id === project && !['complete', 'selected'].includes(row.state)).slice(0, 1) || [];
  return <div className="projects">
    <div className="section-heading"><div><div className="eyebrow">YOUR LABORATORY</div>
      <h1>Make every attempt count.</h1><p className="muted">Choose a project. Follow its protocol. Keep the native evidence.</p>
    </div><Badge variant="secondary">Local collection</Badge></div>
    <ProjectCards {...props}/>
    {resumes.map((row: Session) => <div className="resume" key={row.session_id}>
      <div><strong>Continue your attempt</strong><p>{row.task_id} · {row.state}</p></div>
      <Button variant="outline" onClick={() => retain(row)}>Resume session</Button>
    </div>)}
    <TaskNavigation {...props}/>
    <div className="task-list">{tasks.tasks.map((task: Task) => <TaskRow key={task.task_id} task={task} select={select}/>)}</div>
    <p className="muted collection-note">Development attempts, raw saves and admitted study data are counted separately. Project plans supply study denominators.</p>
  </div>;
}

function ProjectCards({ overview, project, setProject }: any) {
  return <div className="project-grid">{overview?.projects.map((item: any) =>
    <button className={`project-card ${project === item.project_id ? 'selected' : ''}`}
      key={item.project_id} onClick={() => setProject(item.project_id)}>
      <div className="project-icon">{item.project_id === 'smart-swarm' ? <Zap/> : <Boxes/>}</div>
      <h2>{item.title}</h2>
      <p>{item.project_id === 'smart-swarm' ? 'Staged visual stories · project-owned scientific gates' : 'SO101, Tank and ROSMASTER · native human demonstrations'}</p>
      <span>{item.robot_ids.map((id: string) => id.toUpperCase()).join(' · ')}</span>
    </button>)}</div>;
}

function TaskNavigation({ overview, project, group, setGroup, tasks }: any) {
  const groups = overview?.projects.find((item: any) => item.project_id === project)?.task_groups || [];
  return <div className="list-heading task-navigation"><h2>Recording tasks</h2>
    <select aria-label="Task group" value={group} onChange={event => setGroup(event.target.value)}>
      <option value="">All groups</option>
      {groups.map((item: any) => <option key={item.id || item} value={item.id || item}>{item.title || item.id || item}</option>)}
    </select>
    <span>{tasks.offset + 1}–{tasks.offset + tasks.tasks.length} of {tasks.total || '…'}</span>
    <Button variant="ghost" size="sm" disabled={!tasks.offset} onClick={() => tasks.setOffset(Math.max(0, tasks.offset - 50))}>Previous</Button>
    <Button variant="ghost" size="sm" disabled={tasks.offset + tasks.tasks.length >= tasks.total} onClick={() => tasks.setOffset(tasks.offset + 50)}>Next</Button>
  </div>;
}

function TaskRow({ task, select }: {task: Task; select: (task: Task) => void}) {
  return <Card className="task-row"><div className="robot-mark">{task.robot_id.toUpperCase()}</div>
    <div><h3>{task.title}</h3><p>{task.dataset_intent.replaceAll('_', ' ')} · {task.split} · {task.source_group}</p></div>
    <Button variant="outline" onClick={() => select(task)}>Open task</Button>
  </Card>;
}

export function SettingsView({ session }: any) {
  return <div className="projects"><div className="eyebrow">STATION PROFILE</div>
    <h1>Configure once. Recheck what changes.</h1>
    <Card className="settings-card"><h2>Local services & permissions</h2>
      <p>Native service identities, camera roles and the shared inference pool are configured on Homebrain. Devices reconnect by persistent identity.</p>
      <p>Microphone access is opt-in. Use push-to-talk in the assistant. Local microphone/speaker mode is half duplex.</p>
      <p>Concurrency qualification requires an attended native recording under assistant load before existing reservations can be relaxed.</p>
    </Card><VoiceSettings session={session}/>
  </div>;
}
