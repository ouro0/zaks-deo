/**
 * app.js — Zak's Deo Download v3
 * © 2024 Zak. Tous droits réservés.
 *
 * Fonctionnalités :
 *  - Mode sombre / clair avec persistance
 *  - Recommandation automatique du meilleur format
 *  - File d'attente multi-liens
 *  - Historique de session (10 derniers téléchargements)
 */

const API = '/api';

// ── Persistance thème ─────────────────────────────────────────────────────────
const savedTheme = sessionStorage.getItem('theme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);

// ── apiFetch ──────────────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  let res;
  try {
    res = await fetch(API + path, { ...opts, headers });
  } catch (e) {
    throw new Error(
      'Impossible de joindre le serveur.\n' +
      'Lancez : python -m uvicorn main:app --port 8000\n' +
      'Puis ouvrez : http://localhost:8000'
    );
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Erreur ${res.status}`);
  return data;
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, type = 'info', ms = 4000) {
  let c = document.getElementById('toast-container');
  if (!c) {
    c = document.createElement('div');
    c.id = 'toast-container';
    c.className = 'toast-container';
    document.body.appendChild(c);
  }
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), ms);
}

// ── Historique session ────────────────────────────────────────────────────────
const SESSION_HISTORY_KEY = 'zaks_history';

function getHistory() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_HISTORY_KEY) || '[]'); }
  catch { return []; }
}

function saveHistory(list) {
  sessionStorage.setItem(SESSION_HISTORY_KEY, JSON.stringify(list.slice(0, 10)));
}

function addToHistory(entry) {
  const list = getHistory();
  // Éviter doublons par URL
  const filtered = list.filter(e => e.url !== entry.url);
  filtered.unshift(entry);
  saveHistory(filtered);
}

// ════════════════════════════════════════
//  INIT PRINCIPALE
// ════════════════════════════════════════
async function initIndex() {
  const $ = id => document.getElementById(id);

  // ── Thème toggle ──────────────────────────────────────────────────────────
  const themeToggle = $('theme-toggle');
  const themeIcon   = $('theme-icon');

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
    sessionStorage.setItem('theme', theme);
  }
  applyTheme(savedTheme);

  themeToggle?.addEventListener('click', () => {
    const cur = document.documentElement.getAttribute('data-theme');
    applyTheme(cur === 'dark' ? 'light' : 'dark');
  });

  // ── Tabs ──────────────────────────────────────────────────────────────────
  const tabBtns   = document.querySelectorAll('.tab-btn');
  const tabPanels = { single: $('tab-single'), multi: $('tab-multi'), history: $('tab-history') };

  tabBtns.forEach(btn => btn.addEventListener('click', () => {
    tabBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const tab = btn.dataset.tab;
    Object.entries(tabPanels).forEach(([k, el]) => {
      if (el) el.style.display = k === tab ? '' : 'none';
    });
    if (tab === 'history') renderHistory();
  }));

  // ════════════════════════════════════════
  //  TAB : Single URL
  // ════════════════════════════════════════
  const urlInput    = $('url-input');
  const dlBtn       = $('dl-btn');
  const fmtBtns     = document.querySelectorAll('#tab-single .fmt-btn');
  const previewCard = $('preview-card');
  const prevThumb   = $('preview-thumb');
  const prevTitle   = $('preview-title');
  const prevMeta    = $('preview-meta');
  const jobProg     = $('job-progress');
  const progBar     = $('progress-bar');
  const progPct     = $('progress-pct');
  const progSpeed   = $('progress-speed');
  const progEta     = $('progress-eta');
  const msgBox      = $('msg-box');
  const dlLink      = $('download-link');
  const recBanner   = $('rec-banner');
  const recText     = $('rec-text');
  const recApply    = $('rec-apply');

  let selectedFmt   = 'video_480';
  let pollId        = null;
  let prevTimeout   = null;
  let lastPreview   = null; // dernières infos vidéo pour l'historique
  let recommendedFmt = null;

  // ── Sélection du format ────────────────────────────────────────────────
  function setFmt(fmt) {
    selectedFmt = fmt;
    fmtBtns.forEach(b => b.classList.toggle('active', b.dataset.fmt === fmt));
  }

  fmtBtns.forEach(btn => btn.addEventListener('click', () => setFmt(btn.dataset.fmt)));

  // ── Recommandation format ──────────────────────────────────────────────
  recApply?.addEventListener('click', () => {
    if (recommendedFmt) {
      setFmt(recommendedFmt);
      if (recBanner) recBanner.style.display = 'none';
      toast(`Format appliqué : ${recommendedFmt}`, 'success', 2500);
    }
  });

  // ── Preview auto ───────────────────────────────────────────────────────
  urlInput?.addEventListener('input', () => {
    clearTimeout(prevTimeout);
    const url = urlInput.value.trim();
    if (url.startsWith('http')) {
      prevTimeout = setTimeout(() => fetchPreview(url), 900);
    } else {
      previewCard?.classList.remove('visible');
      if (recBanner) recBanner.style.display = 'none';
    }
  });

  async function fetchPreview(url) {
    try {
      const info = await apiFetch('/info', {
        method: 'POST',
        body: JSON.stringify({ url, format: selectedFmt })
      });
      lastPreview = { ...info, url };

      if (prevThumb) {
        prevThumb.src = info.thumbnail || '';
        prevThumb.style.display = info.thumbnail ? '' : 'none';
      }
      if (prevTitle) prevTitle.textContent = info.title || 'Sans titre';
      if (prevMeta)  prevMeta.textContent  = `${info.platform || ''} · ${info.duration || '?'} · ${info.uploader || ''}`;
      previewCard?.classList.add('visible');

      // ── Recommandation automatique du meilleur format ──────────────────
      if (info.recommended && info.recommended !== selectedFmt) {
        recommendedFmt = info.recommended;
        if (recText) recText.textContent = `💡 ${info.rec_label} — Appliquer ?`;
        if (recBanner) recBanner.style.display = 'flex';
      } else {
        if (recBanner) recBanner.style.display = 'none';
      }

    } catch {
      previewCard?.classList.remove('visible');
      if (recBanner) recBanner.style.display = 'none';
    }
  }

  // ── Messages ───────────────────────────────────────────────────────────
  function showMsg(text, type = 'error') {
    if (!msgBox) return;
    msgBox.className = `msg msg-${type} visible`;
    const icons = { error: '⚠ ', success: '✓ ', info: 'ℹ ' };
    msgBox.textContent = (icons[type] || '') + text;
  }
  function clearMsg() { if (msgBox) msgBox.className = 'msg'; }

  // ── Bouton télécharger ─────────────────────────────────────────────────
  dlBtn?.addEventListener('click', async () => {
    const url = urlInput?.value.trim();
    if (!url || !url.startsWith('http')) {
      showMsg('Entrez une URL valide (commence par https://)');
      return;
    }

    clearMsg();
    previewCard?.classList.remove('visible');
    if (recBanner) recBanner.style.display = 'none';
    if (dlLink) dlLink.style.display = 'none';
    if (jobProg) jobProg.classList.remove('visible');

    dlBtn.disabled = true;
    dlBtn.innerHTML = '<span class="spinner"></span> Envoi…';

    try {
      const job = await apiFetch('/download', {
        method: 'POST',
        body: JSON.stringify({ url, format: selectedFmt })
      });
      toast('Téléchargement lancé !', 'success');
      startPolling(job.job_id, url);
    } catch (e) {
      showMsg(e.message);
      dlBtn.disabled = false;
      dlBtn.innerHTML = '⬇ Télécharger';
    }
  });

  // ── Polling du statut ──────────────────────────────────────────────────
  function startPolling(jobId, url) {
    if (jobProg) jobProg.classList.add('visible');
    if (progBar) progBar.classList.add('indeterminate');
    clearInterval(pollId);

    pollId = setInterval(async () => {
      try {
        const s = await apiFetch(`/status/${jobId}`);
        const p = s.progress || {};

        if (progBar) {
          progBar.classList.remove('indeterminate');
          progBar.style.width = (p.pct || 0) + '%';
        }
        if (progPct)   progPct.textContent   = (p.pct || 0) + '%';
        if (progSpeed) progSpeed.textContent = p.speed || '—';
        if (progEta)   progEta.textContent   = p.eta   || '—';

        const statusLabel = $('progress-status');
        const labels = {
          pending    : '⏳ En attente…',
          downloading: '⬇ Téléchargement en cours…',
          processing : '⚙ Traitement / fusion…',
          done       : '✓ Terminé !',
          error      : '✗ Erreur',
        };
        if (statusLabel) statusLabel.textContent = labels[s.status] || '…';

        if (s.status === 'done')  { clearInterval(pollId); onDone(jobId, s, url); }
        if (s.status === 'error') { clearInterval(pollId); onError(s.error_msg); }
      } catch {}
    }, 1500);
  }

  function onDone(jobId, s, url) {
    if (progBar) progBar.style.width = '100%';
    if (progPct) progPct.textContent = '100%';
    dlBtn.disabled = false;
    dlBtn.innerHTML = '⬇ Télécharger';
    showMsg('Prêt ! Cliquez sur le bouton vert pour sauvegarder.', 'success');
    if (dlLink) {
      dlLink.href     = `/api/download/${jobId}/file`;
      dlLink.download = s.filename || 'download';
      dlLink.style.display = 'flex';
    }
    // ── Ajout à l'historique ──────────────────────────────────────────
    addToHistory({
      jobId,
      url,
      title     : lastPreview?.title    || s.filename || url,
      thumbnail : lastPreview?.thumbnail || '',
      platform  : lastPreview?.platform  || '',
      duration  : lastPreview?.duration  || '',
      format    : selectedFmt,
      filename  : s.filename || '',
      savedAt   : new Date().toLocaleTimeString('fr-FR'),
    });
  }

  function onError(msg) {
    if (progBar) { progBar.classList.remove('indeterminate'); progBar.style.width = '0%'; }
    if (jobProg) jobProg.classList.remove('visible');
    dlBtn.disabled = false;
    dlBtn.innerHTML = '⬇ Télécharger';
    showMsg(msg || 'Erreur lors du téléchargement. Réessayez.');
  }


  // ════════════════════════════════════════
  //  TAB : Multi-URLs
  // ════════════════════════════════════════
  const multiInput    = $('multi-input');
  const multiDlBtn    = $('multi-dl-btn');
  const queueList     = $('queue-list');
  const multiFmtBtns  = document.querySelectorAll('#multi-format-grid .fmt-btn');
  let multiSelectedFmt = 'video_480';

  multiFmtBtns.forEach(btn => btn.addEventListener('click', () => {
    multiFmtBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    multiSelectedFmt = btn.dataset.fmt;
  }));

  const queueJobs = []; // {jobId, url, el, saveEl}

  multiDlBtn?.addEventListener('click', async () => {
    const raw  = multiInput?.value.trim() || '';
    const urls = raw.split('\n').map(u => u.trim()).filter(u => u.startsWith('http'));
    if (!urls.length) {
      toast('Entrez au moins un lien valide.', 'error');
      return;
    }

    multiDlBtn.disabled = true;
    multiDlBtn.innerHTML = '<span class="spinner"></span> Envoi de la file…';

    try {
      const res = await apiFetch('/download/batch', {
        method: 'POST',
        body: JSON.stringify({ urls, format: multiSelectedFmt })
      });

      if (queueList) queueList.innerHTML = '';
      queueJobs.length = 0;

      // Compteur
      const counter = document.createElement('div');
      counter.className = 'queue-counter';
      counter.id = 'queue-counter';
      if (queueList) queueList.appendChild(counter);

      res.jobs.forEach(j => {
        const item    = document.createElement('div');
        item.className = 'queue-item';

        const urlSpan = document.createElement('span');
        urlSpan.className = 'queue-item-url';
        urlSpan.textContent = j.url;

        const badge = document.createElement('span');
        badge.className = 'queue-item-status status-pending';
        badge.textContent = '⏳ En attente';

        const saveBtn = document.createElement('a');
        saveBtn.className   = 'queue-save-btn';
        saveBtn.textContent = '💾 Sauvegarder';
        saveBtn.target      = '_blank';

        item.appendChild(urlSpan);
        item.appendChild(badge);
        item.appendChild(saveBtn);
        if (queueList) queueList.insertBefore(item, counter);

        queueJobs.push({ jobId: j.job_id, url: j.url, badge, saveBtn });
        pollQueue(j.job_id, queueJobs[queueJobs.length - 1]);
      });

      toast(`${res.total} téléchargements lancés !`, 'success');
      updateCounter();

    } catch (e) {
      toast(e.message, 'error');
    } finally {
      multiDlBtn.disabled = false;
      multiDlBtn.innerHTML = '📋 Lancer la file d\'attente';
    }
  });

  function updateCounter() {
    const counter = $('queue-counter');
    if (!counter) return;
    const done  = queueJobs.filter(j => j.done).length;
    const error = queueJobs.filter(j => j.error).length;
    const total = queueJobs.length;
    counter.textContent = `✅ ${done} / ${total} terminés${error ? ` · ❌ ${error} erreurs` : ''}`;
  }

  function pollQueue(jobId, entry) {
    const intervalId = setInterval(async () => {
      try {
        const s = await apiFetch(`/status/${jobId}`);
        const labels = {
          pending    : { text: '⏳ En attente',  cls: 'status-pending' },
          downloading: { text: '⬇ En cours…',    cls: 'status-processing' },
          processing : { text: '⚙ Traitement…',  cls: 'status-processing' },
          done       : { text: '✓ Terminé',       cls: 'status-done' },
          error      : { text: '✗ Erreur',        cls: 'status-error' },
        };
        const lbl = labels[s.status] || { text: s.status, cls: 'status-pending' };
        entry.badge.className = `queue-item-status ${lbl.cls}`;
        entry.badge.textContent = lbl.text;

        if (s.status === 'done') {
          clearInterval(intervalId);
          entry.done = true;
          entry.saveBtn.href  = `/api/download/${jobId}/file`;
          entry.saveBtn.style.display = 'inline-flex';
          updateCounter();
        }
        if (s.status === 'error') {
          clearInterval(intervalId);
          entry.error = true;
          updateCounter();
        }
      } catch {}
    }, 1800);
  }


  // ════════════════════════════════════════
  //  TAB : Historique
  // ════════════════════════════════════════
  function renderHistory() {
    const list = $('history-list');
    if (!list) return;
    const history = getHistory();
    list.innerHTML = '';

    if (!history.length) {
      list.innerHTML = '<p class="history-empty">Aucun téléchargement dans cette session.</p>';
      return;
    }

    history.forEach(entry => {
      const item = document.createElement('div');
      item.className = 'history-item';

      const thumb = document.createElement('img');
      thumb.className = 'history-thumb';
      thumb.src = entry.thumbnail || '';
      thumb.alt = '';
      if (!entry.thumbnail) thumb.style.display = 'none';

      const info = document.createElement('div');
      info.className = 'history-info';
      info.innerHTML = `
        <div class="history-title">${escHtml(entry.title)}</div>
        <div class="history-meta">${escHtml(entry.platform)} · ${escHtml(entry.format)} · ${escHtml(entry.savedAt)}</div>
      `;

      const reBtn = document.createElement('button');
      reBtn.className = 'history-re-btn';
      reBtn.textContent = '↩ Re-télécharger';
      reBtn.addEventListener('click', () => {
        // Switcher sur l'onglet single et pré-remplir
        tabBtns.forEach(b => b.classList.remove('active'));
        document.querySelector('[data-tab="single"]')?.classList.add('active');
        Object.entries(tabPanels).forEach(([k, el]) => {
          if (el) el.style.display = k === 'single' ? '' : 'none';
        });
        if (urlInput) urlInput.value = entry.url;
        setFmt(entry.format);
        urlInput?.dispatchEvent(new Event('input'));
        toast('URL et format restaurés.', 'info', 2500);
      });

      item.appendChild(thumb);
      item.appendChild(info);
      item.appendChild(reBtn);
      list.appendChild(item);
    });
  }

  $('clear-history-btn')?.addEventListener('click', () => {
    sessionStorage.removeItem(SESSION_HISTORY_KEY);
    renderHistory();
    toast('Historique effacé.', 'info', 2000);
  });

  // ── Util ───────────────────────────────────────────────────────────────
  function escHtml(s = '') {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
}

// ── Auto-init ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initIndex();
});
