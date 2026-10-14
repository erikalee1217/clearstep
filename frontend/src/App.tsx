import { useEffect, useState } from 'react';
import { ArrowLeft, Check, Pencil, Play, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { dateInput } from './fixtures';
import { confirmBatch } from './confirmation';
import { editTask } from './taskEditing';
import FocusMode from './FocusMode';
import { resolveRanking, type RankingSnapshot } from './rankedTasks';
import { loadBrainDump, loadTasks, saveBrainDump, saveTasks } from './storage';
import type { ConfirmedTask, DraftTask, RankedTask } from './types';

type ReviewTask = DraftTask & Pick<ConfirmedTask, 'importance' | 'start_friction'> & { selected: boolean };

function localDatetime(value: string): string {
  const date = new Date(value);
  return `${dateInput(date)}T${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

export default function App() {
  const [initial] = useState(() => {
    try { return { tasks: loadTasks(), error: '' }; }
    catch { return { tasks: [] as ConfirmedTask[], error: 'Saved tasks could not be loaded. Reload or reset saved tasks.' }; }
  });
  const [tasks, setTasks] = useState(initial.tasks);
  const [initialBrainDump] = useState(() => {
    try { return { text: loadBrainDump(), error: '' }; }
    catch { return { text: '', error: 'Brain Dump could not be loaded from this browser.' }; }
  });
  const [brainDump, setBrainDump] = useState(initialBrainDump.text);
  const [brainDumpError, setBrainDumpError] = useState(initialBrainDump.error);
  const [submittedText, setSubmittedText] = useState('');
  const [drafts, setDrafts] = useState<ReviewTask[]>([]);
  const [draftsEdited, setDraftsEdited] = useState(false);
  const [screen, setScreen] = useState<'dump' | 'review' | 'start'>(initial.tasks.length === 0 ? 'dump' : 'start');
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState('');
  const [emptyExtraction, setEmptyExtraction] = useState(false);
  const [focusId, setFocusId] = useState<string | null>(null);
  const [editingTask, setEditingTask] = useState<ConfirmedTask | null>(null);
  const [editError, setEditError] = useState('');
  const [ranking, setRanking] = useState<RankingSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(initial.error);
  const [rankError, setRankError] = useState('');
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    if (!tasks.some(task => task.status === 'todo')) { setRanking(null); setLoading(false); setRankError(''); return; }
    const controller = new AbortController();
    setLoading(true);
    setRanking(null);
    setRankError('');
    fetch('/rank', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
      body: JSON.stringify({ tasks, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone }),
    }).then(async response => {
      if (!response.ok) throw new Error('Ranking unavailable. Check that the backend is running.');
      return response.json() as Promise<RankedTask[]>;
    }).then(result => {
      if (!controller.signal.aborted) setRanking({ tasks, refresh, ranking: result });
    }).catch(reason => {
      if (!controller.signal.aborted) setRankError(reason.message || 'Ranking unavailable.');
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [tasks, refresh]);

  function persist(next: ConfirmedTask[]) {
    try { saveTasks(next); setTasks(next); setError(''); return true; }
    catch { setError('Tasks could not be saved in this browser. Your current view has been kept.'); return false; }
  }
  function update(index: number, patch: Partial<ReviewTask>) {
    setDraftsEdited(true);
    setDrafts(current => current.map((task, i) => i === index ? { ...task, ...patch } : task));
  }
  function changeBrainDump(text: string) {
    setBrainDump(text);
    setExtractError('');
    setEmptyExtraction(false);
    try { saveBrainDump(text); setBrainDumpError(''); }
    catch { setBrainDumpError('Brain Dump is kept in this view, but could not be saved for refresh.'); }
  }
  async function extract() {
    if (extracting || !brainDump.trim() || brainDump.length > 10000) return;
    if (draftsEdited && !window.confirm('Replace your unconfirmed task edits with a new extraction?')) return;
    const rawText = brainDump;
    setExtracting(true);
    setExtractError('');
    setEmptyExtraction(false);
    try {
      const response = await fetch('/extract', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brain_dump: rawText, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Extraction unavailable. Please try again.');
      if (!Array.isArray(data)) throw new Error('Extraction returned an invalid response. Please try again.');
      setDrafts(data.map((task: DraftTask) => ({ ...task, start_friction: null, selected: true })));
      setDraftsEdited(false);
      setSubmittedText(rawText);
      if (!data.length) { setEmptyExtraction(true); return; }
      setScreen('review');
    } catch (reason) {
      setExtractError(reason instanceof Error && !(reason instanceof TypeError) ? reason.message : 'Could not reach extraction. Please try again.');
    } finally { setExtracting(false); }
  }
  function confirm() {
    const selected = drafts.filter(task => task.selected);
    if (!selected.length || selected.some(task => !task.title.trim())) { setError('Select at least one task and give each selected task a title.'); return; }
    const next = confirmBatch(drafts);
    if (persist([...tasks, ...next])) {
      changeBrainDump('');
      setSubmittedText('');
      setDrafts([]);
      setDraftsEdited(false);
      setScreen('start');
    }
  }
  function complete(id: string) {
    if (persist(tasks.map(task => task.id === id ? { ...task, status: 'done' } : task))) setFocusId(null);
  }
  function openEditor(task: ConfirmedTask) {
    setEditingTask({ ...task });
    setEditError('');
  }
  function saveEdit() {
    if (!editingTask) return;
    const original = tasks.find(task => task.id === editingTask.id);
    if (!original) { setEditError('This task is no longer available. Cancel to return.'); return; }
    try {
      const updated = editTask(original, editingTask);
      if (persist(tasks.map(task => task.id === original.id ? updated : task))) setEditingTask(null);
    } catch (reason) { setEditError(reason instanceof Error ? reason.message : 'Could not update task.'); }
  }
  function deleteTask() {
    if (!editingTask || !window.confirm(`Delete "${editingTask.title}"?`)) return;
    if (persist(tasks.filter(task => task.id !== editingTask.id))) {
      if (focusId === editingTask.id) setFocusId(null);
      setEditingTask(null);
    }
  }
  function reset() {
    if (!window.confirm('Remove saved tasks and clear the Brain Dump?')) return;
    if (persist([])) { changeBrainDump(''); setSubmittedText(''); setDrafts([]); setDraftsEdited(false); setFocusId(null); setEditingTask(null); setEditError(''); setScreen('dump'); }
  }
  const focused = tasks.find(task => task.id === focusId && task.status === 'todo');
  const rankedTasks = resolveRanking(tasks, ranking, refresh, loading || !!rankError);
  const recommended = rankedTasks[0]?.task;
  const alternatives = rankedTasks.slice(1);
  const rankingPending = tasks.some(task => task.status === 'todo') && !rankError &&
    (loading || !ranking || ranking.tasks !== tasks || ranking.refresh !== refresh);
  const completed = tasks.filter(task => task.status === 'done').length;

  return <main>
    <header><a className="brand" href="#">ClearStep</a><span>{completed} completed</span><button className="icon" title="Reset tasks" aria-label="Reset tasks" onClick={reset} disabled={extracting}><RotateCcw size={18} /></button></header>
    {error && <p role="alert" className="error">{error}</p>}
    {brainDumpError && <p role="alert" className="error">{brainDumpError}</p>}
    {editingTask ? <section>
      <h1>Edit task</h1>
      {editError && <p role="alert" className="error">{editError}</p>}
      <form onSubmit={event => { event.preventDefault(); saveEdit(); }}>
        <fieldset className="draft">
          <label className="task-title">Task<input autoFocus required maxLength={200} value={editingTask.title} onChange={event => setEditingTask({ ...editingTask, title: event.target.value })} /></label>
          <label>First step<input maxLength={500} value={editingTask.first_step ?? ''} onChange={event => setEditingTask({ ...editingTask, first_step: event.target.value || null })} /></label>
          <div className="fields">
            <label>Deadline<select value={editingTask.due_at ? 'time' : editingTask.due_date ? 'date' : 'none'} onChange={event => setEditingTask({ ...editingTask, due_date: event.target.value === 'date' ? dateInput(new Date()) : null, due_at: event.target.value === 'time' ? new Date().toISOString() : null })}><option value="none">None</option><option value="date">Date only</option><option value="time">Date and time</option></select></label>
            {editingTask.due_date && <label>Due date<input type="date" required value={editingTask.due_date} onChange={event => setEditingTask({ ...editingTask, due_date: event.target.value || null })} /></label>}
            {editingTask.due_at && <label>Due time (local)<input type="datetime-local" required value={localDatetime(editingTask.due_at)} onChange={event => setEditingTask({ ...editingTask, due_at: event.target.value ? new Date(event.target.value).toISOString() : null })} /></label>}
          </div>
          <label className="include"><input type="checkbox" checked={editingTask.importance === 'high'} onChange={event => setEditingTask({ ...editingTask, importance: event.target.checked ? 'high' : 'normal' })} /> High importance</label>
        </fieldset>
        <div className="task-actions"><button className="primary" type="submit"><Check size={18} /> Save</button><button className="quiet-button" type="button" onClick={() => setEditingTask(null)}>Cancel</button></div>
        <button className="quiet-button delete-task" type="button" onClick={deleteTask}><Trash2 size={18} /> Delete task</button>
      </form>
    </section> : focused ? <FocusMode key={focused.id} task={focused} onExit={() => setFocusId(null)} onComplete={() => complete(focused.id)} /> : screen === 'dump' ? <section className="brain-dump">
      {tasks.length > 0 && <button className="text-button" disabled={extracting} onClick={() => setScreen('start')}><ArrowLeft size={18} /> Start Here</button>}
      <h1>Brain Dump</h1>
      <form onSubmit={event => { event.preventDefault(); void extract(); }}>
        <label>Your thoughts and tasks<textarea rows={8} maxLength={10000} value={brainDump} disabled={extracting} onChange={event => changeBrainDump(event.target.value)} /></label>
        {extracting && <p role="status">Turning your thoughts into tasks...</p>}
        {extractError && <p role="alert" className="error">{extractError}</p>}
        {emptyExtraction && <p role="status">No clear tasks found. Edit your Brain Dump and try again.</p>}
        <button className="primary" disabled={extracting || !brainDump.trim() || brainDump.length > 10000} type="submit"><Play size={18} /> {extractError ? 'Try again' : 'Find tasks'}</button>
      </form>
    </section> : screen === 'review' ? <section>
      <button className="text-button" onClick={() => setScreen('dump')}><ArrowLeft size={18} /> Edit Brain Dump</button>
      <h1>Your next steps</h1>
      <details className="original-dump" open><summary>Original Brain Dump</summary><p>{submittedText}</p></details>
      <form onSubmit={event => { event.preventDefault(); confirm(); }}>
        <div className="draft-list">{drafts.map((task, index) => <article className="draft" key={index}>
          <label className="include"><input type="checkbox" checked={task.selected} onChange={event => update(index, { selected: event.target.checked })} /> Include task {index + 1}</label>
          <fieldset disabled={!task.selected}>
            <label className="task-title">Task<input required maxLength={200} value={task.title} onChange={event => update(index, { title: event.target.value })} /></label>
            <label><span>First step {task.first_step_origin === 'suggested' && <span className="muted">(suggested)</span>}</span><input maxLength={500} value={task.first_step ?? ''} onChange={event => update(index, { first_step: event.target.value || null, first_step_origin: event.target.value ? 'user' : null })} /></label>
            <div className="fields">
              <label>Deadline<select value={task.due_at ? 'time' : task.due_date ? 'date' : 'none'} onChange={event => update(index, { due_date: event.target.value === 'date' ? dateInput(new Date()) : null, due_at: event.target.value === 'time' ? new Date().toISOString() : null })}><option value="none">None</option><option value="date">Date only</option><option value="time">Date and time</option></select></label>
              {task.due_date && <label>Due date<input type="date" required value={task.due_date} onChange={event => update(index, { due_date: event.target.value || null })} /></label>}
              {task.due_at && <label>Due time (local)<input type="datetime-local" required value={localDatetime(task.due_at)} onChange={event => update(index, { due_at: event.target.value ? new Date(event.target.value).toISOString() : null })} /></label>}
            </div>
            <label className="include"><input type="checkbox" checked={task.importance === 'high'} onChange={event => update(index, { importance: event.target.checked ? 'high' : 'normal' })} /> High importance</label>
          </fieldset>
        </article>)}</div>
        <button className="primary" type="submit" disabled={!drafts.some(task => task.selected)}><Check size={18} /> Confirm reviewed tasks</button>
      </form>
    </section> : <section>
      <div className="section-heading"><h1>Start Here</h1>
      <button className="quiet-button" onClick={() => setScreen('dump')}><Plus size={18} /> Add tasks</button></div>
      {rankingPending ? <p role="status">Finding your next task...</p> : rankError ? <div role="alert"><p className="error">{rankError}</p><button onClick={() => setRefresh(value => value + 1)}><RotateCcw size={18} /> Try again</button></div> : recommended ? <div className="recommendation">
        <h2>{recommended.title}</h2><p>{rankedTasks[0].reasons.join(' · ')}</p>
        {recommended.first_step && <p className="first-step">{recommended.first_step}</p>}
        <div className="task-actions"><button className="primary" onClick={() => setFocusId(recommended.id)}><Play size={18} /> Start</button><button className="quiet-button" onClick={() => openEditor(recommended)}><Pencil size={18} /> Edit</button></div>
      </div> : <p>All done for now.</p>}
      {alternatives.length > 0 && <><h2 className="list-heading">Choose another task</h2>
      <div className="task-list">{alternatives.map(({ task }) => <div className="task-row" key={task.id}><span>{task.title}</span><div className="row-actions"><button className="icon" title={`Edit ${task.title}`} aria-label={`Edit ${task.title}`} onClick={() => openEditor(task)}><Pencil size={18} /></button><button className="icon" title={`Focus on ${task.title}`} aria-label={`Focus on ${task.title}`} onClick={() => setFocusId(task.id)}><Play size={18} /></button></div></div>)}</div>
      </>}
    </section>}
  </main>;
}
