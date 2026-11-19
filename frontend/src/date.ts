import type { DraftTask } from './types';

type Deadline = Pick<DraftTask, 'due_date' | 'due_at'>;

export function dateInput(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function defaultDueAt(): string {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(9, 0, 0, 0);
  return tomorrow.toISOString();
}

export function changeDeadlineMode(task: Deadline, mode: string): Deadline {
  if (mode === 'date') {
    return {
      due_date: task.due_date ?? dateInput(task.due_at ? new Date(task.due_at) : new Date()),
      due_at: null,
    };
  }
  if (mode === 'time') {
    return {
      due_date: null,
      due_at: task.due_at ?? (task.due_date
        ? new Date(`${task.due_date}T09:00:00`).toISOString()
        : defaultDueAt()),
    };
  }
  return { due_date: null, due_at: null };
}
