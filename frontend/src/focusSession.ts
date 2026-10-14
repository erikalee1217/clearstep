export type Duration = 10 | 20 | null;
export type Session =
  | { phase: 'ready'; duration: Duration }
  | { phase: 'untimed' }
  | { phase: 'running'; intervalMs: number; remainingMs: number; endsAt: number }
  | { phase: 'paused' | 'finished'; intervalMs: number; remainingMs: number };
export type SessionAction =
  | { type: 'select'; duration: Duration }
  | { type: 'start' | 'tick' | 'pause' | 'resume' | 'continue'; now: number };

export const initialSession: Session = { phase: 'ready', duration: 10 };

function startInterval(minutes: number, now: number): Session {
  const intervalMs = minutes * 60_000;
  return { phase: 'running', intervalMs, remainingMs: intervalMs, endsAt: now + intervalMs };
}

export function sessionReducer(state: Session, action: SessionAction): Session {
  switch (action.type) {
    case 'select':
      return state.phase === 'ready' ? { ...state, duration: action.duration } : state;
    case 'start':
      return state.phase !== 'ready' ? state : state.duration === null
        ? { phase: 'untimed' } : startInterval(state.duration, action.now);
    case 'continue':
      return state.phase === 'finished' ? startInterval(10, action.now) : state;
    case 'resume':
      return state.phase === 'paused' ? { ...state, phase: 'running', endsAt: action.now + state.remainingMs } : state;
    case 'pause':
    case 'tick': {
      if (state.phase !== 'running') return state;
      const remainingMs = Math.max(0, Math.min(state.intervalMs, state.endsAt - action.now));
      if (remainingMs === 0) return { phase: 'finished', intervalMs: state.intervalMs, remainingMs: 0 };
      return action.type === 'pause'
        ? { phase: 'paused', intervalMs: state.intervalMs, remainingMs }
        : { ...state, remainingMs };
    }
  }
}

export function intervalProgress(state: Session): number | null {
  return 'intervalMs' in state ? Math.max(0, Math.min(1, 1 - state.remainingMs / state.intervalMs)) : null;
}
