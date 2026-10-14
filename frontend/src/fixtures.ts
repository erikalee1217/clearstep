import type { DraftTask } from './types';

export function dateInput(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

export function fixtures(): DraftTask[] {
  const today = new Date();
  const day = (offset: number) => {
    const value = new Date(today);
    value.setDate(value.getDate() + offset);
    return dateInput(value);
  };
  const application = new Date(today);
  application.setHours(17, 0, 0, 0);
  return [
    { title: 'Submit application', first_step: 'Open the application form', due_at: application.toISOString() },
    { title: 'Prepare portfolio case study', first_step: 'List three project decisions' },
    { title: 'Prepare interview examples', first_step: 'Write one debugging example', due_date: day(3) },
    { title: 'Plan capstone project', first_step: null, due_date: day(2) },
    { title: 'Organize downloads', first_step: 'Open Downloads and select five old files' },
  ].map(task => ({ importance: 'normal', due_date: null, due_at: null, ...task,
    first_step_origin: task.first_step ? 'suggested' : null }));
}
