// ── State ────────────────────────────────────────────────────────────────────

let mediaRecorder = null;
let audioStream = null;
let analyserNode = null;
let animFrameId = null;
let recordingStartTime = null;
let timerInterval = null;
let pollingInterval = null;
let expandedJobId = null;
let expandedJobStatus = null;
let activeTab = 'notulen';
let wakeLock = null;
let watchdogInterval = null;
let recorderDead = false;

// Chunked-upload session state. session.id is the server-assigned job_id;
// session.nextSeq is the seq number we'll attach to the next chunk MediaRecorder
// emits. session.draining is the in-progress drain promise (serialises uploads).
let session = null;

// ── IndexedDB queue ──────────────────────────────────────────────────────────
//
// Chunks are written here *before* they're POSTed. Surviving an iOS tab
// eviction is the whole point: when the page is reopened, the recovery banner
// drains anything left behind.
//
// Two stores:
//   sessions: keyPath 'id' — { id, title, meeting_date, attendees, agenda,
//                              mime_type, started_at }
//   chunks:   keyPath '[session_id, seq]' — { session_id, seq, blob }

const IDB_NAME = 'notulen-uploads';
const IDB_VERSION = 1;
let _idbPromise = null;

function idb() {
  if (_idbPromise) return _idbPromise;
  _idbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, IDB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains('sessions')) {
        db.createObjectStore('sessions', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('chunks')) {
        const cs = db.createObjectStore('chunks', { keyPath: ['session_id', 'seq'] });
        cs.createIndex('by_session', 'session_id');
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror  = () => reject(req.error);
  });
  return _idbPromise;
}

async function idbTx(store, mode, fn) {
  const db = await idb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, mode);
    const result = fn(tx.objectStore(store));
    tx.oncomplete = () => resolve(result);
    tx.onerror    = () => reject(tx.error);
    tx.onabort    = () => reject(tx.error);
  });
}

async function idbPutSession(s)        { return idbTx('sessions', 'readwrite', os => os.put(s)); }
async function idbDeleteSession(id)    { return idbTx('sessions', 'readwrite', os => os.delete(id)); }
async function idbAllSessions() {
  const db = await idb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('sessions', 'readonly');
    const req = tx.objectStore('sessions').getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror   = () => reject(req.error);
  });
}
async function idbPutChunk(sessionId, seq, blob) {
  return idbTx('chunks', 'readwrite', os => os.put({ session_id: sessionId, seq, blob }));
}
async function idbDeleteChunk(sessionId, seq) {
  return idbTx('chunks', 'readwrite', os => os.delete([sessionId, seq]));
}
async function idbChunksForSession(sessionId) {
  const db = await idb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('chunks', 'readonly');
    const req = tx.objectStore('chunks').index('by_session').getAll(sessionId);
    req.onsuccess = () => resolve((req.result || []).sort((a, b) => a.seq - b.seq));
    req.onerror   = () => reject(req.error);
  });
}
async function idbDeleteAllChunks(sessionId) {
  const db = await idb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('chunks', 'readwrite');
    const store = tx.objectStore('chunks');
    const req = store.index('by_session').openKeyCursor(IDBKeyRange.only(sessionId));
    req.onsuccess = () => {
      const cur = req.result;
      if (cur) { store.delete(cur.primaryKey); cur.continue(); }
    };
    tx.oncomplete = () => resolve();
    tx.onerror    = () => reject(tx.error);
  });
}

// ── Team members ─────────────────────────────────────────────────────────────

// Quick-pick attendee names shown on the upload form; edit to taste.
const TEAM = ['Alice', 'Bob', 'Carol', 'Dave'];
const selectedMembers = new Set();

function initChips() {
  const container = document.getElementById('team-chips');
  container.innerHTML = TEAM.map(name =>
    `<span class="chip" onclick="toggleChip(this, '${name}')">${name}</span>`
  ).join('');
}

function toggleChip(el, name) {
  if (selectedMembers.has(name)) {
    selectedMembers.delete(name);
    el.classList.remove('selected');
  } else {
    selectedMembers.add(name);
    el.classList.add('selected');
  }
}

function getAttendees() {
  const extra = document.getElementById('attendees-extra').value.trim();
  const extraList = extra ? extra.split(',').map(s => s.trim()).filter(Boolean) : [];
  return [...selectedMembers, ...extraList].join(', ');
}

