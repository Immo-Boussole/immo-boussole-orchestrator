/**
 * Immo-Boussole Orchestrator — app.js
 *
 * Modules:
 *  - ThemeManager    : dark/light toggle + localStorage persistence
 *  - ToastManager    : toast notification queue
 *  - InstanceActions : REST API wrappers with toast feedback
 *  - LogStream       : SSE log streaming (EventSource)
 *  - StatusPoller    : auto-refresh instance status every 15s
 *  - ModalManager    : open/close modals
 *  - ConfirmDialog   : confirmation dialog before destructive actions
 */

'use strict';

/* ══════════════════════════════════════════════════════════════════════════
   THEME MANAGER
   ══════════════════════════════════════════════════════════════════════════ */

const ThemeManager = (() => {
  const STORAGE_KEY = 'ibo-theme';
  const DARK  = 'dark';
  const LIGHT = 'light';

  function current() {
    return document.documentElement.getAttribute('data-theme') || DARK;
  }

  function apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
    const btn = document.getElementById('btn-theme');
    if (btn) btn.textContent = theme === DARK ? '☀️' : '🌙';
  }

  function toggle() {
    apply(current() === DARK ? LIGHT : DARK);
  }

  function init() {
    const saved = localStorage.getItem(STORAGE_KEY);
    apply(saved || DARK);
    const btn = document.getElementById('btn-theme');
    if (btn) btn.addEventListener('click', toggle);
  }

  return { init, toggle, current };
})();

/* ══════════════════════════════════════════════════════════════════════════
   TOAST MANAGER
   ══════════════════════════════════════════════════════════════════════════ */

const ToastManager = (() => {
  function show(message, type = 'info', duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(16px)';
      toast.style.transition = 'all 0.3s';
      setTimeout(() => toast.remove(), 320);
    }, duration);
  }

  return { show };
})();

/* ══════════════════════════════════════════════════════════════════════════
   MODAL MANAGER
   ══════════════════════════════════════════════════════════════════════════ */

const ModalManager = (() => {
  function open(id) {
    const el = document.getElementById(id);
    if (el) {
      el.classList.add('open');
      // Trap focus on first focusable element
      const first = el.querySelector('input, select, textarea, button');
      if (first) first.focus();
    }
  }

  function close(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('open');
  }

  function closeOnOverlay(e) {
    if (e.target.classList.contains('modal-overlay')) {
      e.target.classList.remove('open');
    }
  }

  function init() {
    // Close modal when clicking overlay background
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', closeOnOverlay);
    });
    // Close buttons
    document.querySelectorAll('[data-modal-close]').forEach(btn => {
      btn.addEventListener('click', () => {
        const target = btn.closest('.modal-overlay');
        if (target) target.classList.remove('open');
      });
    });
    // Escape key
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.open').forEach(el => {
          el.classList.remove('open');
        });
      }
    });
  }

  return { open, close, init };
})();

/* ══════════════════════════════════════════════════════════════════════════
   CONFIRM DIALOG
   ══════════════════════════════════════════════════════════════════════════ */

