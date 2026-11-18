import type { ConfirmedTask, DraftTask } from './types';

export type ReviewTask = DraftTask & { selected: boolean };

export function confirmBatch(drafts: ReviewTask[]): ConfirmedTask[] {
  const createdAt = new Date().toISOString();
  return drafts.filter(task => task.selected).map(({ selected: _, ...task }) => ({
    ...task, title: task.title.trim(), first_step: task.first_step?.trim() || null,
    first_step_origin: task.first_step?.trim() ? task.first_step_origin : null,
    id: crypto.randomUUID(), created_at: createdAt, status: 'todo',
  }));
}
