import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

// Use the existing TypeScript compiler to load the production function in Node.
const source = await readFile(new URL('../src/confirmation.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } });
const { confirmBatch } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);

test('confirmation preserves selection/order and assigns one timestamp per batch', () => {
  const RealDate = Date;
  let tick = 0;
  globalThis.Date = class extends RealDate {
    constructor() { super(1791273600000 + tick++); }
  };
  try {
    const draft = { first_step: null, first_step_origin: null, due_at: null, due_date: null,
      importance: 'normal', start_friction: null, selected: true };
    const first = confirmBatch([
      { ...draft, title: 'First' },
      { ...draft, title: 'Excluded', selected: false },
      { ...draft, title: 'Second' },
    ]);
    const later = confirmBatch([{ ...draft, title: 'Later' }]);
    assert.deepEqual(first.map(task => task.title), ['First', 'Second']);
    assert.equal(first[0].created_at, first[1].created_at);
    assert.ok(later[0].created_at > first[0].created_at);
    assert.notEqual(first[0].id, first[1].id);
    assert.ok(first.every(task => task.status === 'todo' && !('selected' in task)));
  } finally { globalThis.Date = RealDate; }
});

test('confirmation preserves reviewed importance and steps but always unsets friction', () => {
  const draft = { title: 'Task', importance: 'high', start_friction: 'low', selected: true,
    first_step: '  Choose one section  ', first_step_origin: 'user', due_date: null, due_at: null };
  const [high, overridden] = confirmBatch([
    draft,
    { ...draft, importance: 'normal', start_friction: 'high', first_step: '   ' },
  ]);
  assert.equal(high.importance, 'high');
  assert.equal(overridden.importance, 'normal');
  assert.equal(high.start_friction, null);
  assert.equal(overridden.start_friction, null);
  assert.equal(high.first_step, 'Choose one section');
  assert.equal(high.first_step_origin, 'user');
  assert.equal(overridden.first_step, null);
  assert.equal(overridden.first_step_origin, null);
});