// ── Init ─────────────────────────────────────────────────────────────────────

document.getElementById('meeting-date').value = new Date().toISOString().slice(0, 10);
initChips();
loadJobs();
loadHealth();
setInterval(loadHealth, 120000);  // every 2 min

async function loadHealth() {
  try {
    const resp = await fetch('/api/health/notulen/full');
    const h = await resp.json();
    const el = document.getElementById('health-banner');
    if (h.status === 'ok') {
      el.classList.remove('visible', 'degraded', 'broken');
      return;
    }
    const failing = (h.checks || []).filter(c => !c.ok).map(c => c.name).join(', ');
    el.textContent = '';
    const strong = document.createElement('strong');
    strong.textContent = h.status === 'broken' ? '⚠️ Pipeline down' : '⚠️ Pipeline degraded';
    el.appendChild(strong);
    el.append(' — ' + (failing || 'see logs'));
    el.classList.remove('degraded', 'broken');
    el.classList.add('visible', h.status === 'broken' ? 'broken' : 'degraded');
  } catch (e) { /* silent */ }
}

// ── Recording ────────────────────────────────────────────────────────────────

async function toggleRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    stopRecording();
  } else {
    await startRecording();
  }
}

async function startRecording() {
  const title = document.getElementById('title').value.trim();
  if (!title) {
    document.getElementById('title').focus();
    document.getElementById('title').style.borderColor = 'var(--red)';
    setTimeout(() => document.getElementById('title').style.borderColor = '', 1500);
    return;
  }

  try {
    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    document.getElementById('rec-status').textContent = 'Microfoon niet beschikbaar';
    return;
  }

  const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
    ? 'audio/webm;codecs=opus'
    : MediaRecorder.isTypeSupported('audio/mp4')
      ? 'audio/mp4'
      : '';

  // Open a recording session on the server. The job_id is what every chunk
  // POST hangs off; we persist it to IndexedDB so an evicted tab can resume.
  const startForm = new FormData();
  startForm.append('title', title);
  startForm.append('meeting_date', document.getElementById('meeting-date').value);
  startForm.append('attendees', getAttendees());
  startForm.append('agenda', document.getElementById('agenda').value.trim());

  let startResp;
  try {
    startResp = await fetch('/api/upload/start', { method: 'POST', body: startForm });
  } catch (err) {
    audioStream.getTracks().forEach(t => t.stop());
    audioStream = null;
    document.getElementById('rec-status').textContent = 'Geen verbinding met server';
    return;
  }
  if (!startResp.ok) {
    audioStream.getTracks().forEach(t => t.stop());
    audioStream = null;
    let detail = 'Server weigerde opname';
    try { detail = (await startResp.json()).detail || detail; } catch (e) {}
    document.getElementById('rec-status').textContent = detail;
    return;
  }
  const startData = await startResp.json();

  session = {
    id: startData.job_id,
    title,
    meeting_date: document.getElementById('meeting-date').value,
    attendees: getAttendees(),
    agenda: document.getElementById('agenda').value.trim(),
    mime_type: mimeType || 'application/octet-stream',
    started_at: Date.now(),
    nextSeq: 1,
    draining: null,
  };
  await idbPutSession({
    id: session.id,
    title: session.title,
    meeting_date: session.meeting_date,
    attendees: session.attendees,
    agenda: session.agenda,
    mime_type: session.mime_type,
    started_at: session.started_at,
  });

  const options = mimeType ? { mimeType } : {};
  mediaRecorder = new MediaRecorder(audioStream, options);

  mediaRecorder.ondataavailable = async (e) => {
    if (!session || !e.data || e.data.size === 0) return;
    const seq = session.nextSeq++;
    try {
      await idbPutChunk(session.id, seq, e.data);
    } catch (err) {
      console.warn('IndexedDB put failed', err);
    }
    drainChunks(session.id);
  };

  mediaRecorder.onstop = () => finalizeAndResetUI();
  mediaRecorder.onerror = (e) => {
    console.warn('MediaRecorder error', e.error || e);
    handleRecorderDeath();
  };

  // Waveform visualization
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioCtx.createMediaStreamSource(audioStream);
  analyserNode = audioCtx.createAnalyser();
  analyserNode.fftSize = 256;
  source.connect(analyserNode);
  drawWaveform();

  // 5-second chunks keep request overhead low while limiting blast-radius
  // for any single failed POST. ~30KB opus per chunk at 64kbps.
  mediaRecorder.start(5000);
  recordingStartTime = Date.now();
  recorderDead = false;
  acquireWakeLock();
  startRecorderWatchdog();

  document.getElementById('rec-btn').classList.add('recording');
  document.getElementById('rec-status').textContent =
    'Opname bezig — laat het scherm aan, druk niet op de aan/uit-knop';
  document.getElementById('rec-status').classList.add('active');
  document.getElementById('timer').classList.add('visible');
  document.getElementById('waveform').classList.add('visible');

  function timerTick() {
    if (!recordingStartTime) return;
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const s = String(elapsed % 60).padStart(2, '0');
    document.getElementById('timer').textContent = `${m}:${s}`;
    timerInterval = requestAnimationFrame(timerTick);
  }
  timerInterval = requestAnimationFrame(timerTick);
}

