const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('index.html', 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
function setup(reject = false) {
  const events = {}, pageEvents = {}, classes = new Set();
  let frames = [], plays = 0;
  const video = {
    controls: true,
    removeAttribute(name) { assert.equal(name, 'controls'); this.controls = false; },
    paused: true, readyState: 3, currentTime: 1,
    classList: { add: x => classes.add(x), remove: x => classes.delete(x) },
    addEventListener: (name, fn) => events[name] = fn,
    requestVideoFrameCallback: fn => frames.push(fn),
    play() { plays++; this.paused = reject; return reject ? Promise.reject(new Error('blocked')) : Promise.resolve(); },
    pause() { this.paused = true; }
  };
  const document = { hidden: false, querySelector: () => video,
    addEventListener: (name, fn) => pageEvents[name] = fn };
  const window = { addEventListener: (name, fn) => pageEvents[name] = fn };
  vm.runInNewContext(code, { document, window });
  return { video, document, events, pageEvents, classes, plays: () => plays,
    frame: () => { const batch = frames; frames = []; batch.forEach(fn => fn()); } };
}
(async () => {
  let t = setup();
  assert.equal(t.plays(), 1);
  for (const key of ['autoplay', 'muted', 'defaultMuted', 'playsInline']) assert.equal(t.video[key], true);
  assert.equal(t.video.controls, false);
  assert.equal(t.classes.has('ready'), false);
  t.events.playing(); t.frame(); assert(t.classes.has('ready'));
  t.pageEvents.pageshow(); assert.equal(t.plays(), 1);
  t.document.hidden = true; t.pageEvents.visibilitychange(); assert(t.video.paused);
  t.document.hidden = false; t.pageEvents.visibilitychange();
  assert.equal(t.video.currentTime, 0); assert.equal(t.plays(), 2);
  t.events.playing(); t.events.error(); t.frame(); assert(!t.classes.has('ready'));
  t.document.hidden = true; t.pageEvents.visibilitychange();
  t.document.hidden = false; t.pageEvents.visibilitychange(); assert.equal(t.plays(), 2); assert.equal(t.video.controls, false);
  t = setup(true); await new Promise(resolve => setImmediate(resolve));
  assert(!t.classes.has('ready')); assert.equal(t.plays(), 1); assert.equal(t.video.controls, false);
  t = setup(); t.pageEvents.pagehide(); t.pageEvents.pageshow();
  assert.equal(t.plays(), 2); assert.equal(t.video.currentTime, 0);
  console.log('PASS: initial playback, first-frame reveal, rejected autoplay, media-error fallback, visibility replay, BFCache replay, and no duplicate initial pageshow playback (simulated events).');
})();
