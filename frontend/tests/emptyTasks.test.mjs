import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

// Compile the existing app for a render-only test, without adding a DOM library.
const require = createRequire(import.meta.url);
const previous = ['.ts', '.tsx'].map(extension => require.extensions[extension]);
let App;
let FocusMode;
let FocusJourney;
try {
  for (const extension of ['.ts', '.tsx']) {
    require.extensions[extension] = (module, filename) => {
      const { outputText } = ts.transpileModule(readFileSync(filename, 'utf8'), {
        compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
      });
      module._compile(outputText, filename);
    };
  }
  App = require('../src/App.tsx').default;
  FocusMode = require('../src/FocusMode.tsx').default;
  FocusJourney = require('../src/FocusJourney.tsx').default;
} finally {
  ['.ts', '.tsx'].forEach((extension, index) => {
    if (previous[index]) require.extensions[extension] = previous[index];
    else delete require.extensions[extension];
  });
}

test('Start Here hides alternatives when no todos remain or ranking is not available yet', () => {
  const previousStorage = globalThis.localStorage;
  try {
    for (const status of ['done', 'todo']) {
      globalThis.localStorage = { getItem: key => key === 'clearstep.tasks.v1'
        ? JSON.stringify([{ id: 'task-1', title: 'Test task', status }]) : null };
      const html = renderToStaticMarkup(React.createElement(App));
      assert.ok(html.includes('Start Here'));
      assert.ok(!html.includes('Choose another task'));
      assert.ok(!html.includes('class="task-list"'));
      if (status === 'todo') assert.ok(html.includes('Finding your next task...'));
      if (status === 'done') assert.ok(html.includes('All done for now.'));
    }
  } finally {
    if (previousStorage === undefined) delete globalThis.localStorage;
    else globalThis.localStorage = previousStorage;
  }
});

test('Focus entry defaults to 10 min and exposes Start focus without completion pressure', () => {
  let completions = 0;
  const html = renderToStaticMarkup(React.createElement(FocusMode, {
    task: { id: 'focus-task', title: 'Prepare portfolio', first_step: 'Choose one section' },
    onExit: () => {}, onComplete: () => { completions++; },
  }));
  assert.ok(html.includes('Prepare portfolio'));
  assert.ok(html.includes('Choose one section'));
  assert.match(html, /checked=""\/><span>10 min/);
  assert.ok(html.includes('Start focus'));
  assert.ok(html.includes('Exit focus'));
  assert.ok(!html.includes('role="timer"'));
  assert.ok(!html.includes('Mark task complete'));
  assert.equal(completions, 0);
});

test('Focus entry omits the first-step section when no step exists', () => {
  const html = renderToStaticMarkup(React.createElement(FocusMode, {
    task: { id: 'focus-task', title: 'Reply to Maya', first_step: null },
    onExit: () => {}, onComplete: () => {},
  }));
  assert.ok(!html.includes('First step'));
});

test('journey keeps the scene in untimed mode but exposes a travel route only for timed intervals', () => {
  for (const progress of [null, 0, 0.5, 1]) {
    const html = renderToStaticMarkup(React.createElement(FocusJourney, { progress, phase: progress === null ? 'untimed' : 'running' }));
    assert.equal(html.includes('class="journey-route"'), progress !== null);
    assert.ok(html.includes('class="journey-earth"'));
    assert.ok(html.includes('class="journey-terrain"'));
    assert.ok(!html.includes('class="journey-clearing"'));
    assert.ok(html.includes('class="companion-life"'));
    assert.ok(html.includes('aria-hidden="true"'));
  }
});

test('multiple journey scenes use unique gradient IDs with matching local references', () => {
  const html = renderToStaticMarkup(React.createElement(React.Fragment, null,
    ...[0, 0.5, 1].map(progress => React.createElement(FocusJourney, {
      key: progress, progress, phase: progress === 1 ? 'finished' : 'running',
    })),
  ));
  const ids = [...html.matchAll(/id="([^"]+)"/g)].map(match => match[1]);
  assert.equal(ids.length, 12);
  assert.equal(new Set(ids).size, ids.length);
  for (const match of html.matchAll(/url\(#([^)]+)\)/g)) assert.ok(ids.includes(match[1]));
});

test('journey exposes session phase only for presentation', () => {
  for (const phase of ['ready', 'running', 'paused', 'finished', 'untimed']) {
    const html = renderToStaticMarkup(React.createElement(FocusJourney, { phase, progress: phase === 'untimed' ? null : 0.5 }));
    assert.ok(html.includes(`phase-${phase}`));
    assert.ok(html.includes('class="companion-life"'));
  }
});
