import type { ConfirmedTask, RankedTask } from './types';

export type RankingSnapshot = {
  tasks: ConfirmedTask[];
  refresh: number;
  ranking: RankedTask[];
};

export function resolveRanking(tasks: ConfirmedTask[], snapshot: RankingSnapshot | null, refresh: number, unavailable: boolean) {
  if (unavailable || !snapshot || snapshot.tasks !== tasks || snapshot.refresh !== refresh) return [];
  return snapshot.ranking.flatMap(ranked => {
    const task = tasks.find(task => task.id === ranked.id && task.status === 'todo');
    return task ? [{ task, reasons: ranked.reasons }] : [];
  });
}
