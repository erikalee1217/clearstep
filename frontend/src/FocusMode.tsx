import { useEffect, useReducer } from 'react';
import { ArrowLeft, Check, Footprints, Pause, Play, RotateCw } from 'lucide-react';
import FocusJourney from './FocusJourney';
import { initialSession, intervalProgress, sessionReducer, type Duration } from './focusSession';
import type { ConfirmedTask } from './types';

export default function FocusMode({ task, onExit, onComplete }: {
  task: ConfirmedTask; onExit: () => void; onComplete: () => void;
}) {
  const [session, dispatch] = useReducer(sessionReducer, initialSession);
  useEffect(() => {
    if (session.phase !== 'running') return;
    const tick = () => dispatch({ type: 'tick', now: Date.now() });
    const interval = window.setInterval(tick, 250);
    document.addEventListener('visibilitychange', tick);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', tick);
    };
  }, [session.phase]);

  const progress = intervalProgress(session);
  const seconds = 'remainingMs' in session ? Math.ceil(session.remainingMs / 1000) : null;
  const time = seconds === null ? null : `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
  return <section className="focus">
    <button className="text-button" onClick={onExit}><ArrowLeft size={18} /> Exit focus</button>
    <div className={`focus-task focus-${session.phase}`}>
      <h1>{task.title}</h1>
      {task.first_step && <><h2>First step</h2><p className="first-step">{task.first_step}</p></>}
      <FocusJourney phase={session.phase} progress={session.phase === 'ready' ? session.duration === null ? null : 0 : progress} />
      {session.phase === 'ready' ? <div className="focus-ready-controls">
        <fieldset className="focus-duration"><legend>Focus duration</legend>
          {([10, 20, null] as Duration[]).map(duration => <label key={duration ?? 'none'}>
            <input type="radio" name="focus-duration" checked={session.duration === duration}
              onChange={() => dispatch({ type: 'select', duration })} />
            <span>{duration === null ? 'No timer' : `${duration} min`}</span>
          </label>)}
        </fieldset>
        <button className="primary" onClick={() => dispatch({ type: 'start', now: Date.now() })}><Play size={18} /> Start focus</button>
      </div> : <>
        {time !== null && <div className="focus-clock" role="timer" aria-label="Focus interval remaining" aria-live="off">{time}</div>}
        <p className="session-status" role="status">{session.phase === 'finished' ? 'Focus session complete' : session.phase === 'paused' ? 'Paused' : session.phase === 'running' ? `of ${session.intervalMs / 60000} minutes` : ''}</p>
        <div className="task-actions focus-actions">
          {session.phase === 'running' && <button className="quiet-button" onClick={() => dispatch({ type: 'pause', now: Date.now() })}><Pause size={18} /> Pause</button>}
          {session.phase === 'paused' && <button className="primary" onClick={() => dispatch({ type: 'resume', now: Date.now() })}><Play size={18} /> Resume</button>}
          {session.phase === 'finished' && <button className="quiet-button continue-focus" onClick={() => dispatch({ type: 'continue', now: Date.now() })}><RotateCw size={20} /> Continue for 10 min</button>}
          <button className={session.phase === 'untimed' ? 'primary' : 'quiet-button'} onClick={onExit}><Footprints size={18} /> Done for now</button>
        </div>
        <button className="quiet-button complete-task" onClick={onComplete}><Check size={18} /> Mark task complete</button>
      </>}
    </div>
  </section>;
}