function stopRecording() {
  // Recorder may already be dead (OS suspended it). Skip .stop() in that case
  // and finalize whatever chunks reached the server.
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();  // fires onstop → finalizeAndResetUI
  } else if (session) {
    finalizeAndResetUI();
  }
  stopRecorderWatchdog();
  releaseWakeLock();
  if (audioStream) {
    audioStream.getTracks().forEach(t => t.stop());
    audioStream = null;
  }
  if (animFrameId) {
    cancelAnimationFrame(animFrameId);
    animFrameId = null;
  }
  if (timerInterval) {
    cancelAnimationFrame(timerInterval);
    timerInterval = null;
  }
  recordingStartTime = null;

  document.getElementById('rec-btn').classList.remove('recording');
  document.getElementById('rec-status').textContent = '';
  document.getElementById('rec-status').classList.remove('active');
  document.getElementById('rec-status').classList.remove('dead');
  document.getElementById('timer').classList.remove('visible');
  document.getElementById('waveform').classList.remove('visible');
}

// ── Wake lock + dead-recorder watchdog ───────────────────────────────────────
//
// Mobile browsers suspend MediaRecorder when the screen sleeps. Screen Wake
// Lock keeps the screen on so capture stays alive; the watchdog catches the
// case where it dies anyway (Wake Lock API absent, OS overrode it, mic track
// ended, etc.) so the UI doesn't show a ghost timer + dead stop button.

async function acquireWakeLock() {
  if (!('wakeLock' in navigator)) return;
  try {
    wakeLock = await navigator.wakeLock.request('screen');
    wakeLock.addEventListener('release', () => { wakeLock = null; });
  } catch (err) {
    console.warn('Wake lock request failed', err);
  }
}

function releaseWakeLock() {
  if (!wakeLock) return;
  try { wakeLock.release(); } catch (e) { /* best effort */ }
  wakeLock = null;
}

// Browsers auto-release wake locks when the tab goes hidden. Re-acquire when
// the user brings the tab back while a session is still active.
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && session && !wakeLock) {
    acquireWakeLock();
  }
});

function startRecorderWatchdog() {
  stopRecorderWatchdog();
  watchdogInterval = setInterval(() => {
    if (!session || recorderDead) return;
    const stateOk = mediaRecorder && mediaRecorder.state === 'recording';
    const track = audioStream && audioStream.getAudioTracks()[0];
    const trackOk = track && track.readyState === 'live';
    if (!stateOk || !trackOk) {
      handleRecorderDeath();
    }
  }, 2000);
}

function stopRecorderWatchdog() {
  if (watchdogInterval) {
    clearInterval(watchdogInterval);
    watchdogInterval = null;
  }
}

// Recorder died while we still thought we were recording. Halt the timer,
// flag the UI red, and replace the "stop" affordance with a manual finalize
// against the chunks that did reach the server.
function handleRecorderDeath() {
  if (recorderDead) return;
  recorderDead = true;
  stopRecorderWatchdog();
  releaseWakeLock();

  if (timerInterval) {
    cancelAnimationFrame(timerInterval);
    timerInterval = null;
  }
  if (animFrameId) {
    cancelAnimationFrame(animFrameId);
    animFrameId = null;
  }

  const status = document.getElementById('rec-status');
  status.classList.add('dead');
  status.innerHTML = '';
  const msg = document.createElement('span');
  msg.textContent = 'Opname onverwacht gestopt (telefoon-standby?). ';
  status.appendChild(msg);
  const finBtn = document.createElement('button');
  finBtn.textContent = 'Afronden met wat we hebben';
  finBtn.className = 'recovery-action';
  finBtn.onclick = () => finalizeAndResetUI();
  status.appendChild(finBtn);
}