const ConfirmDialog = (() => {
  function show(message, onConfirm) {
    // Remove any existing dialog
    document.getElementById('confirm-dialog-overlay')?.remove();

    const overlay = document.createElement('div');
    overlay.id = 'confirm-dialog-overlay';
    overlay.className = 'modal-overlay open';
    overlay.innerHTML = `
      <div class="confirm-dialog" role="dialog" aria-modal="true">
        <h3>⚠️ Confirmation</h3>
        <p>${message}</p>
        <div class="confirm-actions">
          <button class="btn btn-ghost" id="confirm-cancel">Cancel</button>
          <button class="btn btn-danger" id="confirm-ok">Confirm</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    overlay.querySelector('#confirm-cancel').addEventListener('click', () => overlay.remove());
    overlay.querySelector('#confirm-ok').addEventListener('click', () => {
      overlay.remove();
      onConfirm();
    });
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  }

  return { show };
})();

/* ══════════════════════════════════════════════════════════════════════════
   INSTANCE ACTIONS
   ══════════════════════════════════════════════════════════════════════════ */

const InstanceActions = (() => {
  async function _call(path, method = 'POST', body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const resp = await fetch(path, opts);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
    return data;
  }

  function _setLoading(btn, loading) {
    if (!btn) return;
    btn.disabled = loading;
    if (loading) {
      btn.dataset.originalText = btn.textContent;
      btn.textContent = '⏳';
    } else {
      btn.textContent = btn.dataset.originalText || btn.textContent;
    }
  }

  async function action(name, actionName, btn = null, body = null) {
    _setLoading(btn, true);
    try {
      const data = await _call(`/api/instances/${encodeURIComponent(name)}/${actionName}`, 'POST', body);
      ToastManager.show(data.message || `${actionName} OK`, 'success');
      setTimeout(() => window.location.reload(), 1200);
    } catch (err) {
      ToastManager.show(`Error: ${err.message}`, 'error', 6000);
    } finally {
      _setLoading(btn, false);
    }
  }

  async function deleteInstance(name, keepVolumes, btn = null) {
    ConfirmDialog.show(
      `Delete instance <strong>${name}</strong>? ${keepVolumes ? 'Volumes will be kept.' : '⚠️ Volumes will also be deleted!'}`,
      async () => {
        _setLoading(btn, true);
        try {
          await _call(
            `/api/instances/${encodeURIComponent(name)}?keep_volumes=${keepVolumes}`,
            'DELETE'
          );
          ToastManager.show(`Instance '${name}' deleted.`, 'success');
          setTimeout(() => (window.location.href = '/'), 1200);
        } catch (err) {
          ToastManager.show(`Error: ${err.message}`, 'error', 6000);
        } finally {
          _setLoading(btn, false);
        }
      }
    );
  }

  async function createInstance(formData, btn = null) {
    _setLoading(btn, true);
    try {
      const data = await _call('/api/instances', 'POST', formData);
      ToastManager.show(`Instance '${data.config.name}' created!`, 'success');
      setTimeout(() => window.location.reload(), 1200);
    } catch (err) {
      ToastManager.show(`Error: ${err.message}`, 'error', 6000);
    } finally {
      _setLoading(btn, false);
    }
  }

  return { action, deleteInstance, createInstance };
})();

/* ══════════════════════════════════════════════════════════════════════════
   LOG STREAM (SSE)
   ══════════════════════════════════════════════════════════════════════════ */

const LogStream = (() => {
  let source = null;
  let autoScroll = true;

  function start(instanceName, terminalEl) {
    if (source) source.close();

    source = new EventSource(`/api/instances/${encodeURIComponent(instanceName)}/logs/stream`);

    source.onmessage = (e) => {
      const line = document.createElement('span');
      line.className = 'log-line' + (e.data.includes('[error]') || e.data.includes('ERROR') ? ' log-line-err' : '');
      line.textContent = e.data + '\n';
      terminalEl.appendChild(line);

      // Keep max 5000 lines to prevent memory leak
      while (terminalEl.children.length > 5000) {
        terminalEl.removeChild(terminalEl.firstChild);
      }

      if (autoScroll) {
        terminalEl.scrollTop = terminalEl.scrollHeight;
      }
    };

    source.onerror = () => {
      const line = document.createElement('span');
      line.className = 'log-line log-line-err';
      line.textContent = '[stream disconnected — reconnecting…]\n';
      terminalEl.appendChild(line);
    };
  }

  function stop() {
    if (source) { source.close(); source = null; }
  }

  function clear(terminalEl) {
    terminalEl.innerHTML = '';
  }

  function setAutoScroll(val) { autoScroll = val; }

  return { start, stop, clear, setAutoScroll };
})();

/* ══════════════════════════════════════════════════════════════════════════
   STATUS POLLER (dashboard auto-refresh)
   ══════════════════════════════════════════════════════════════════════════ */

const StatusPoller = (() => {
  let intervalId = null;

  function updateBadge(name, state, health) {
    const badge = document.querySelector(`[data-instance-badge="${name}"]`);
    if (!badge) return;

    const effectiveState = (health && health !== 'none' && health !== 'healthy')
      ? health
      : state;

    const map = {
      running: ['badge-running', '🟢 Running'],
      exited:  ['badge-exited',  '🔴 Exited'],
      stopped: ['badge-stopped', '🔴 Stopped'],
      unhealthy: ['badge-unhealthy', '🟡 Unhealthy'],
      absent:  ['badge-absent',  '⚪ Absent'],
      error:   ['badge-error',   '⚠️ Error'],
    };

    const [cls, label] = map[effectiveState] || ['badge-unknown', '⚪ Unknown'];
    badge.className = `badge ${cls}`;
    badge.innerHTML = `<span class="badge-dot"></span>${label}`;
  }

  function start(interval = 15000) {
    intervalId = setInterval(async () => {
      try {
        const resp = await fetch('/api/instances');
        if (!resp.ok) return;
        const data = await resp.json();
        data.forEach(item => {
          updateBadge(item.config.name, item.status.state, item.status.health);
        });
      } catch (_) { /* network hiccup, ignore */ }
    }, interval);
  }

  function stop() {
    if (intervalId) { clearInterval(intervalId); intervalId = null; }
  }

  return { start, stop };
})();

/* ══════════════════════════════════════════════════════════════════════════
   CREATE INSTANCE FORM
   ══════════════════════════════════════════════════════════════════════════ */

function initCreateForm() {
  const form = document.getElementById('form-create-instance');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('[type="submit"]');
    const fd = new FormData(form);

    const payload = {
      name:               fd.get('name'),
      host:               fd.get('host') || 'local',
      port:               parseInt(fd.get('port')) || 8000,
      image:              fd.get('image') || null,
      env_file:           fd.get('env_file') || null,
      build_context:      fd.get('build_context') || null,
      description:        fd.get('description') || '',
      start_after_create: fd.get('start_after_create') === 'on',
    };

    await InstanceActions.createInstance(payload, btn);
  });
}

/* ══════════════════════════════════════════════════════════════════════════
   INIT
   ══════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  ThemeManager.init();
  ModalManager.init();
  initCreateForm();

  // Dashboard: start status polling if instance badges exist
  if (document.querySelector('[data-instance-badge]')) {
    StatusPoller.start(15000);
  }

  // Detail page: start log stream
  const terminal = document.getElementById('log-terminal');
  const instanceName = document.querySelector('[data-instance-name]')?.dataset.instanceName;
  if (terminal && instanceName) {
    LogStream.start(instanceName, terminal);

    // Auto-scroll toggle
    const scrollToggle = document.getElementById('btn-autoscroll');
    if (scrollToggle) {
      scrollToggle.addEventListener('click', () => {
        const enabled = scrollToggle.dataset.autoscroll !== 'false';
        LogStream.setAutoScroll(!enabled);
        scrollToggle.dataset.autoscroll = enabled ? 'false' : 'true';
        scrollToggle.textContent = enabled ? '▶ Auto-scroll: OFF' : '▶ Auto-scroll: ON';
      });
    }

    // Clear logs button
    document.getElementById('btn-clear-logs')?.addEventListener('click', () => {
      LogStream.clear(terminal);
    });

    // Stop/Start stream
    const streamBtn = document.getElementById('btn-toggle-stream');
    if (streamBtn) {
      let streaming = true;
      streamBtn.addEventListener('click', () => {
        if (streaming) { LogStream.stop(); streamBtn.textContent = '▶ Start stream'; }
        else           { LogStream.start(instanceName, terminal); streamBtn.textContent = '⏸ Pause stream'; }
        streaming = !streaming;
      });
    }
  }

  // Wire up action buttons (data-action, data-instance)
  document.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const inst = btn.dataset.instance;
      const act  = btn.dataset.action;

      if (act === 'delete') {
        const keepVol = btn.dataset.keepVolumes !== 'false';
        await InstanceActions.deleteInstance(inst, keepVol, btn);
      } else {
        await InstanceActions.action(inst, act, btn);
      }
    });
  });

  // Open add-instance modal
  document.getElementById('btn-add-instance')?.addEventListener('click', () => {
    ModalManager.open('modal-create-instance');
  });

  document.getElementById('fab-add')?.addEventListener('click', () => {
    ModalManager.open('modal-create-instance');
  });
});
