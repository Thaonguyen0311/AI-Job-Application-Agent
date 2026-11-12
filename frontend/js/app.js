/* ============================================================
   JobQuest frontend — vanilla JS SPA
   ============================================================ */
const API = (location.protocol === 'file:')
  ? 'http://localhost:8000/api'
  : (localStorage.getItem('jq_api') || '/api');

const state = { token: localStorage.getItem('jq_token') || null,
                username: localStorage.getItem('jq_user') || null,
                profile: null, charts: {} };

/* ---------- tiny helpers ---------- */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const el = (t, cls, html) => { const e = document.createElement(t); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
const esc = s => (s ?? '').toString().replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function toast(msg, kind = '') {
  const t = el('div', 'toast ' + kind, esc(msg));
  $('#toasts').appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateY(8px)'; t.style.transition = 'all .3s'; }, 2600);
  setTimeout(() => t.remove(), 3000);
}

const pendingReads = new Map();

function api(path, options = {}) {
  const { method = 'GET', body, auth = true } = options;
  if (method !== 'GET' && !(method === 'POST' && path === '/cv/preview')) {
    return sendApiRequest(path, options);
  }
  const key = JSON.stringify([auth, state.token, method, path, options.form ?? false, body, options.fresh ?? false]);
  if (!pendingReads.has(key)) {
    const request = sendApiRequest(path, options).finally(() => pendingReads.delete(key));
    pendingReads.set(key, request);
  }
  return pendingReads.get(key);
}

async function sendApiRequest(path, { method = 'GET', body, auth = true, form = false } = {}) {
  const requestToken = state.token;
  const headers = {};
  if (auth && state.token) headers['Authorization'] = 'Bearer ' + state.token;
  let payload;
  if (form) { payload = new URLSearchParams(body); headers['Content-Type'] = 'application/x-www-form-urlencoded'; }
  else if (body !== undefined) { payload = JSON.stringify(body); headers['Content-Type'] = 'application/json'; }
  const res = await fetch(API + path, { method, headers, body: payload });
  if (auth && requestToken !== state.token) throw new Error('Session changed. Please retry.');
  if (res.status === 401 && auth) { logout(); throw new Error('Session expired. Please sign in.'); }
  const ct = res.headers.get('content-type') || '';
  const data = ct.includes('json') ? await res.json() : await res.text();
  if (auth && requestToken !== state.token) throw new Error('Session changed. Please retry.');
  if (!res.ok) throw new Error((data && data.detail) || 'Something went wrong.');
  return data;
}

/* ============================================================
   AUTH
   ============================================================ */
function showAuthView(v) {
  ['login', 'register', 'forgot'].forEach(x => $('#view-' + x).classList.toggle('hidden', x !== v));
  $('#fg-step2').classList.add('hidden');
}
$$('[data-go]').forEach(a => a.onclick = () => showAuthView(a.dataset.go));

function setMsg(id, text, ok = false) {
  const m = $('#' + id); m.textContent = text; m.className = 'form-msg ' + (ok ? 'ok' : 'err');
}

$('#btn-login').onclick = async () => {
  const btn = $('#btn-login'); btn.disabled = true;
  try {
    const d = await api('/auth/login-json', { method: 'POST', auth: false, body: {
      username: $('#login-username').value.trim(), password: $('#login-password').value } });
    saveSession(d);
  } catch (e) { setMsg('login-msg', e.message); }
  btn.disabled = false;
};

$('#btn-register').onclick = async () => {
  const btn = $('#btn-register'); btn.disabled = true;
  try {
    const d = await api('/auth/register', { method: 'POST', auth: false, body: {
      username: $('#reg-username').value.trim(), password: $('#reg-password').value,
      security_question: $('#reg-question').value.trim(), security_answer: $('#reg-answer').value.trim() } });
    saveSession(d); toast('Welcome to JobQuest! 🎉', 'ok');
  } catch (e) { setMsg('reg-msg', e.message); }
  btn.disabled = false;
};

$('#btn-fg-start').onclick = async () => {
  try {
    const d = await api('/auth/forgot/start', { method: 'POST', auth: false, body: { username: $('#fg-username').value.trim() } });
    $('#fg-question-label').textContent = d.security_question;
    $('#fg-step2').classList.remove('hidden');
    setMsg('fg-msg', '', true); $('#fg-msg').className = 'form-msg';
  } catch (e) { setMsg('fg-msg', e.message); }
};

$('#btn-fg-reset').onclick = async () => {
  try {
    const d = await api('/auth/forgot/reset', { method: 'POST', auth: false, body: {
      username: $('#fg-username').value.trim(), security_answer: $('#fg-answer').value.trim(),
      new_password: $('#fg-newpass').value } });
    saveSession(d); toast('Password updated ✓', 'ok');
  } catch (e) { setMsg('fg-msg', e.message); }
};

function saveSession(d) {
  if (state.token && state.token !== d.access_token) logout();
  resetOnboarding();
  state.token = d.access_token; state.username = d.username;
  localStorage.setItem('jq_token', d.access_token);
  localStorage.setItem('jq_user', d.username);
  enterApp();
}
function logout() {
  resetOnboarding();
  state.token = state.username = null; state.profile = null; jobMeta = null;
  jobsCache = [];
  Object.keys(pageCache).forEach(key => { pageCache[key] = null; });
  jobsRequestId++;
  clearTimeout(searchTimer);
  clearTimeout(tourTimer);
  endTour();
  closeModal();
  $('#modal-body').replaceChildren();
  $('#profile-form').replaceChildren();
  Object.values(state.charts).forEach(chart => chart.destroy());
  state.charts = {};
  localStorage.removeItem('jq_token'); localStorage.removeItem('jq_user');
  $('#app').style.display = 'none'; $('#onboarding').classList.remove('show');
  $('#auth').style.display = 'grid';
}
$('#btn-logout').onclick = logout;

/* ============================================================
   NAV / SHELL
   ============================================================ */
function enterApp() {
  const token = state.token;
  $('#auth').style.display = 'none';
  $('#side-username').textContent = state.username;
  $('#side-avatar').textContent = (state.username || 'S')[0].toUpperCase();
  // First-time users must complete onboarding before the app.
  api('/profile').then(p => {
    if (state.token !== token) return;
    state.profile = p;
    if (!p.onboarded) { showOnboarding(); }
    else { finalizeEnterApp(); }
  }).catch(e => {
    if (state.token !== token) return;
    logout();
    setMsg('login-msg', e.message);
  });
}

function finalizeEnterApp() {
  $('#onboarding').classList.remove('show');
  $('#app').style.display = 'block';
  navigate('dashboard');
  maybeAutoTour();
}

/* ---------- Onboarding wizard ---------- */
let onboardingVersion = 0;
function resetOnboarding(profile = {}) {
  onboardingVersion++;
  const onb = $('#onboarding');
  $$('input, textarea', onb).forEach(input => { input.value = ''; });
  $$('.tag', onb).forEach(tag => tag.remove());
  ['full_name', 'email', 'phone', 'location', 'linkedin', 'github', 'university',
   'degree', 'graduation_year', 'gpa', 'summary'].forEach(key => {
    $('#onb-' + key).value = profile[key] || '';
  });
  ['skills', 'languages', 'preferred_roles', 'preferred_locations'].forEach(key => {
    const wrap = $('#onb-' + key), input = $('input', wrap);
    (profile[key] || []).forEach(value => wrap.insertBefore(elFromHTML(tagHTML(value)), input));
  });
  const exp = (profile.experience || [])[0] || {};
  $('#onb-exp-title').value = exp.title || '';
  $('#onb-exp-org').value = exp.org || '';
  $('#onb-exp-bullets').value = (exp.bullets || []).join('\n');
  $('#onb-msg').textContent = ''; $('#onb-msg').className = 'form-msg';
  $('#onb-finish').disabled = false;
  $('#onb-finish').textContent = 'Finish & explore jobs →';
}
function showOnboarding() {
  resetOnboarding(state.profile || {});
  $('#app').style.display = 'none';
  const onb = $('#onboarding');
  onb.classList.add('show');
  $$('.tag-input-wrap', onb).forEach(setupTagInput);
  goStep(0);
  $$('[data-next]', onb).forEach(b => b.onclick = () => {
    if (b.dataset.next === '1' && !validStep0()) return;
    if (b.dataset.next === '2' && !validStep1()) return;
    goStep(+b.dataset.next);
  });
  $$('[data-prev]', onb).forEach(b => b.onclick = () => goStep(+b.dataset.prev));
  $('#onb-finish').onclick = finishOnboarding;
}
function goStep(n) {
  $$('.onb-panel').forEach(p => p.classList.toggle('on', +p.dataset.panel === n));
  $$('.onb-dot').forEach(d => d.classList.toggle('on', +d.dataset.d <= n));
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
function validStep0() {
  const ok = $('#onb-full_name').value.trim() && $('#onb-email').value.trim();
  if (!ok) toast('Please add your name and email.', 'err');
  return ok;
}
function validStep1() {
  const ok = readTags('onb-skills').length > 0;
  if (!ok) toast('Add at least one skill.', 'err');
  return ok;
}
async function finishOnboarding() {
  const btn = $('#onb-finish');
  if (btn.disabled) return;
  const token = state.token, version = onboardingVersion;
  const current = () => token === state.token && version === onboardingVersion;
  const expTitle = $('#onb-exp-title').value.trim();
  const experience = expTitle ? [{
    title: expTitle, org: $('#onb-exp-org').value.trim(), dates: '',
    bullets: $('#onb-exp-bullets').value.split('\n').map(x => x.trim()).filter(Boolean) }] : [];
  const body = {
    full_name: $('#onb-full_name').value, email: $('#onb-email').value,
    phone: $('#onb-phone').value, location: $('#onb-location').value,
    linkedin: $('#onb-linkedin').value, github: $('#onb-github').value,
    university: $('#onb-university').value, degree: $('#onb-degree').value,
    graduation_year: $('#onb-graduation_year').value, gpa: $('#onb-gpa').value,
    summary: $('#onb-summary').value, skills: readTags('onb-skills'),
    languages: readTags('onb-languages'),
    preferred_roles: readTags('onb-preferred_roles'),
    preferred_locations: readTags('onb-preferred_locations'),
    experience, projects: [], hobbies: [], onboarded: true,
  };
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Saving…';
  try {
    const profile = await api('/profile', { method: 'PUT', body });
    if (!current()) return;
    state.profile = profile;
    toast('Profile ready — welcome to JobQuest! 🎉', 'ok');
    finalizeEnterApp();
  } catch (e) { if (current()) setMsg('onb-msg', e.message); }
  finally {
    if (current()) { btn.disabled = false; btn.textContent = 'Finish & explore jobs →'; }
  }
}

function navigate(page) {
  $$('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.nav === page));
  $$('.view').forEach(v => v.classList.add('hidden'));
  $('#page-' + page).classList.remove('hidden');
  closeSidebar();
  if (page === 'dashboard') loadDashboard();
  if (page === 'jobs') loadJobs();
  if (page === 'applications') loadApplications();
  if (page === 'autopilot') loadAutopilot();
  if (page === 'profile') loadProfile();
}
$$('.nav-item').forEach(n => n.onclick = () => navigate(n.dataset.nav));

const openSidebar = () => { $('#sidebar').classList.add('open'); $('#scrim').classList.add('show'); };
const closeSidebar = () => { $('#sidebar').classList.remove('open'); $('#scrim').classList.remove('show'); };
$('#hamb').onclick = openSidebar; $('#scrim').onclick = closeSidebar;

/* ---------- modal ---------- */
function openModal(title, node) {
  $('#modal-title').textContent = title;
  const b = $('#modal-body'); b.innerHTML = ''; b.appendChild(node);
  $('#modal-back').classList.add('show');
}
function closeModal() { $('#modal-back').classList.remove('show'); }
$('#modal-x').onclick = closeModal;
$('#modal-back').onclick = e => { if (e.target.id === 'modal-back') closeModal(); };

/* ============================================================
   GUIDED TOUR (coach marks) — educates a first-time user
   ============================================================ */
const TOUR_STEPS = [
  { target: null, title: "Welcome to JobQuest! 👋",
    body: "Here's a quick 60-second tour of how to go from your profile to submitted applications. You can skip anytime." },
  { page: "dashboard", target: "[data-nav=dashboard]",
    title: "1. Your dashboard",
    body: "Your job hunt at a glance — totals, your application funnel, match-score spread, and what JobQuest learns about you over time." },
  { page: "jobs", target: "[data-nav=jobs]",
    title: "2. Find jobs",
    body: "Every job here is scored against your profile and sorted by how well it fits you." },
  { page: "jobs", target: "#job-country",
    title: "3. Filter your way",
    body: "Narrow the list by country, source (LinkedIn, Indeed, company sites), and minimum match score." },
  { page: "jobs", target: "#jobs-note",
    title: "4. Only jobs you can actually apply to",
    body: "JobQuest shows jobs with a direct application form. Jobs needing an employer-portal login are hidden and never auto-applied to — the count is shown here." },
  { page: "jobs", target: ".job-card", scrollTo: true,
    title: "5. Read a job card",
    body: "Each card shows the source badge, the country, the skills you match, and your personal match score in the ring." },
  { page: "jobs", target: ".job-card [data-review]", scrollTo: true,
    title: "6. Review & apply",
    body: "Opens a tailored CV for that role plus an editable cover letter — adjust anything, then submit. Your CV is auto-built from your profile." },
  { page: "jobs", target: "#btn-auto-open",
    title: "7. Auto-apply",
    body: "In a hurry? Let JobQuest apply to your best matches at once, within the countries and score you choose." },
  { page: "applications", target: "[data-nav=applications]",
    title: "8. Track applications",
    body: "Every submission lands here with its confirmation reference. Change a status (interview, offer, rejected) and JobQuest learns from it." },
  { page: "autopilot", target: "[data-nav=autopilot]",
    title: "9. Daily autopilot",
    body: "Turn on autopilot to auto-apply once a day — set your minimum match score and preferred countries, and it runs on schedule." },
  { page: "profile", target: "[data-nav=profile]",
    title: "10. Keep your profile sharp",
    body: "Your profile powers every CV, cover letter and match score. Update it anytime — you're all set. Happy hunting! 🚀" },
];

let tourIdx = 0;
function startTour() {
  if (!state.token) return;
  window.addEventListener('resize', positionTour);
  tourIdx = 0;
  $('#tour-overlay').classList.add('show');
  showTourStep();
}
function endTour() {
  const wasOpen = $('#tour-overlay').classList.contains('show');
  $('#tour-overlay').classList.remove('show');
  if (wasOpen) {
    try { localStorage.setItem('jq_tour_done_' + (state.username || 'u'), '1'); } catch (e) {}
  }
  window.removeEventListener('resize', positionTour);
}
async function showTourStep() {
  const step = TOUR_STEPS[tourIdx];
  $('#tour-count').textContent = tourIdx === 0 ? 'GET STARTED' : `STEP ${tourIdx} OF ${TOUR_STEPS.length - 1}`;
  $('#tour-title').textContent = step.title;
  $('#tour-body').textContent = step.body;
  $('#tour-back').style.visibility = tourIdx === 0 ? 'hidden' : 'visible';
  $('#tour-next').textContent = tourIdx === TOUR_STEPS.length - 1 ? 'Finish' : 'Next';

  if (step.page) {
    const active = $('.nav-item.active');
    if (!active || active.dataset.nav !== step.page) navigate(step.page);
  }
  // wait for the target to exist (pages load async)
  let tries = 0;
  while (step.target && !$(step.target) && tries < 25) { await new Promise(r => setTimeout(r, 80)); tries++; }
  if (step.scrollTo && step.target && $(step.target)) {
    $(step.target).scrollIntoView({ block: 'center', behavior: 'smooth' });
    await new Promise(r => setTimeout(r, 320));
  }
  positionTour();
}
function positionTour() {
  const step = TOUR_STEPS[tourIdx];
  const hole = $('#tour-hole'), pop = $('#tour-pop');
  const target = step && step.target ? $(step.target) : null;
  if (!target) {
    hole.classList.add('center');
    hole.style.width = hole.style.height = '0px';
    hole.style.top = '50%'; hole.style.left = '50%';
    pop.style.top = '50%'; pop.style.left = '50%';
    pop.style.transform = 'translate(-50%, -50%)';
    return;
  }
  hole.classList.remove('center');
  const r = target.getBoundingClientRect();
  const pad = 8;
  hole.style.top = (r.top - pad) + 'px';
  hole.style.left = (r.left - pad) + 'px';
  hole.style.width = (r.width + pad * 2) + 'px';
  hole.style.height = (r.height + pad * 2) + 'px';

  pop.style.transform = 'none';
  const pw = pop.offsetWidth, ph = pop.offsetHeight;
  const vw = window.innerWidth, vh = window.innerHeight, gap = 14;
  let top, left;
  if (r.right + gap + pw < vw) {            // place to the right (e.g. sidebar)
    left = r.right + gap; top = r.top;
  } else if (r.bottom + gap + ph < vh) {    // below
    top = r.bottom + gap; left = r.left;
  } else if (r.top - gap - ph > 0) {        // above
    top = r.top - gap - ph; left = r.left;
  } else {                                   // fallback: right-clamped
    left = vw - pw - gap; top = gap;
  }
  left = Math.max(gap, Math.min(left, vw - pw - gap));
  top = Math.max(gap, Math.min(top, vh - ph - gap));
  pop.style.top = top + 'px'; pop.style.left = left + 'px';
}
$('#tour-next').onclick = () => {
  if (tourIdx >= TOUR_STEPS.length - 1) { endTour(); return; }
  tourIdx++; showTourStep();
};
$('#tour-back').onclick = () => { if (tourIdx > 0) { tourIdx--; showTourStep(); } };
$('#tour-skip').onclick = endTour;
$('#btn-tour').onclick = startTour;
window.addEventListener('resize', positionTour);

let tourTimer;
function maybeAutoTour() {
  let done = false;
  try { done = localStorage.getItem('jq_tour_done_' + (state.username || 'u')) === '1'; } catch (e) {}
  clearTimeout(tourTimer);
  if (!done) tourTimer = setTimeout(startTour, 700);
}

/* ============================================================
   DASHBOARD
   ============================================================ */
const STATUS_COLORS = { applied: '#6C5CE7', in_review: '#F5A524', interview: '#22C55E',
  offer: '#0EA5A0', rejected: '#EF4444', withdrawn: '#94A3B8' };
const STATUS_LABEL = { applied: 'Applied', in_review: 'In review', interview: 'Interview',
  offer: 'Offer', rejected: 'Rejected', withdrawn: 'Withdrawn', failed: 'Failed' };

function ringClass(score) { return score >= 75 ? 'good' : score >= 50 ? 'mid' : ''; }

function countUp(node, target) {
  const start = performance.now(), dur = 800;
  function step(now) {
    const p = Math.min(1, (now - start) / dur);
    node.textContent = (Math.round(target * (1 - Math.pow(1 - p, 3)) * 10) / 10)
      .toString().replace(/\.0$/, '');
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

async function loadDashboard() {
  const wrap = $('#dash-content');
  wrap.className = 'center-load'; wrap.innerHTML = '<div class="spinner dark"></div>';
  try {
    const d = await api('/dashboard');
    wrap.className = '';
    wrap.innerHTML = `
      <div class="stat-grid">
        <div class="stat accent"><div class="k">Applications</div><div class="v" data-n="${d.total_applications}">0</div><div class="spark"></div></div>
        <div class="stat"><div class="k">Auto-applied</div><div class="v" data-n="${d.auto_applied}">0</div></div>
        <div class="stat"><div class="k">Avg match</div><div class="v" data-n="${d.avg_score}">0</div></div>
        <div class="stat"><div class="k">Interview rate</div><div class="v"><span data-n="${d.interview_rate}">0</span>%</div></div>
      </div>
      <div class="grid-2-13" style="margin-bottom:16px">
        <div class="card"><div class="card-h">Application funnel</div><div class="chart-wrap"><canvas id="ch-funnel"></canvas></div></div>
        <div class="card"><div class="card-h">Match-score distribution</div><div class="chart-wrap"><canvas id="ch-dist"></canvas></div></div>
      </div>
      <div class="grid-2">
        <div class="card"><div class="card-h">What JobQuest learned about you</div><div id="learned-box"></div></div>
        <div class="card"><div class="card-h">Recent activity</div><div id="recent-box"></div></div>
      </div>`;

    $$('[data-n]', wrap).forEach(n => countUp(n, parseFloat(n.dataset.n)));
    renderLearned(d.learned);
    renderRecent(d.recent);
    drawFunnel(d.status_counts);
    drawDist(d.score_buckets);
  } catch (e) { wrap.className = ''; wrap.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
}

function renderLearned(l) {
  const box = $('#learned-box');
  if (!l || l.signal_count === 0) {
    box.innerHTML = `<div class="empty">Update the status of a few applications (interview, rejected, offer…) and JobQuest will start spotting what works for you.</div>`;
    return;
  }
  let html = '';
  if (l.liked_skills?.length) html += `<div style="margin-bottom:12px"><div class="hint" style="margin-bottom:6px">Skills linked to your best outcomes</div><div class="learned-chips">${l.liked_skills.map(s => `<span class="chip lime">${esc(s)}</span>`).join('')}</div></div>`;
  if (l.avoided_skills?.length) html += `<div style="margin-bottom:12px"><div class="hint" style="margin-bottom:6px">Down-ranked after rejections</div><div class="learned-chips">${l.avoided_skills.map(s => `<span class="chip warn">${esc(s)}</span>`).join('')}</div></div>`;
  if (l.liked_companies?.length) html += `<div style="margin-bottom:12px"><div class="hint" style="margin-bottom:6px">Companies you're doing well with</div><div class="learned-chips">${l.liked_companies.map(c => `<span class="chip">${esc(c)}</span>`).join('')}</div></div>`;
  html += `<div class="hint">Remote preference: <b>${l.prefers_remote ? 'yes' : 'no clear signal'}</b> · learned from ${l.signal_count} status update${l.signal_count === 1 ? '' : 's'}${l.rejection_count ? ` (incl. ${l.rejection_count} rejection${l.rejection_count === 1 ? '' : 's'})` : ''}.</div>`;
  box.innerHTML = html;
}

function renderRecent(recent) {
  const box = $('#recent-box');
  if (!recent?.length) { box.innerHTML = `<div class="empty">No applications yet. Head to <b>Find jobs</b> to get started.</div>`; return; }
  box.innerHTML = recent.map(r => `
    <div class="recent-row">
      <div class="ring-score ${ringClass(r.score)}" style="--p:${r.score}"><span>${Math.round(r.score)}</span></div>
      <div class="grow"><div class="t">${esc(r.title)}${r.auto ? '<span class="auto-tag">AUTO</span>' : ''}</div><div class="c">${esc(r.company)}</div></div>
      <span class="status-pill" style="background:${STATUS_COLORS[r.status]}">${STATUS_LABEL[r.status]}</span>
    </div>`).join('');
}

function drawFunnel(counts) {
  if (typeof Chart === 'undefined') return; // CDN blocked / offline
  const order = ['applied', 'in_review', 'interview', 'offer', 'rejected', 'withdrawn'];
  state.charts.funnel?.destroy();
  state.charts.funnel = new Chart($('#ch-funnel'), {
    type: 'bar',
    data: { labels: order.map(s => STATUS_LABEL[s]),
      datasets: [{ data: order.map(s => counts[s] || 0),
        backgroundColor: order.map(s => STATUS_COLORS[s]), borderRadius: 8, barThickness: 26 }] },
    options: { indexAxis: 'y', plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#EEE' } }, y: { grid: { display: false } } },
      responsive: true, maintainAspectRatio: false }
  });
}

function drawDist(buckets) {
  if (typeof Chart === 'undefined') return; // CDN blocked / offline
  state.charts.dist?.destroy();
  state.charts.dist = new Chart($('#ch-dist'), {
    type: 'bar',
    data: { labels: Object.keys(buckets),
      datasets: [{ data: Object.values(buckets), backgroundColor: '#6C5CE7', borderRadius: 8 }] },
    options: { plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#EEE' } }, x: { grid: { display: false } } },
      responsive: true, maintainAspectRatio: false }
  });
}

$('#btn-quick-auto').onclick = () => openAutoApply();

/* ============================================================
   JOBS
   ============================================================ */
let jobsCache = [];
let jobMeta = null;
let jobsRequestId = 0;

const pageCache = {
  profile: null,
  completeness: null,
  autopilot: null
};

async function loadJobs() {
  const requestId = ++jobsRequestId;
  const token = state.token;
  const current = () => requestId === jobsRequestId && token === state.token;
  const wrap = $('#jobs-content');
  wrap.className = 'center-load'; wrap.innerHTML = '<div class="spinner dark"></div>';
  try {
    if (!jobMeta) {
      const meta = await api('/jobs/meta');
      if (!current()) return;
      jobMeta = meta;
    }
    populateJobFilters(jobMeta);
    const min = $('#job-minscore').value, q = $('#job-search').value.trim();
    const country = $('#job-country').value, source = $('#job-source').value;
    const qs = new URLSearchParams({ min_score: min });
    if (q) qs.set('q', q);
    if (country && country !== 'all') qs.set('country', country);
    if (source && source !== 'all') qs.set('source', source);
    const jobs = await api('/jobs/matches?' + qs.toString());
    if (!current()) return;
    jobsCache = jobs;
    wrap.className = '';
    renderJobsNote(jobMeta, jobsCache.length);
    renderJobs(jobsCache);
  } catch (e) { if (current()) { wrap.className = ''; wrap.innerHTML = `<div class="empty">${esc(e.message)}</div>`; } }
}

function populateJobFilters(meta) {
  const cSel = $('#job-country');

  if (cSel.options.length <= 1) {
    [
      'Finland',
      'Denmark',
      'Sweden',
      'Norway',
      'France',
      'Germany',
      'Rest of Europe',
      'European Union'
    ].forEach(c => {
      const o = el('option');
      o.value = c;
      o.textContent = c;
      cSel.appendChild(o);
    });
  }

  const sSel = $('#job-source');
  if (sSel.options.length <= 1) {
    meta.sources.forEach(s => {
      const o = el('option');
      o.value = s.name;
      o.textContent = `${s.name} (${s.count})`;
      sSel.appendChild(o);
    });
  }
}

function renderJobsNote(meta, showing) {
  const sources = meta.sources.map(s => s.name).join(', ');
  $('#jobs-note').innerHTML =
    `Showing <b>${showing}</b> directly-applyable job${showing === 1 ? '' : 's'} from ${esc(sources)}.` +
    (meta.hidden_login_required ? ` <span class="lock">🔒 ${meta.hidden_login_required} hidden — they require signing into an employer portal, so JobQuest won't apply to them.</span>` : '');
}

function srcClass(source) {
  const s = (source || '').toLowerCase();
  if (s.includes('linkedin')) return 'src-linkedin';
  if (s.includes('indeed')) return 'src-indeed';
  if (s.includes('company')) return 'src-company';
  return 'src-other';
}

function renderJobs(jobs) {
  const wrap = $('#jobs-content');
  if (!jobs.length) { wrap.innerHTML = `<div class="empty">No jobs match that filter. Try lowering the match threshold or refreshing the feed.</div>`; return; }
  const list = el('div', 'job-list');
  jobs.forEach(j => {
    const c = el('div', 'job-card');
    const matched = j.matched_skills.map(s => `<span class="skill-tag match">${esc(s)}</span>`).join('');
    const missing = j.missing_skills.slice(0, 4).map(s => `<span class="skill-tag miss">${esc(s)}</span>`).join('');
    c.innerHTML = `
      <div class="ring-score big ${ringClass(j.match_score)}" style="--p:0" data-p="${j.match_score}"><span>${Math.round(j.match_score)}</span></div>
      <div class="job-main">
        <div class="job-title">${esc(j.title)}</div>
        <div class="job-meta"><span class="src-badge ${srcClass(j.source)}">${esc(j.source)}</span> · ${esc(j.company)} ${j.remote ? '' : ` · <span class="country">${esc(j.country || j.location)}</span>`} ${j.remote ? '<span class="tag-remote">Remote</span>' : ''} ${j.requires_cover_letter ? '· <span class="badge-cover">✍ cover letter</span>' : ''}</div>

        <div class="job-skills">${matched}${missing}</div>
      </div>
      <div class="job-actions">
        ${j.application_status === 'failed'
          ? (j.can_retry
            ? `<button class="btn btn-primary btn-sm" data-review="${j.id}">Retry (Demo)</button>`
            : '<button class="btn btn-ghost btn-sm" disabled>Failed · check log</button>')
          : j.already_applied
            ? '<button class="btn btn-ghost btn-sm" disabled>✓ Applied</button>'
            : `<button class="btn btn-primary btn-sm" data-review="${j.id}">Review &amp; apply</button>`}
      </div>`;
    list.appendChild(c);
  });
  wrap.innerHTML = ''; wrap.appendChild(list);
  requestAnimationFrame(() => $$('.ring-score[data-p]', wrap).forEach(r => r.style.setProperty('--p', r.dataset.p)));
  $$('[data-review]', wrap).forEach(b => b.onclick = () => openApplyReview(b.dataset.review));
}

let searchTimer;
$('#job-search').oninput = () => { clearTimeout(searchTimer); searchTimer = setTimeout(loadJobs, 300); };
$('#job-minscore').onchange = loadJobs;
$('#job-country').onchange = loadJobs;
$('#job-source').onchange = loadJobs;
$('#btn-refresh-jobs').onclick = async () => {
  try { const d = await api('/jobs/refresh', { method: 'POST' }); jobMeta = null; toast(`Feed refreshed · ${d.total_applyable} jobs available`, 'ok'); loadJobs(); }
  catch (e) { toast(e.message, 'err'); }
};
$('#btn-auto-open').onclick = () => openAutoApply();

/* ---------- Review & apply modal (manual) ---------- */
async function openApplyReview(jobId, applicationJob = null) {
  const job = applicationJob || jobsCache.find(j => j.id == jobId);
  const node = el('div');
  node.innerHTML = `
    <div class="hint" style="margin-bottom:10px">Your CV is tailored to <b>${esc(job ? job.title : 'this role')}</b>. Content comes from your profile — edit it under <a data-goprofile>My profile</a> to change the CV.</div>
    <div class="doc-preview"><iframe id="cv-frame" sandbox="" title="CV preview"></iframe></div>
    <div class="review-cover">
      <label>Cover letter — edit before sending</label>
      <textarea id="cover-edit" placeholder="Loading a draft…"></textarea>
      <div class="review-note" id="cover-note"></div>
    </div>
    <div style="margin-top:16px;display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">
      <button class="btn btn-ghost btn-sm" id="cv-download">⬇ Download CV (PDF)</button>
      <button class="btn btn-primary" id="do-apply" disabled>Submit application</button>
    </div>
    <div class="form-msg" id="apply-msg"></div>`;
  openModal('Review & apply', node);

  const tpl = 'modern';
  const frame = $('#cv-frame', node);
  const btn = $('#do-apply', node);
  const ta = $('#cover-edit', node);
  const download = $('#cv-download', node);
  const token = state.token;
  const active = () => node.isConnected && token === state.token;
  let previewId = 0, previewReady = false, draftReady = false, submitting = false, retryBlocked = false;
  const updateButtons = () => {
    btn.disabled = !previewReady || !draftReady || submitting || retryBlocked;
    download.disabled = !previewReady || submitting;
  };
  const renderCV = async () => {
    const requestId = ++previewId;
    previewReady = false;
    updateButtons();
    frame.srcdoc = '<div style="display:grid;place-items:center;height:100%;font-family:sans-serif;color:#888">Generating…</div>';
    try {
      const d = await api('/cv/preview', { method: 'POST', body: { job_id: +jobId, template: tpl } });
      if (!active() || requestId !== previewId) return;
      frame.srcdoc = d.html;
      previewReady = true;
    } catch (e) {
      if (active() && requestId === previewId) frame.srcdoc = `<p style="color:#b00">${esc(e.message)}</p>`;
    } finally { if (active() && requestId === previewId) updateButtons(); }
  };
  node.querySelector('[data-goprofile]').onclick = () => { closeModal(); navigate('profile'); };

  download.onclick = () => downloadPDF(jobId, tpl);
  btn.onclick = async () => {
    if (btn.disabled || !active()) return;
    if (job?.requires_cover_letter && !ta.value.trim()) {
      $('#apply-msg', node).textContent = 'Please add the required cover letter.';
      return;
    }
    submitting = true; updateButtons(); btn.innerHTML = '<span class="spinner"></span> Submitting…';
    try {
      const application = await api('/applications', { method: 'POST', body: {
        job_id: +jobId, template: tpl,
        cover_letter: ta.value.trim() ? ta.value : (job && job.requires_cover_letter ? ta.value : ''),
      } });
      if (active()) {
        if (application.status === 'failed') {
          retryBlocked = !application.can_retry;
          setMsg('apply-msg', 'Submission failed. ' + (application.can_retry
            ? 'You can retry this Demo application.'
            : 'Check the submission log and employer portal before taking further action.'));
        } else {
          toast('Application attempt recorded. Check the submission log for its result and mode.', 'ok');
          closeModal();
        }
        if (!$('#page-applications').classList.contains('hidden')) loadApplications();
        else loadJobs();
      }
    } catch (e) {
      if (active()) { $('#apply-msg', node).textContent = e.message; $('#apply-msg', node).className = 'form-msg err'; }
    } finally { submitting = false; btn.innerHTML = 'Submit application'; updateButtons(); }
  };
  renderCV();
  ta.disabled = true;
  try {
    const d = await api('/cv/cover-letter/draft', { method: 'POST', body: { job_id: +jobId } });
    if (!active()) return;
    ta.value = d.cover_letter || '';
    $('#cover-note', node).textContent = job?.requires_cover_letter
      ? 'This role asks for a cover letter. Personalise it, then submit.'
      : 'Optional for this role — leave blank to skip, or edit and send.';
  } catch (e) {
    if (active()) $('#cover-note', node).textContent = 'Draft unavailable. You can write a cover letter here.';
  } finally { draftReady = true; ta.disabled = false; ta.placeholder = 'Write or edit your cover letter'; updateButtons(); }
}

async function downloadPDF(jobId, tpl) {
  try {
    const res = await fetch(API + '/cv/pdf', { method: 'POST',
      headers: { 'Authorization': 'Bearer ' + state.token, 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId ? +jobId : null, template: tpl }) });
    if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'PDF export failed'); }
    const blob = await res.blob();
    const a = el('a'); a.href = URL.createObjectURL(blob); a.download = 'JobQuest_CV.pdf'; a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) { toast(e.message, 'err'); }
}

/* ---------- auto-apply modal ---------- */
function openAutoApply() {
  const countries = (jobMeta && jobMeta.countries) || [];
  const pref = (state.profile && state.profile.preferred_locations) || [];
  const isPref = c => pref.some(p => p.toLowerCase() === c.toLowerCase());
  const node = el('div');
  node.innerHTML = `
    <p class="hint">JobQuest scores every un-applied job and applies to the strongest matches, generating a cover letter automatically wherever the role needs one. Only directly-applyable jobs are included.</p>
    <div class="field"><label>Only apply to jobs above this match score</label>
      <select class="input" id="aa-min"><option value="40">40%+</option><option value="50">50%+</option><option value="60" selected>60%+</option><option value="75">75%+</option></select></div>
    <div class="field"><label>Countries to apply in ${pref.length ? '<span class="hint">(your preferences are pre-selected)</span>' : ''}</label>
      <div class="country-picker" id="aa-countries">
        ${[
  'Finland',
  'Denmark',
  'Sweden',
  'Norway',
  'France',
  'Germany',
  'Rest of Europe',
  'European Union'
].map(c => `<span class="country-opt ${isPref(c) ? 'on' : ''}" data-c="${esc(c)}">${esc(c)}</span>`).join('')}
      </div><div class="hint">Leave all unselected to use your profile's preferred countries. If your profile has none, all countries are eligible.</div></div>
    <div class="field"><label>Maximum applications this run</label>
      <select class="input" id="aa-limit"><option>3</option><option selected>5</option><option>8</option><option>10</option></select></div>
    <div style="text-align:right;margin-top:8px"><button class="btn btn-lime" id="aa-run">⚡ Run auto-apply</button></div>
    <div id="aa-result" style="margin-top:14px"></div>`;
  openModal('Auto-apply', node);
  $$('#aa-countries .country-opt', node).forEach(o => o.onclick = () => o.classList.toggle('on'));
  $('#aa-run').onclick = async () => {
    const btn = $('#aa-run'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Applying…';
    const selCountries = $$('#aa-countries .country-opt.on', node).map(o => o.dataset.c);
    try {
      const created = await api('/applications/auto', { method: 'POST',
        body: { min_score: +$('#aa-min').value, limit: +$('#aa-limit').value, countries: selCountries } });
      const box = $('#aa-result');
      if (!created.length) { box.innerHTML = `<div class="empty">No new jobs met your criteria. Try lowering the score or widening countries.</div>`; }
      else {
        const submitted = created.filter(a => a.status !== 'failed').length;
        box.innerHTML = `<div class="hint" style="margin-bottom:8px">Submitted: ${submitted} · Failed: ${created.length - submitted}</div>` +
          created.map(a => `<div class="recent-row"><div class="ring-score ${ringClass(a.match_score)}" style="--p:${a.match_score}"><span>${Math.round(a.match_score)}</span></div><div class="grow"><div class="t">${esc(a.job.title)}</div><div class="c">${esc(a.job.company)} · ${esc(a.job.country || a.job.location)}</div></div>${a.cover_letter ? '<span class="badge-cover">✍ cover letter</span>' : ''}</div>`).join('');
        toast(`Submitted: ${submitted} · Failed: ${created.length - submitted}`, submitted === created.length ? 'ok' : 'err');
      }
    } catch (e) { toast(e.message, 'err'); }
    btn.disabled = false; btn.innerHTML = '⚡ Run auto-apply';
  };
}

/* ============================================================
   APPLICATIONS
   ============================================================ */
async function loadApplications() {
  const wrap = $('#apps-content');
  wrap.className = 'center-load'; wrap.innerHTML = '<div class="spinner dark"></div>';
  try {
    const apps = await api('/applications');
    wrap.className = '';
    if (!apps.length) { wrap.innerHTML = `<div class="empty">No applications yet. Go to <b>Find jobs</b> and apply — or let auto-apply do the work.</div>`; return; }
    const opts = ['applied', 'in_review', 'interview', 'offer', 'rejected', 'withdrawn'];
    wrap.innerHTML = `
      <table class="app-table">
        <thead><tr><th>Match</th><th>Role</th><th>Company</th><th>Status</th><th>Docs</th></tr></thead>
        <tbody>${apps.map(a => `
          <tr>
            <td><div class="ring-score ${ringClass(a.match_score)}" style="--p:${a.match_score}"><span>${Math.round(a.match_score)}</span></div></td>
            <td><b>${esc(a.job.title)}</b>${a.auto_applied ? '<span class="auto-tag">AUTO</span>' : ''}<div class="c" style="font-size:12px;color:var(--muted)">${esc(a.job.location)}</div>${a.submission_status === 'submitted' ? `<div class="submitted-tag">✓ Submitted · <span class="mono">${esc(a.confirmation_ref)}</span></div>` : ''}</td>
            <td>${esc(a.job.company)}</td>
            <td><select class="status-select" data-app="${a.id}" data-prev="${esc(a.status)}" ${a.status === 'failed' ? 'disabled' : ''}>
              ${a.status === 'failed' ? '<option selected>Failed</option>' : ''}
              ${opts.map(o => `<option value="${o}" ${o === a.status ? 'selected' : ''}>${STATUS_LABEL[o]}</option>`).join('')}
            </select>${a.can_retry
              ? `<button class="btn btn-ghost btn-sm" data-retry="${a.id}">Retry (Demo)</button>`
              : a.status === 'failed' ? '<div class="hint">Check log; retry is not confirmed safe.</div>' : ''}</td>
            <td><button class="btn btn-ghost btn-sm" data-docs="${a.id}">View</button></td>
          </tr>`).join('')}
        </tbody>
      </table>`;
    $$('[data-app]', wrap).forEach(sel => sel.onchange = () => updateStatus(sel.dataset.app, sel.value, sel));
    $$('[data-docs]', wrap).forEach(b => b.onclick = () => openDocs(b.dataset.docs));
    $$('[data-retry]', wrap).forEach(b => b.onclick = () => {
      const application = apps.find(a => a.id == b.dataset.retry);
      openApplyReview(application.job.id, application.job);
    });
  } catch (e) { wrap.className = ''; wrap.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
}

async function updateStatus(id, status, sel) {
  const prev = sel.dataset.prev || 'applied';
  if (prev === status) return;
  sel.disabled = true;
  try {
    await api(`/applications/${id}/status`, { method: 'PATCH', body: { status } });
    sel.dataset.prev = status;
    sel.style.borderColor = STATUS_COLORS[status];
    toast(`Marked as “${STATUS_LABEL[status]}” — JobQuest is learning`, 'ok');
  } catch (e) { toast(e.message, 'err'); sel.value = prev; }
  finally { sel.disabled = false; }
}

async function openDocs(id) {
  const node = el('div', null, '<div class="center-load"><div class="spinner dark"></div></div>');
  openModal('Application documents', node);
  try {
    const d = await api(`/applications/${id}/documents`);
    node.innerHTML = `
      <div class="seg" id="doc-seg"><button class="on" data-doc="cv">CV</button>${d.cover_letter ? '<button data-doc="cover">Cover letter</button>' : ''}</div>
      <div id="doc-cv" class="doc-preview"><iframe sandbox="" title="Application CV"></iframe></div>
      <div id="doc-cover" class="cover-text hidden">${esc(d.cover_letter)}</div>`;
    node.querySelector('#doc-cv iframe').srcdoc = d.cv_html;
    $$('#doc-seg button', node).forEach(b => b.onclick = () => {
      $$('#doc-seg button', node).forEach(x => x.classList.remove('on')); b.classList.add('on');
      $('#doc-cv', node).classList.toggle('hidden', b.dataset.doc !== 'cv');
      $('#doc-cover', node).classList.toggle('hidden', b.dataset.doc !== 'cover');
    });
  } catch (e) { node.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
}

/* ============================================================
   PROFILE
   ============================================================ */
async function loadProfile(force = false) {
  try {

    if (!force && pageCache.profile) {
      state.profile = pageCache.profile;
    } else {
      state.profile = await api('/profile');
      pageCache.profile = state.profile;
    }

    renderProfileForm(state.profile);
    updateCompleteness(force);

  } catch (e) {
    toast(e.message, 'err');
  }
}

function tagField(id, label, values, placeholder) {
  return `<div class="field"><label>${label}</label>
    <div class="tag-input-wrap" id="${id}">
      ${(values || []).map(v => tagHTML(v)).join('')}
      <input placeholder="${placeholder}" data-taginput>
    </div><div class="hint">Type and press Enter to add.</div></div>`;
}
const tagHTML = v => `<span class="tag" data-val="${esc(v)}">${esc(v)}<b>×</b></span>`;

function renderProfileForm(p) {
  const f = $('#profile-form');
  f.innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <div class="card-h">Contact</div>
      <div class="profile-grid">
        <div class="field"><label>Full name</label><input class="input" id="pf-full_name" value="${esc(p.full_name)}"></div>
        <div class="field"><label>Email</label><input class="input" id="pf-email" value="${esc(p.email)}"></div>
        <div class="field"><label>Phone</label><input class="input" id="pf-phone" value="${esc(p.phone)}"></div>
        <div class="field"><label>Location</label><input class="input" id="pf-location" value="${esc(p.location)}"></div>
        <div class="field"><label>LinkedIn username</label><input class="input" id="pf-linkedin" value="${esc(p.linkedin)}"></div>
        <div class="field"><label>GitHub username</label><input class="input" id="pf-github" value="${esc(p.github)}"></div>
      </div>
    </div>

    <div class="card" style="margin-bottom:16px">
      <div class="card-h">Education</div>
      <div class="profile-grid">
        <div class="field"><label>University</label><input class="input" id="pf-university" value="${esc(p.university)}"></div>
        <div class="field"><label>Degree</label><input class="input" id="pf-degree" value="${esc(p.degree)}"></div>
        <div class="field"><label>Graduation year</label><input class="input" id="pf-graduation_year" value="${esc(p.graduation_year)}"></div>
        <div class="field"><label>GPA (optional)</label><input class="input" id="pf-gpa" value="${esc(p.gpa)}"></div>
      </div>
    </div>

    <div class="card" style="margin-bottom:16px">
      <div class="card-h">About you</div>
      <div class="field"><label>Summary</label><textarea class="input" id="pf-summary" placeholder="A sentence or two about you and what you're looking for.">${esc(p.summary)}</textarea></div>
      ${tagField('tg-skills', 'Skills', p.skills, 'e.g. Python')}
      ${tagField('tg-languages', 'Languages', p.languages, 'e.g. English (fluent)')}
      ${tagField('tg-hobbies', 'Hobbies & interests', p.hobbies, 'e.g. Chess')}
      ${tagField('tg-preferred_roles', 'Preferred roles', p.preferred_roles, 'e.g. Frontend Intern')}
      ${tagField('tg-preferred_locations', 'Preferred locations', p.preferred_locations, 'e.g. Remote')}
    </div>

    <div class="card" style="margin-bottom:16px">
      <div class="card-h">Experience</div>
      <div id="exp-list"></div>
      <button class="btn btn-ghost btn-sm" id="add-exp">+ Add experience</button>
    </div>

    <div class="card">
      <div class="card-h">Projects</div>
      <div id="proj-list"></div>
      <button class="btn btn-ghost btn-sm" id="add-proj">+ Add project</button>
    </div>`;

  // tag inputs
  $$('.tag-input-wrap', f).forEach(setupTagInput);
  // repeat blocks
  (p.experience || []).forEach(e => addExpBlock(e));
  (p.projects || []).forEach(pr => addProjBlock(pr));
  $('#add-exp').onclick = () => addExpBlock();
  $('#add-proj').onclick = () => addProjBlock();
}

function setupTagInput(wrap) {
  const input = wrap.querySelector('[data-taginput]');
  wrap.onclick = e => { if (e.target.tagName === 'B') e.target.parentElement.remove(); else input.focus(); };
  input.onkeydown = e => {
    if (e.key === 'Enter' && input.value.trim()) {
      e.preventDefault();
      wrap.insertBefore(elFromHTML(tagHTML(input.value.trim())), input);
      input.value = '';
    } else if (e.key === 'Backspace' && !input.value) {
      const tags = wrap.querySelectorAll('.tag'); if (tags.length) tags[tags.length - 1].remove();
    }
  };
}
const elFromHTML = h => { const d = el('div'); d.innerHTML = h; return d.firstElementChild; };
const readTags = id => $$('#' + id + ' .tag').map(t => t.dataset.val);

function repeatBlock(kind, data = {}) {
  const isExp = kind === 'exp';
  const b = el('div', 'repeat-block');
  b.innerHTML = `
    <button class="rm" title="Remove">×</button>
    <div class="profile-grid">
      <div class="field"><label>${isExp ? 'Title' : 'Project name'}</label><input class="input rb-title" value="${esc(data.title || data.name || '')}"></div>
      ${isExp ? `<div class="field"><label>Organisation</label><input class="input rb-org" value="${esc(data.org || '')}"></div>` : ''}
      <div class="field"><label>Dates</label><input class="input rb-dates" value="${esc(data.dates || '')}" placeholder="e.g. 2024 – Present"></div>
    </div>
    <div class="field"><label>Highlights (one per line)</label><textarea class="input rb-bullets" placeholder="What you did and the impact.">${esc((data.bullets || []).join('\n'))}</textarea></div>`;
  b.querySelector('.rm').onclick = () => b.remove();
  return b;
}
function addExpBlock(d) { $('#exp-list').appendChild(repeatBlock('exp', d)); }
function addProjBlock(d) { $('#proj-list').appendChild(repeatBlock('proj', d)); }

function collectRepeats(listId, isExp) {
  return $$('#' + listId + ' .repeat-block').map(b => {
    const bullets = b.querySelector('.rb-bullets').value.split('\n').map(x => x.trim()).filter(Boolean);
    const base = { dates: b.querySelector('.rb-dates').value.trim(), bullets };
    if (isExp) return { title: b.querySelector('.rb-title').value.trim(), org: b.querySelector('.rb-org').value.trim(), ...base };
    return { name: b.querySelector('.rb-title').value.trim(), ...base };
  }).filter(x => (x.title || x.name));
}

let profileSavePending = false;

async function saveProfile() {
  if (profileSavePending) return;
  const body = {
    full_name: $('#pf-full_name').value, email: $('#pf-email').value, phone: $('#pf-phone').value,
    location: $('#pf-location').value, linkedin: $('#pf-linkedin').value, github: $('#pf-github').value,
    university: $('#pf-university').value, degree: $('#pf-degree').value,
    graduation_year: $('#pf-graduation_year').value, gpa: $('#pf-gpa').value,
    summary: $('#pf-summary').value,
    skills: readTags('tg-skills'), hobbies: readTags('tg-hobbies'), languages: readTags('tg-languages'),
    preferred_roles: readTags('tg-preferred_roles'), preferred_locations: readTags('tg-preferred_locations'),
    experience: collectRepeats('exp-list', true), projects: collectRepeats('proj-list', false),
  };
  const buttons = [$('#btn-save-profile'), $('#btn-save-profile-2')];
  profileSavePending = true;
  buttons.forEach(button => { button.disabled = true; });
  try {
    state.profile = await api('/profile', { method: 'PUT', body });
    pageCache.profile = state.profile;
    pageCache.completeness = null;
    await updateCompleteness(true);
    toast('Profile saved ✓', 'ok');
  } catch (e) {
    toast(e.message, 'err');
  } finally {
    profileSavePending = false;
    buttons.forEach(button => { button.disabled = false; });
  }
}
$('#btn-save-profile').onclick = saveProfile;
$('#btn-save-profile-2').onclick = saveProfile;

async function updateCompleteness(force = false) {

  try {

    let c;

    if (!force && pageCache.completeness) {
      c = pageCache.completeness;
    } else {
      c = await api('/profile/completeness', { fresh: force });
      pageCache.completeness = c;
    }

    $('#comp-bar').style.width = c.percent + '%';
    $('#comp-pct').textContent = c.percent + '%';

    $('#comp-missing').textContent =
      c.missing.length
        ? 'Add for better matches: ' + c.missing.join(', ')
        : 'Your profile is complete — nice work! 🎯';

  } catch {}

}

/* ============================================================
   AUTOPILOT
   ============================================================ */
async function loadAutopilot() {
  const wrap = $('#autopilot-content');
  wrap.className = 'center-load'; wrap.innerHTML = '<div class="spinner dark"></div>';
  try {
    if (!jobMeta) jobMeta = await api('/jobs/meta');
    const [conf, logs] = await Promise.all([api('/autopilot'), api('/autopilot/logs?limit=50')]);
    wrap.className = '';
    renderAutopilot(conf, logs);
  } catch (e) { wrap.className = ''; wrap.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
}

function renderAutopilot(conf, logs) {
  const s = conf.settings, sch = conf.schedule;
  const nextRun = sch.next_run ? new Date(sch.next_run).toLocaleString() : '—';
  const lastRun = s.last_run_at ? new Date(s.last_run_at).toLocaleString() : 'never';
  const wrap = $('#autopilot-content');
  wrap.innerHTML = `
    <div class="ap-hero">
      <div>
        <div class="k">Daily run time (server)</div>
        <div class="when">${esc(sch.time)} <span style="font-size:14px;opacity:.8">${esc(sch.timezone)}</span></div>
        <div class="next">Next scheduled run: ${esc(nextRun)} · Scheduler ${sch.running ? 'running' : (sch.enabled ? 'starting' : 'off')}</div>
      </div>
      <span class="ap-status ${s.enabled ? 'on' : 'off'}">${s.enabled ? 'AUTOPILOT ON' : 'AUTOPILOT OFF'}</span>
    </div>

    <div class="grid-2" style="margin-bottom:16px">
      <div class="card">
        <div class="card-h">Settings</div>
        <div class="ap-row">
          <div><div class="lab">Daily auto-apply</div><div class="desc">Apply automatically each day at the scheduled time.</div></div>
          <label class="toggle"><input type="checkbox" id="ap-enabled" ${s.enabled ? 'checked' : ''}><span class="track"></span></label>
        </div>
        <div class="ap-row">
          <div><div class="lab">Minimum match score</div><div class="desc">Only apply to jobs at or above this fit.</div></div>
          <select class="input" id="ap-min" style="max-width:120px">
            ${[30,40,50,60,70,75].map(v => `<option value="${v}" ${v === Math.round(s.min_score) ? 'selected' : ''}>${v}%+</option>`).join('')}
          </select>
        </div>
        <div class="ap-row">
          <div><div class="lab">Max applications per day</div><div class="desc">A safety cap so it never over-applies.</div></div>
          <select class="input" id="ap-limit" style="max-width:120px">
            ${[3,5,8,10,15].map(v => `<option value="${v}" ${v === s.daily_limit ? 'selected' : ''}>${v}</option>`).join('')}
          </select>
        </div>
        <div style="padding:12px 0">
          <div class="lab" style="margin-bottom:8px">Countries to apply in</div>
          <div class="country-picker" id="ap-countries">
           ${[
  'Finland',
  'Denmark',
  'Sweden',
  'Norway',
  'France',
  'Germany',
  'Rest of Europe',
  'European Union'
].map(c => {
              const saved = (s.countries || []);
              const pref = (state.profile && state.profile.preferred_locations) || [];
              const on = saved.length ? saved.includes(c) : pref.some(p => p.toLowerCase() === c.toLowerCase());
              return `<span class="country-opt ${on ? 'on' : ''}" data-c="${esc(c)}">${esc(c)}</span>`;
            }).join('')}
          </div>
          <div class="hint" style="margin-top:8px">Defaults to your preferred countries. Leave all unselected to use your profile's preferred countries. If your profile has none, all countries are eligible.</div>
        </div>
        <div style="text-align:right;margin-top:14px"><button class="btn btn-primary btn-sm" id="ap-save">Save settings</button></div>
        <div class="hint" style="margin-top:10px">Last run: ${esc(lastRun)}${s.last_run_count ? ` · applied to ${s.last_run_count} job(s)` : ''}</div>
      </div>

      <div class="card">
        <div class="card-h">How it works</div>
        <div class="desc" style="font-size:13.5px;line-height:1.6;color:var(--muted)">
          Every day at <b>${esc(sch.time)} ${esc(sch.timezone)}</b>, JobQuest refreshes the job feed, scores each new role against your profile, and submits applications to the strongest matches — writing a cover letter wherever the posting needs one. Every submission is recorded below with a confirmation reference so you can verify exactly what was sent.
        </div>
        <div class="hint" style="margin-top:12px">Want to see it work right now? Hit <b>Run now</b> at the top.</div>
      </div>
    </div>

    <div class="card">
      <div class="card-h">Submission log <span class="hint" style="font-weight:400">— auditable proof of every application</span></div>
      <div id="ap-logs"></div>
    </div>`;

  renderLogs(logs);
  $$('#ap-countries .country-opt').forEach(o => o.onclick = () => o.classList.toggle('on'));
  $('#ap-save').onclick = saveAutopilot;
  $('#ap-enabled').onchange = () => {
    $('.ap-status').className = 'ap-status ' + ($('#ap-enabled').checked ? 'on' : 'off');
    $('.ap-status').textContent = $('#ap-enabled').checked ? 'AUTOPILOT ON' : 'AUTOPILOT OFF';
  };
}

function renderLogs(logs) {
  const box = $('#ap-logs');
  if (!logs.length) { box.innerHTML = `<div class="empty">No submissions yet. Turn on autopilot or hit “Run now”.</div>`; return; }
  box.innerHTML = `
    <table class="app-table">
      <thead><tr><th>When</th><th>Role</th><th>Type</th><th>Result</th><th>Confirmation</th></tr></thead>
      <tbody>${logs.map(l => `
        <tr>
          <td class="mono">${l.created_at ? new Date(l.created_at).toLocaleString() : '—'}</td>
          <td>${l.job ? `<b>${esc(l.job.title)}</b><div class="desc" style="font-size:12px;color:var(--muted)">${esc(l.job.company)}</div>` : '—'}</td>
          <td><span class="runtype">${esc(l.run_type)}</span></td>
          <td><span class="log-status ${esc(l.status)}">${esc(l.status)}</span></td>
          <td class="mono">${esc(l.confirmation_ref || '—')}</td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

async function saveAutopilot() {
  const btn = $('#ap-save'); btn.disabled = true;
  const countries = $$('#ap-countries .country-opt.on').map(o => o.dataset.c);
  try {
    await api('/autopilot', { method: 'PUT', body: {
      enabled: $('#ap-enabled').checked, min_score: +$('#ap-min').value,
      daily_limit: +$('#ap-limit').value, countries } });
    toast('Autopilot settings saved ✓', 'ok');
  } catch (e) { toast(e.message, 'err'); }
  btn.disabled = false;
}

$('#btn-run-now').onclick = async () => {
  const btn = $('#btn-run-now'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Running…';
  try {
    const created = await api('/autopilot/run-now', { method: 'POST' });
    const submitted = created.filter(a => a.status !== 'failed').length;
    toast(created.length ? `Submitted: ${submitted} · Failed: ${created.length - submitted}` : 'No new jobs met your threshold.', created.length && submitted !== created.length ? 'err' : 'ok');
    loadAutopilot();
  } catch (e) { toast(e.message, 'err'); }
  btn.disabled = false; btn.innerHTML = '⚡ Run now';
};

/* ============================================================
   ROTATOR + BOOT
   ============================================================ */
const ROT = ['Built for <span>students</span>.', 'CVs that <span>fit the job</span>.',
  'Apply while you <span>sleep</span>.', 'Track every <span>callback</span>.'];
let rotI = 0;
setInterval(() => {
  const r = $('#rotator'); if (!r || $('#auth').style.display === 'none') return;
  rotI = (rotI + 1) % ROT.length;
  r.style.opacity = '0';
  setTimeout(() => { r.innerHTML = ROT[rotI]; r.style.transition = 'opacity .4s'; r.style.opacity = '1'; }, 300);
}, 3200);

// enter key on auth forms
['login-password', 'login-username'].forEach(id => $('#' + id).addEventListener('keydown', e => { if (e.key === 'Enter') $('#btn-login').click(); }));

if (state.token) enterApp(); else { $('#auth').style.display = 'grid'; }