// Shared finalize+reset path. Called from mediaRecorder.onstop (normal stop)
// and from handleRecorderDeath → user clicks "Afronden met wat we hebben".
let finalizing = false;
async function finalizeAndResetUI() {
  if (!session || finalizing) return;
  finalizing = true;
  const sid = session.id;
  showProcessing('Uploaden...');
  try {
    await drainChunks(sid);
    await finalizeSession(sid);
  } catch (err) {
    showProcessing('Upload mislukt: ' + (err.message || err), 5000);
    finalizing = false;
    return;
  }
  await idbDeleteAllChunks(sid);
  await idbDeleteSession(sid);
  session = null;
  finalizing = false;
  recorderDead = false;
  stopRecorderWatchdog();
  releaseWakeLock();
  showProcessing('Verwerken... dit kan enkele minuten duren');
  startPolling(sid);
  document.getElementById('title').value = '';
  document.getElementById('attendees-extra').value = '';
  document.getElementById('agenda').value = '';
  document.getElementById('timer').textContent = '00:00';
  const status = document.getElementById('rec-status');
  status.classList.remove('dead', 'active');
  status.innerHTML = '';
  selectedMembers.clear();
  document.querySelectorAll('.chip.selected').forEach(c => c.classList.remove('selected'));
}

function drawWaveform() {
  const canvas = document.getElementById('waveform-canvas');
  const ctx = canvas.getContext('2d');
  const w = canvas.width = canvas.offsetWidth * 2;
  const h = canvas.height = canvas.offsetHeight * 2;

  function draw() {
    if (!analyserNode) return;
    animFrameId = requestAnimationFrame(draw);
    const data = new Uint8Array(analyserNode.frequencyBinCount);
    analyserNode.getByteFrequencyData(data);

    ctx.fillStyle = '#1e1e1e';
    ctx.fillRect(0, 0, w, h);

    const barW = (w / data.length) * 1.5;
    let x = 0;
    for (let i = 0; i < data.length; i++) {
      const barH = (data[i] / 255) * h;
      ctx.fillStyle = `hsl(210, 80%, ${40 + (data[i] / 255) * 30}%)`;
      ctx.fillRect(x, h - barH, barW - 1, barH);
      x += barW;
    }
  }
  draw();
}

// ── Upload ───────────────────────────────────────────────────────────────────

function showProcessing(message, autoHideMs) {
  const proc = document.getElementById('processing');
  const label = document.getElementById('processing-label');
  proc.classList.add('visible');
  label.textContent = message;
  if (autoHideMs) {
    setTimeout(() => proc.classList.remove('visible'), autoHideMs);
  }
}

// Serialise chunk uploads per session. Multiple ondataavailable events can
// arrive while a POST is still in flight; we want strict in-order delivery
// to avoid 409s on the server, so we chain on the last drain promise.
const _drainPromises = new Map();
function drainChunks(sessionId) {
  const prev = _drainPromises.get(sessionId) || Promise.resolve();
  const next = prev.then(() => _drainChunksOnce(sessionId)).catch((err) => {
    console.warn('drain error', err);
  });
  _drainPromises.set(sessionId, next);
  return next;
}

async function _drainChunksOnce(sessionId) {
  while (true) {
    const pending = await idbChunksForSession(sessionId);
    if (!pending.length) return;
    const head = pending[0];
    const form = new FormData();
    form.append('chunk', head.blob, `c${head.seq}.webm`);
    const url = `/api/upload/chunk?job=${encodeURIComponent(sessionId)}&seq=${head.seq}`;
    let resp;
    try {
      resp = await fetch(url, { method: 'POST', body: form });
    } catch (netErr) {
      // Network blip — leave chunk queued, retry next drain.
      throw netErr;
    }
    if (resp.status === 409 || resp.status === 410) {
      // Server says: out-of-order or session gone. Stop draining; recovery
      // banner on next load can attempt explicit recovery.
      const detail = await resp.text();
      console.warn('chunk rejected', resp.status, detail);
      return;
    }
    if (!resp.ok) {
      throw new Error(`Server ${resp.status} on chunk ${head.seq}`);
    }
    await idbDeleteChunk(sessionId, head.seq);
    if (session && session.id === sessionId) {
      const live = document.getElementById('rec-status');
      if (live && mediaRecorder && mediaRecorder.state === 'recording') {
        // Display as mm:ss so the number maps to the recording timer instead
        // of an opaque seq counter (chunks are 5s each).
        const sentSec = head.seq * 5;
        const mm = String(Math.floor(sentSec / 60)).padStart(2, '0');
        const ss = String(sentSec % 60).padStart(2, '0');
        live.textContent =
          `Opname bezig (verzonden tot ${mm}:${ss}) — laat het scherm aan, druk niet op de aan/uit-knop`;
      }
    }
  }
}

