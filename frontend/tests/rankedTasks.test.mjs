import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/rankedTasks.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } });
const { resolveRanking } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
const tasks = Object.freeze(['A', 'B', 'C', 'D'].map(id => Object.freeze({
  id, title: id, status: 'todo', importance: 'normal', start_friction: null,
  created_at: '2026-10-12T00:00:00Z',
})));
const snapshot = (tasks, ids, refresh = 0) => ({
  tasks, refresh, ranking: ids.map(id => ({ id, reasons: [`Reason for ${id}`] })),
});
const ids = result => result.map(entry => entry.task.id);

test('recommendation and alternatives follow ranking, without changing stored order', () => {
  const before = JSON.stringify(tasks);
  const result = resolveRanking(tasks, snapshot(tasks, ['C', 'D', 'B', 'A']), 0, false);
  assert.equal(result[0].task.id, 'C');
  assert.deepEqual(ids(result.slice(1)), ['D', 'B', 'A']);
  assert.deepEqual(result[0].reasons, ['Reason for C']);
  assert.equal(JSON.stringify(tasks), before);
  assert.deepEqual(tasks.map(task => task.id), ['A', 'B', 'C', 'D']);
});

test('tied ranking output is preserved without a frontend sort', () => {
  assert.deepEqual(ids(resolveRanking(tasks, snapshot(tasks, ['A', 'B', 'C', 'D']), 0, false)), ['A', 'B', 'C', 'D']);
});

test('missing, deleted and completed tasks are excluded, with reasons staying aligned', () => {
  const current = tasks.filter(task => task.id !== 'B').map(task => task.id === 'C' ? { ...task, status: 'done' } : task);
  const result = resolveRanking(current, snapshot(current, ['missing', 'C', 'B', 'D', 'A']), 0, false);
  assert.deepEqual(ids(result), ['D', 'A']);
  assert.deepEqual(result[0].reasons, ['Reason for D']);
  assert.deepEqual(resolveRanking([], snapshot([], ['A']), 0, false), []);
});

test('loading, unavailable and stale responses never supply alternatives', () => {
  const ranked = snapshot(tasks, ['C', 'D', 'B', 'A']);
  assert.deepEqual(resolveRanking(tasks, null, 0, false), []);
  assert.deepEqual(resolveRanking(tasks, ranked, 0, true), []);
  assert.deepEqual(resolveRanking(tasks, ranked, 1, false), []);
  assert.deepEqual(resolveRanking([...tasks], ranked, 0, false), []);
});

test('edits invalidate the old ranking until the new task snapshot is ranked', () => {
  const old = snapshot(tasks, ['C', 'D', 'B', 'A']);
  const edited = tasks.map(task => task.id === 'A' ? { ...task, title: 'Edited A', importance: 'high' } : task);
  assert.deepEqual(resolveRanking(edited, old, 0, false), []);
  const result = resolveRanking(edited, snapshot(edited, ['A', 'C', 'D', 'B']), 0, false);
  assert.equal(result[0].task.title, 'Edited A');
  assert.deepEqual(ids(result.slice(1)), ['C', 'D', 'B']);
  assert.deepEqual(tasks.map(task => task.id), ['A', 'B', 'C', 'D']);
});
