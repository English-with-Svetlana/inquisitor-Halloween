const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('index.html', 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
function setup(reject = false, initiallyHidden = false) {
  const events = {}, pageEvents = {};
  let plays = 0, pauses = 0;
  const poster = { hidden: true };
  const video = {
    controls: true, hidden: false, paused: true, currentTime: 1,
    removeAttribute(name) { assert.equal(name, 'controls'); this.controls = false; },
    addEventListener: (name, fn) => events[name] = fn,
    play() {
      plays++;
      this.paused = reject;
      if (reject === 'throw') throw new Error('blocked');
      return reject ? Promise.reject(new Error('blocked')) : Promise.resolve();
    },
    pause() { pauses++; this.paused = true; }
  };
  const document = { hidden: initiallyHidden,
    querySelector: name => name === 'video' ? video : poster,
    addEventListener: (name, fn) => pageEvents[name] = fn };
  const window = { addEventListener: (name, fn) => pageEvents[name] = fn };
  vm.runInNewContext(code, { document, window });
  return { video, poster, document, events, pageEvents,
    plays: () => plays, pauses: () => pauses };
}
(async () => {
  let t = setup();
  assert.equal(t.plays(), 1);
  for (const key of ['autoplay', 'loop', 'muted', 'defaultMuted', 'playsInline']) assert.equal(t.video[key], true);
  assert.equal(t.video.controls, false);
  assert.equal(t.video.volume, 0);
  assert.equal(t.video.hidden, false); // Native poster works before playing.
  t.events.playing();
  assert.equal(t.poster.hidden, true);
  assert.equal(t.video.hidden, false); // No frame callback can leave it invisible.
  t.pageEvents.pageshow(); assert.equal(t.plays(), 1);
  assert.equal(t.events.ended, undefined); // Native loop has no JS end handler.
  assert.equal(t.pauses(), 0);
  t.document.hidden = true; t.pageEvents.visibilitychange();
  assert.equal(t.pauses(), 1);
  t.document.hidden = false; t.pageEvents.visibilitychange();
  assert.equal(t.plays(), 2);
  assert.equal(t.video.currentTime, 1); // Resume without seeking/reset flicker.
  t.pageEvents.visibilitychange(); assert.equal(t.plays(), 2);
  t.events.error(); t.events.playing();
  assert.equal(t.poster.hidden, false);
  assert.equal(t.video.hidden, true);
  t.pageEvents.pagehide(); t.pageEvents.pageshow(); assert.equal(t.plays(), 2);
  for (const rejection of [true, 'throw']) {
    t = setup(rejection); await new Promise(resolve => setImmediate(resolve));
    assert.equal(t.poster.hidden, false);
    assert.equal(t.video.hidden, true);
    assert.equal(t.video.controls, false);
    assert.equal(t.plays(), 1);
  }
  t = setup(false, true); assert.equal(t.plays(), 0);
  t.document.hidden = false; t.pageEvents.visibilitychange();
  // Initial hidden state must be marked suspended to start on becoming visible.
  assert.equal(t.plays(), 1);
  t = setup(); t.pageEvents.pagehide(); t.pageEvents.pageshow();
  assert.equal(t.plays(), 2);
  console.log('PASS: silent native-loop configuration; immediate video/poster visibility; no end handler; rejected/thrown autoplay fallback; error fallback; visibility/BFCache resume; no resets or duplicate initial playback. Actual browser looping is not simulated.');
})();