async function finalizeSession(sessionId) {
  const url = `/api/upload/finalize?job=${encodeURIComponent(sessionId)}`;
  const resp = await fetch(url, { method: 'POST' });
  if (!resp.ok) {
    let detail = `Server ${resp.status}`;
    try { detail = (await resp.json()).detail || detail; } catch (e) {}
    throw new Error(detail);
  }
  return resp.json();
}

// pagehide / visibilitychange are the only events iOS reliably fires before
// suspending the tab. sendBeacon is fire-and-forget but survives suspension.
function flushPendingOnHide() {
  if (!session) return;
  // Pull the most recent chunk synchronously-ish from IndexedDB and beacon it.
  idbChunksForSession(session.id).then((pending) => {
    if (!pending.length) return;
    // Only the oldest pending chunk is the next in seq order; sendBeacon
    // posts to /chunk where it's idempotent on duplicates.
    const head = pending[0];
    const form = new FormData();
    form.append('chunk', head.blob, `c${head.seq}.webm`);
    const url = `/api/upload/chunk?job=${encodeURIComponent(session.id)}&seq=${head.seq}`;
    try { navigator.sendBeacon(url, form); } catch (e) { /* best effort */ }
  });
}
window.addEventListener('pagehide', flushPendingOnHide);
window.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') flushPendingOnHide();
});

// ── Recovery ────────────────────────────────────────────────────────────────
//
// On page load, walk the sessions store. For each one:
//   - if the server says it's still recording → offer to resume + finalize
//   - if the server has moved on (pending/transcribing/complete/failed) →
//     drop the local copy silently
//   - if the server returns 404 → drop the local copy silently
// Anything older than 24h is dropped unconditionally (stale browser state).

const RECOVERY_MAX_AGE_MS = 24 * 60 * 60 * 1000;

async function scanForRecovery() {
  let sessions;
  try { sessions = await idbAllSessions(); } catch (e) { return; }
  if (!sessions.length) return;
  for (const s of sessions) {
    if (Date.now() - (s.started_at || 0) > RECOVERY_MAX_AGE_MS) {
      await idbDeleteAllChunks(s.id);
      await idbDeleteSession(s.id);
      continue;
    }
    let serverState;
    try {
      const resp = await fetch(`/api/upload/state?job=${encodeURIComponent(s.id)}`);
      if (resp.status === 404) {
        await idbDeleteAllChunks(s.id);
        await idbDeleteSession(s.id);
        continue;
      }
      if (!resp.ok) continue;
      serverState = await resp.json();
    } catch (e) {
      continue; // try again next page load
    }
    if (serverState.status !== 'recording') {
      // Server already moved past this session.
      await idbDeleteAllChunks(s.id);
      await idbDeleteSession(s.id);
      continue;
    }
    const pending = await idbChunksForSession(s.id);
    showRecoveryBanner(s, pending.length);
    return; // one at a time
  }
}

