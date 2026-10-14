import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/taskEditing.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } });
const { editTask } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
const original = Object.freeze({ id: 'original', title: 'Portfolio', importance: 'high',
  first_step: 'Choose one section', first_step_origin: 'suggested', start_friction: null,
  due_date: '2026-10-12', due_at: null, created_at: '2026-10-06T02:00:00Z', status: 'todo' });

test('edits only allowed fields without mutating identity, age, status or friction', () => {
  const updated = editTask(original, { ...original, id: 'changed', created_at: 'changed',
    status: 'done', start_friction: 'high', title: '  Updated portfolio  ', importance: 'normal' });
  assert.deepEqual(updated, { ...original, title: 'Updated portfolio', importance: 'normal' });
  assert.equal(original.title, 'Portfolio');
  const done = { ...original, status: 'done' };
  assert.equal(editTask(done, { ...done, title: 'Edited' }).status, 'done');
});

test('first-step origin is retained, replaced, added or cleared appropriately', () => {
  assert.equal(editTask(original, { ...original }).first_step_origin, 'suggested');
  assert.equal(editTask(original, { ...original, first_step: 'New step' }).first_step_origin, 'user');
  const empty = { ...original, first_step: null, first_step_origin: null };
  assert.equal(editTask(empty, { ...empty, first_step: 'Added step' }).first_step_origin, 'user');
  const cleared = editTask(original, { ...original, first_step: '   ' });
  assert.equal(cleared.first_step, null);
  assert.equal(cleared.first_step_origin, null);
});

test('deadline can change precision or be removed', () => {
  const timed = editTask(original, { ...original, due_date: null, due_at: '2026-10-13T17:00:00+08:00' });
  assert.equal(timed.due_at, '2026-10-13T17:00:00+08:00');
  assert.equal(timed.due_date, null);
  assert.equal(editTask(timed, { ...timed, due_at: null }).due_at, null);
  assert.equal(editTask(timed, { ...timed, due_at: null, due_date: '2026-10-14' }).due_date, '2026-10-14');
});

test('invalid edits are rejected', () => {
  for (const patch of [{ title: ' ' }, { title: 'a'.repeat(201) }, { first_step: 'a'.repeat(501) },
    { importance: 'urgent' }, { due_at: '2026-10-13T17:00:00Z' }, { due_date: '2026-02-30' },
    { due_date: null, due_at: 'invalid' }, { due_date: null, due_at: '2026-10-13T17:00:00' }]) {
    assert.throws(() => editTask(original, { ...original, ...patch }));
  }
});
