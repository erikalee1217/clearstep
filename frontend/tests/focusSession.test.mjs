import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/focusSession.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } });
const { initialSession, sessionReducer: reduce, intervalProgress: progress } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
const start = (duration, now = 1000) => reduce(reduce(initialSession, { type: 'select', duration }), { type: 'start', now });

test('ready defaults to 10 minutes; opting into untimed focus has no clock transitions', () => {
  assert.deepEqual(initialSession, { phase: 'ready', duration: 10 });
  assert.equal(reduce(initialSession, { type: 'start', now: 1000 }).intervalMs, 600000);
  const untimed = start(null);
  assert.deepEqual(untimed, { phase: 'untimed' });
  assert.equal(progress(untimed), null);
  assert.equal(progress(initialSession), null);
  for (const type of ['tick', 'pause', 'resume', 'continue', 'start']) {
    assert.equal(reduce(untimed, { type, now: 999999 }), untimed);
  }
});

test('10 and 20 minute intervals use elapsed wall time, including delayed callbacks', () => {
  for (const duration of [10, 20]) {
    const running = start(duration);
    assert.equal(running.endsAt, 1000 + duration * 60000);
    const ticked = reduce(running, { type: 'tick', now: 61000 });
    assert.equal(ticked.remainingMs, (duration - 1) * 60000);
    assert.equal(progress(running), 0);
    assert.equal(reduce(running, { type: 'start', now: 2000 }), running);
    assert.equal(reduce(running, { type: 'select', duration: null }), running);
  }
});

test('pause captures exact remaining time and resume excludes the paused gap', () => {
  const paused = reduce(start(10), { type: 'pause', now: 151000 });
  assert.equal(paused.remainingMs, 450000);
  assert.equal(progress(paused), 0.25);
  assert.equal(reduce(paused, { type: 'tick', now: 900000 }), paused);
  const resumed = reduce(paused, { type: 'resume', now: 1000000 });
  assert.equal(resumed.endsAt, 1450000);
  assert.equal(progress(resumed), 0.25);
  assert.equal(reduce(resumed, { type: 'tick', now: 1150000 }).remainingMs, 300000);
  assert.equal(reduce(resumed, { type: 'resume', now: 1100000 }), resumed);
});

test('expiry clamps to zero, including pause at expiry; continue starts a fresh 10 minutes', () => {
  for (const type of ['tick', 'pause']) {
    const finished = reduce(start(20), { type, now: 2000000 });
    assert.deepEqual(finished, { phase: 'finished', intervalMs: 1200000, remainingMs: 0 });
    assert.equal(progress(finished), 1);
    assert.equal(reduce(finished, { type: 'tick', now: 3000000 }), finished);
    const continued = reduce(finished, { type: 'continue', now: 3000000 });
    assert.equal(continued.intervalMs, 600000);
    assert.equal(continued.endsAt, 3600000);
    assert.equal(progress(continued), 0);
  }
});

test('clock moving backwards cannot produce negative interval progress', () => {
  const ticked = reduce(start(10), { type: 'tick', now: 0 });
  assert.equal(ticked.remainingMs, 600000);
  assert.equal(progress(ticked), 0);
});