function showRecoveryBanner(s, pendingCount) {
  const banner = document.getElementById('recovery-banner');
  if (!banner) return;
  const when = new Date(s.started_at).toLocaleString('nl-NL', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
  banner.innerHTML = '';
  const text = document.createElement('span');
  text.textContent = `Onafgeronde opname "${s.title}" van ${when}` +
    (pendingCount ? ` (${pendingCount} chunks lokaal)` : '') + ' — ';
  banner.appendChild(text);
  const resumeBtn = document.createElement('button');
  resumeBtn.textContent = 'Hervat upload';
  resumeBtn.className = 'recovery-action';
  resumeBtn.onclick = () => resumeRecovery(s);
  banner.appendChild(resumeBtn);
  const dropBtn = document.createElement('button');
  dropBtn.textContent = 'Verwerp';
  dropBtn.className = 'recovery-action recovery-drop';
  dropBtn.onclick = () => dropRecovery(s);
  banner.appendChild(dropBtn);
  banner.classList.add('visible');
}

async function resumeRecovery(s) {
  const banner = document.getElementById('recovery-banner');
  banner.textContent = `Hervatten "${s.title}"...`;
  try {
    await drainChunks(s.id);
    await finalizeSession(s.id);
    await idbDeleteAllChunks(s.id);
    await idbDeleteSession(s.id);
    banner.classList.remove('visible');
    showProcessing('Verwerken... dit kan enkele minuten duren');
    startPolling(s.id);
    loadJobs();
  } catch (err) {
    banner.textContent = `Hervatten mislukt: ${err.message || err}`;
  }
}

async function dropRecovery(s) {
  if (!confirm(`Opname "${s.title}" definitief verwerpen?`)) return;
  try { await fetch(`/api/upload/abort?job=${encodeURIComponent(s.id)}`, { method: 'POST' }); }
  catch (e) {}
  await idbDeleteAllChunks(s.id);
  await idbDeleteSession(s.id);
  document.getElementById('recovery-banner').classList.remove('visible');
}

scanForRecovery();

// ── Polling ──────────────────────────────────────────────────────────────────

function startPolling(jobId) {
  if (pollingInterval) clearInterval(pollingInterval);

  pollingInterval = setInterval(async () => {
    try {
      const resp = await fetch(`/api/jobs/${jobId}`);
      const job = await resp.json();

      const label = document.getElementById('processing-label');
      if (job.status === 'transcribing') {
        label.textContent = 'Transcriberen...';
      } else if (job.status === 'structuring') {
        label.textContent = 'Notulen genereren...';
      } else if (job.status === 'committing') {
        // Markdown is done; awaiting the git commit. Keep polling — the
        // git_writer_loop flips it to complete within ~30s (ADR-0020).
        label.textContent = 'Opslaan in git...';
      } else if (job.status === 'complete') {
        label.textContent = 'Klaar!';
        clearInterval(pollingInterval);
        pollingInterval = null;
        setTimeout(() => {
          document.getElementById('processing').classList.remove('visible');
        }, 2000);
        loadJobs();
        expandedJobId = jobId;
      } else if (job.status === 'failed') {
        label.textContent = 'Mislukt: ' + (job.error || 'onbekende fout');
        clearInterval(pollingInterval);
        pollingInterval = null;
        setTimeout(() => {
          document.getElementById('processing').classList.remove('visible');
        }, 5000);
        loadJobs();
      }
    } catch (err) {
      // Ignore polling errors
    }
  }, 3000);
}

// ── Jobs list ────────────────────────────────────────────────────────────────

async function loadJobs() {
  try {
    const resp = await fetch('/api/jobs');
    const data = await resp.json();
    renderJobs(data.jobs || []);
  } catch (err) {
    // Silent fail
  }
}

// Heuristic: a job whose audio is shorter than ~3 min while wall-clock from
// /start (created_at) to completion is >10 min likely got cut off by mobile
// standby. Tag complete jobs only; in-flight ones can still grow. False
// positives are fine — the hint is informational, not blocking.
function looksTruncated(job) {
  if (job.status !== 'complete') return false;
  if (!job.duration_secs || !job.created_at || !job.completed_at) return false;
  const wallClockSec = (new Date(job.completed_at) - new Date(job.created_at)) / 1000;
  if (wallClockSec < 600) return false;       // 10 min wall clock
  if (job.duration_secs > 180) return false;  // 3 min audio
  return true;
}

function renderJobs(jobs) {
  const container = document.getElementById('jobs-list');

  if (!jobs.length) {
    container.innerHTML = '<div class="empty">Nog geen opnames</div>';
    return;
  }

  container.innerHTML = jobs.map(job => {
    const dur = job.duration_secs
      ? `${Math.floor(job.duration_secs / 60)}m ${job.duration_secs % 60}s`
      : '';
    const att = (job.attendees || []).join(', ');
    const isExpanded = expandedJobId === job.id;
    const truncated = looksTruncated(job);

    return `
      <div class="job-card" onclick="toggleJob('${job.id}')">
        <div class="job-header">
          <span class="job-title">${esc(job.title)}</span>
          <span class="badge badge-${job.status}">${job.status}</span>
        </div>
        <div class="job-meta">
          ${job.meeting_date || ''}${dur ? ' · ' + dur : ''}${att ? ' · ' + att : ''}
        </div>
        ${truncated ? '<div class="truncation-hint">Mogelijk afgekapt door telefoon-standby — controleer of dit de hele vergadering is.</div>' : ''}
        ${job.error ? `<div class="error-msg">${esc(job.error)}</div>` : ''}
        ${job.status === 'failed' ? `<button class="delete-btn" style="margin-top:8px" onclick="event.stopPropagation(); deleteJob('${job.id}')">Verwijderen</button>` : ''}
        <div class="job-detail${isExpanded ? ' open' : ''}" id="detail-${job.id}">
          <div id="detail-content-${job.id}">
            ${isExpanded ? '' : '<div class="empty">Laden...</div>'}
          </div>
        </div>
      </div>
    `;
  }).join('');

  // Auto-load expanded job detail
  if (expandedJobId) {
    loadJobDetail(expandedJobId);
  }
}

async function toggleJob(jobId) {
  const detail = document.getElementById(`detail-${jobId}`);
  if (!detail) return;

  if (detail.classList.contains('open')) {
    detail.classList.remove('open');
    expandedJobId = null;
    expandedJobStatus = null;
    return;
  }

  // Close others
  document.querySelectorAll('.job-detail.open').forEach(el => el.classList.remove('open'));
  detail.classList.add('open');
  expandedJobId = jobId;
  expandedJobStatus = null;
  activeTab = 'notulen';  // reset to default on fresh open

  await loadJobDetail(jobId);
}

async function loadJobDetail(jobId) {
  const container = document.getElementById(`detail-content-${jobId}`);
  if (!container) return;

  try {
    const resp = await fetch(`/api/jobs/${jobId}`);
    const job = await resp.json();
    expandedJobStatus = job.status;

    // `committing` already has the full notulen + transcript (only the git
    // sync is pending), so show it like `complete` (ADR-0020).
    if (job.status !== 'complete' && job.status !== 'committing') {
      container.innerHTML = `<div class="empty">${
        job.status === 'failed' ? 'Verwerking mislukt' : 'Nog niet klaar...'
      }</div>`;
      return;
    }

    const isTranscript = activeTab === 'transcript';
    container.innerHTML = `
      <div class="tab-bar">
        <button class="tab${isTranscript ? '' : ' active'}" onclick="event.stopPropagation(); switchTab('${jobId}', 'notulen', this)">Notulen</button>
        <button class="tab${isTranscript ? ' active' : ''}" onclick="event.stopPropagation(); switchTab('${jobId}', 'transcript', this)">Transcript</button>
      </div>
      <div class="tab-content${isTranscript ? '' : ' active'}" id="tab-notulen-${jobId}" onclick="event.stopPropagation()">${esc(job.notulen || '')}</div>
      <div class="tab-content${isTranscript ? ' active' : ''}" id="tab-transcript-${jobId}" onclick="event.stopPropagation()">${esc(job.transcript || '')}</div>
      <a class="download-btn" href="/api/jobs/${jobId}/download" download onclick="event.stopPropagation()">Download .md</a>
      <button class="delete-btn" onclick="event.stopPropagation(); deleteJob('${jobId}')">Verwijderen</button>
    `;
  } catch (err) {
    container.innerHTML = '<div class="empty">Kon details niet laden</div>';
  }
}

function switchTab(jobId, tab, btn) {
  activeTab = tab;  // remember across polling re-renders

  // Update tab buttons
  btn.parentElement.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');

  // Update content
  document.getElementById(`tab-notulen-${jobId}`).classList.toggle('active', tab === 'notulen');
  document.getElementById(`tab-transcript-${jobId}`).classList.toggle('active', tab === 'transcript');
}

async function deleteJob(jobId) {
  if (!confirm('Weet je zeker dat je deze opname wilt verwijderen?')) return;
  try {
    const resp = await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
    if (resp.ok) {
      expandedJobId = null;
      loadJobs();
    }
  } catch (err) {
    // Silent fail
  }
}

function esc(str) {
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}

// Refresh jobs list periodically if any are in progress.
// Skip while the user is reading a completed job — the full re-render
// nukes scroll position in the transcript tab and makes it unreadable.
setInterval(() => {
  if (expandedJobId && expandedJobStatus === 'complete') return;
  const badges = document.querySelectorAll('.badge-pending, .badge-transcribing, .badge-structuring, .badge-committing');
  if (badges.length > 0) loadJobs();
}, 5000);
