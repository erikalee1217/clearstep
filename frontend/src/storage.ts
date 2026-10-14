import type { ConfirmedTask } from './types';

const KEY = 'clearstep.tasks.v1';
const BRAIN_DUMP_KEY = 'clearstep.brain-dump.v1';
export function loadBrainDump(): string {
  return localStorage.getItem(BRAIN_DUMP_KEY) ?? '';
}
export function saveBrainDump(text: string): void {
  if (text) localStorage.setItem(BRAIN_DUMP_KEY, text);
  else localStorage.removeItem(BRAIN_DUMP_KEY);
}
export function loadTasks(): ConfirmedTask[] {
  const raw = localStorage.getItem(KEY);
  if (!raw) return [];
  const value: unknown = JSON.parse(raw);
  if (!Array.isArray(value) || !value.every(task => task && typeof task.id === 'string' && typeof task.title === 'string' && ['todo', 'done'].includes(task.status))) {
    throw new Error('Saved tasks could not be read.');
  }
  return value as ConfirmedTask[];
}
export function saveTasks(tasks: ConfirmedTask[]): void {
  localStorage.setItem(KEY, JSON.stringify(tasks));
}
