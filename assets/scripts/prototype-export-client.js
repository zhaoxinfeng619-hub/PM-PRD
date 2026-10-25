(function () {
  'use strict';
  const cfg = window.PM_RUNTIME || {};
  const server = cfg.server, launcher = cfg.launcher;
  const revisions = new Map();
  let readyPromise = null, exporting = false;
  const path = () => decodeURIComponent(location.pathname);
  function configCheck() {
    if (cfg.readOnly) throw new Error('当前为只读分享模式，请在本地项目执行此操作');
    if (!server || !cfg.projectId || !cfg.token) throw new Error('项目配置缺失，请初始化项目并加载 pm-runtime-config.js');
  }
  async function request(url, payload) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 120000);
    try {
      const response = await fetch(url, {
        method: payload === undefined ? 'GET' : 'POST',
        headers: {'Content-Type':'application/json', 'X-PM-Project':cfg.projectId, 'X-PM-Token':cfg.token},
        body: payload === undefined ? undefined : JSON.stringify(payload),
        cache:'no-store', signal:controller.signal
      });
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || ('HTTP ' + response.status));
      return data;
    } finally { clearTimeout(timer); }
  }
  async function health() {
    const response = await fetch(server + '/api/health', {cache:'no-store', signal:AbortSignal.timeout(3000)});
    const state = await response.json();
    if (state.project_id !== cfg.projectId) {
      const error = new Error('连接到了其他项目，请检查项目配置和端口');
      error.identity = true; throw error;
    }
    if (state.read_only) { const e = new Error('当前服务为只读模式'); e.identity = true; throw e; }
    return state;
  }
  async function ensureReady() {
    configCheck();
    if (readyPromise) return readyPromise;
    readyPromise = (async () => {
      try { return await health(); } catch (e) { if (e.identity) throw e; }
      let launch;
      try { launch = await request(launcher + '/api/launch', {}); }
      catch (e) { throw new Error('服务未启动。请运行 python3 scripts/start_service.py --serve。' + e.message); }
      if (!launch.ok) throw new Error(launch.error || '启动失败');
      const deadline = Date.now() + 45000;
      while (Date.now() < deadline) {
        try { return await health(); } catch (e) { if (e.identity) throw e; }
        await new Promise(r => setTimeout(r, 600));
      }
      throw new Error('启动超时，请在终端执行 --check 查看具体依赖问题');
    })().finally(() => { readyPromise = null; });
    return readyPromise;
  }
  async function api(route, payload) {
    await ensureReady();
    return request(server + route, payload);
  }
  async function revision(file) {
    const data = await api('/api/revision', {path:file || path()});
    revisions.set(file || path(), data.revision);
    return data.revision;
  }
  async function save(content, file) {
    file = file || path();
    if (!revisions.has(file)) throw new Error('尚未读取文件版本，请重新加载页面后再保存');
    const data = await api('/api/save-html', {path:file, content, revision:revisions.get(file)});
    revisions.set(file, data.revision);
    return data;
  }
  async function snapshot(src, opts) {
    opts = opts || {};
    return api('/api/snapshot', {src, base:opts.base || path(), scale:opts.scale || 2,
      viewport:opts.viewport, force:!!opts.force});
  }
  async function asset(src, opts) {
    return api('/api/asset', {src, base:(opts || {}).base || path()});
  }
  async function exportAll(button) {
    if (exporting) return;
    exporting = true;
    const previous = button && button.textContent;
    if (button) {button.disabled = true; button.textContent = '正在连接导出服务…';}
    try {
      const job = await api('/api/screenshot', {path:path(), viewport:{width:innerWidth, height:innerHeight}});
      if (!job.started) throw new Error('导出任务没有启动');
      const deadline = Date.now() + 300000;
      while (Date.now() < deadline) {
        const state = await request(server + '/api/status');
        if (state.job_id !== job.job_id) throw new Error('导出任务已切换，请重新确认结果');
        if (button) button.textContent = '正在导出 ' + state.progress + '/' + state.total;
        if (state.done) {
          if (button) button.textContent = '已导出 ' + state.success_count + ' 张 PNG';
          window.parent.postMessage('export-success', '*');
          return state;
        }
        await new Promise(r => setTimeout(r, 700));
      }
      throw new Error('导出等待超时，请查看服务日志');
    } catch (e) {
      if (button) button.textContent = '导出失败';
      window.alert(e.message);
      window.parent.postMessage('export-error', '*');
    } finally {
      exporting = false;
      if (button) {button.disabled = false; setTimeout(() => button.textContent = previous, 2500);}
    }
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('#exportFab, .export-btn, .export-fab');
    if (!button) return;
    event.preventDefault(); event.stopImmediatePropagation();
    exportAll(button);
  }, true);
  window.addEventListener('message', event => {
    if (event.source !== window.parent || event.data !== 'trigger-export') return;
    exportAll(document.querySelector('#exportFab, .export-btn, .export-fab'));
  });
  window.PMService = {revision, save, api, health};
  window.exportPrototypeViaServer = exportAll;
  window.snapshotPrototypeViaServer = snapshot;
  window.inlineAssetViaServer = asset;
  window.ensureExportServerReady = ensureReady;
})();
