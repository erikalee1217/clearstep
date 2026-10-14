import type { ConfirmedTask } from './types';

export function editTask(original: ConfirmedTask, edited: ConfirmedTask): ConfirmedTask {
  const title = edited.title.trim();
  const firstStep = edited.first_step?.trim() || null;
  if (!title || title.length > 200) throw new Error('Enter a task title of 1 to 200 characters.');
  if (firstStep && firstStep.length > 500) throw new Error('Keep the first step within 500 characters.');
  if (!['normal', 'high'].includes(edited.importance)) throw new Error('Choose a valid importance.');
  if (edited.due_date && edited.due_at) throw new Error('Choose either a date or a date and time.');
  if (edited.due_date && (!/^\d{4}-\d{2}-\d{2}$/.test(edited.due_date) ||
    !Number.isFinite(Date.parse(edited.due_date)) || new Date(edited.due_date).toISOString().slice(0, 10) !== edited.due_date)) {
    throw new Error('Enter a valid deadline date.');
  }
  if (edited.due_at && (!/(Z|[+-]\d{2}:\d{2})$/.test(edited.due_at) || !Number.isFinite(Date.parse(edited.due_at)))) {
    throw new Error('Enter a valid deadline time.');
  }
  return {
    ...original, title, importance: edited.importance,
    first_step: firstStep,
    first_step_origin: firstStep === null ? null : firstStep === original.first_step ? original.first_step_origin : 'user',
    due_date: edited.due_date, due_at: edited.due_at,
  };
}
