export type DraftTask = {
  title: string;
  importance: 'normal' | 'high';
  first_step: string | null;
  first_step_origin: 'explicit' | 'suggested' | 'user' | null;
  due_date: string | null;
  due_at: string | null;
};
export type ConfirmedTask = DraftTask & {
  id: string;
  start_friction: 'low' | 'medium' | 'high' | null;
  status: 'todo' | 'done';
  created_at: string;
};
export type RankedTask = { id: string; reasons: string[] };
