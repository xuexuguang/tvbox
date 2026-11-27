const repo = 'xuexuguang/tvbox';
const branch = 'main';
const contents = `https://api.github.com/repos/${repo}/contents/config/sources.json`;
const raw = `https://raw.githubusercontent.com/${repo}/${branch}`;
const $ = id => document.getElementById(id);
const editor = $('editor');
const form = $('edit-form');
const tokenDialog = $('token-dialog');
const tokenForm = $('token-form');
const tokenStorageKey = 'tvbox.githubToken';
const statusById = new Map();
let config;
let sha;
let token = '';
let editingId;
let writing = false;
let latencySort = 'none';

async function readJson(url, options = {}) {
  const response = await fetch(url, { cache: 'no-store', ...options });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

function githubHeaders() {
  return { Accept: 'application/vnd.github+json', Authorization: `Bearer ${token}` };
}

async function loadRemoteConfig() {
  const file = await readJson(`${contents}?ref=${branch}`, { headers: githubHeaders() });
  const bytes = Uint8Array.from(atob(file.content), char => char.charCodeAt(0));
  config = JSON.parse(new TextDecoder().decode(bytes));
  sha = file.sha;
}

function stateOf(source) {
  const status = statusById.get(source.id);
  if (!status) return '待检测';
  if (status.cached) return '缓存可用';
  return status.ok ? '可用' : '失败';
}

function element(tag, text) {
  const node = document.createElement(tag);
  node.textContent = text;
  return node;
}

function button(text, action, disabled = false) {
  const node = element('button', text);
  node.type = 'button';
  node.disabled = disabled;
  node.addEventListener('click', action);
  return node;
}

function render() {
  if (!config) return;
  const query = $('search').value.trim().toLowerCase();
  const filter = $('filter').querySelector('[aria-pressed="true"]').dataset.filter;
  const visible = config.sources.filter(source => {
    const searchable = [source.name, source.id, ...source.urls].join(' ').toLowerCase();
    return searchable.includes(query) && (filter === 'all' || stateOf(source) === filter);
  });
  if (latencySort !== 'none') {
    const direction = latencySort === 'ascending' ? 1 : -1;
    visible.sort((left, right) => {
      const leftMs = statusById.get(left.id)?.request_ms;
      const rightMs = statusById.get(right.id)?.request_ms;
      if (leftMs == null) return rightMs == null ? 0 : 1;
      if (rightMs == null) return -1;
      return direction * (leftMs - rightMs);
    });
  }
  $('source-count').textContent = `共 ${config.sources.length} 条 · 显示 ${visible.length} 条`;
  for (const [id, label] of [['available', '可用'], ['failed', '失败']]) {
    const badge = $(id);
    badge.hidden = !statusById.size;
    badge.textContent = `${label} ${config.sources.filter(source => stateOf(source) === label).length}`;
  }
  $('sources').replaceChildren(...visible.map(source => {
    const status = statusById.get(source.id);
    const row = document.createElement('tr');
    const name = row.insertCell();
    name.append(element('strong', source.name), element('small', source.id));
    const addresses = row.insertCell();
    addresses.append(element('code', source.urls[0] || '无地址'));
    addresses.append(...source.urls.slice(1).map(url => element('small', url)));
    const health = row.insertCell();
    const label = element('span', stateOf(source));
    label.dataset.state = label.textContent;
    health.append(label);
    if (status?.used_url && !status.cached) label.title = status.used_url;
    const latency = row.insertCell();
    latency.textContent = status?.request_ms != null ? `${status.request_ms} ms` : '—';
    if (status?.error) health.append(element('small', status.error));
    const actions = row.insertCell();
    const result = element('small', '');
    result.setAttribute('role', 'status');
    actions.append(button('测试', event => probe(source, result, event.currentTarget)), ' ',
      button('编辑', () => openEditor(source), writing), ' ',
      button('删除', () => removeSource(source), writing), result);
    return row;
  }));
  if (!visible.length) {
    const cell = $('sources').insertRow().insertCell();
    cell.colSpan = 5;
    cell.textContent = '没有符合条件的源';
  }
  $('add').disabled = writing;
}

async function probe(source, result, control) {
  control.disabled = true;
  result.textContent = '正在测试…';
  const errors = [];
  try {
    if (location.origin === 'http://127.0.0.1:8765') {
      const response = await fetch(`probe?id=${encodeURIComponent(source.id)}`, { method: 'POST' });
      if (response.ok) {
        const tested = await response.json();
        const summary = tested.count == null ? '采集接口可用' : `可用 · ${tested.count} 条`;
        result.textContent = tested.error ? `检测失败 · ${tested.error}` : `${summary} · ${tested.ms} ms · ${tested.url}`;
        return;
      }
      if (response.status !== 404) throw new Error(`本地检测服务返回 HTTP ${response.status}`);
    }
    for (const url of source.urls) {
      const started = performance.now();
      try {
        const target = new URL(url);
        if (source.type === 'cms') {
          target.searchParams.set('ac', 'list');
          target.searchParams.set('pg', '1');
        }
        const data = await readJson(target, { signal: AbortSignal.timeout(6000), credentials: 'omit' });
        const entries = source.type === 'cms' ? data?.list : (data?.sites ?? data?.urls);
        if (!Array.isArray(entries) || !entries.length) throw new Error('未找到有效条目');
        result.textContent = `${entries.length} 条 · ${Math.round(performance.now() - started)} ms · ${url}`;
        return;
      } catch (error) {
        errors.push(error instanceof TypeError ? '浏览器无法读取（网络、跨域或混合内容限制）' : error.message);
      }
    }
    result.textContent = [...new Set(errors)].join('；') || '无地址可测';
  } catch (error) {
    result.textContent = `检测失败 · ${error.message}`;
  } finally {
    control.disabled = false;
  }
}

function openEditor(source) {
  editingId = source?.id;
  $('edit-title').textContent = source ? '编辑源' : '新增源';
  $('edit-message').textContent = '';
  form.elements.name.value = source?.name ?? '';
  form.elements.id.value = source?.id ?? '';
  form.elements.id.readOnly = Boolean(source);
  form.elements.urls.value = source?.urls.join('\n') ?? '';
  editor.showModal();
}

async function save(change, description) {
  if (!token) throw new Error('请先在页面顶部设置 GitHub 令牌。');
  if (!sha) throw new Error('请重新设置令牌，读取 GitHub 上的最新源清单。');
  writing = true;
  render();
  try {
    const next = { ...config, sources: change(config.sources) };
    const bytes = new TextEncoder().encode(`${JSON.stringify(next, null, 2)}\n`);
    const response = await fetch(contents, {
      method: 'PUT',
      headers: { ...githubHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ branch, sha, message: description, content: btoa(Array.from(bytes, byte => String.fromCharCode(byte)).join('')) }),
    });
    if (response.status === 409) {
      sha = undefined;
      throw new Error('源清单已被修改。请重新加载页面，再核对并保存。');
    }
    if (!response.ok) throw new Error(`GitHub 保存失败（HTTP ${response.status}），请检查令牌权限或分支规则。`);
    const saved = await response.json();
    sha = saved.content.sha;
    config = next;
    $('message').textContent = '已保存到 GitHub。可在更新记录中查看订阅生成进度。';
  } finally {
    writing = false;
    render();
  }
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const submit = event.submitter;
  submit.disabled = true;
  try {
    const { name, id, urls } = Object.fromEntries(new FormData(form));
    const addresses = urls.split(/\r?\n/).map(url => url.trim()).filter(Boolean);
    if (!name.trim() || !addresses.length) throw new Error('请填写名称和至少一条地址。');
    for (const url of addresses) {
      if (!/^https?:\/\//i.test(url) || !URL.canParse(url)) throw new Error(`请输入有效的 HTTP 或 HTTPS 地址：${url}`);
    }
    const previous = config.sources.find(source => source.id === editingId);
    if (!previous && config.sources.some(source => source.id === id)) throw new Error('这个源 ID 已存在。');
    const updated = { ...previous, id, name: name.trim(), urls: addresses };
    await save(sources => previous ? sources.map(source => source.id === id ? updated : source) : [...sources, updated], `${previous ? '编辑' : '新增'} TVBox 源 ${id}`);
    statusById.delete(id);
    render();
    editor.close();
  } catch (error) {
    $('edit-message').textContent = error.message;
  } finally {
    submit.disabled = false;
  }
});

async function removeSource(source) {
  if (!token) {
    tokenDialog.showModal();
    return;
  }
  if (!confirm(`从订阅中删除「${source.name}」？`)) return;
  try {
    await save(sources => sources.filter(item => item.id !== source.id), `删除 TVBox 源 ${source.id}`);
    statusById.delete(source.id);
  } catch (error) {
    $('message').textContent = error.message;
  }
}

function rememberedToken() {
  try {
    return localStorage.getItem(tokenStorageKey) ?? '';
  } catch {
    return '';
  }
}

function storeToken(value) {
  try {
    if (value) localStorage.setItem(tokenStorageKey, value);
    else localStorage.removeItem(tokenStorageKey);
    return true;
  } catch {
    return false;
  }
}

async function connectToken(value, remember, restoring = false) {
  const previousToken = token;
  token = value;
  $('auth').disabled = true;
  writing = true;
  render();
  try {
    await loadRemoteConfig();
    const stored = restoring || storeToken(remember ? token : '');
    $('auth').textContent = '管理 GitHub 令牌';
    $('message').textContent = stored ? '已连接 GitHub，可以编辑源。' : '已连接 GitHub，但浏览器无法更新令牌保存设置。';
  } catch (error) {
    token = previousToken;
    if (restoring && error.message === 'HTTP 401') storeToken('');
    $('message').textContent = `GitHub 读取失败（${error.message}），请检查令牌或网络。`;
  } finally {
    $('auth').disabled = false;
    writing = false;
    render();
  }
}

$('auth').addEventListener('click', () => {
  tokenForm.elements.remember.checked = Boolean(rememberedToken());
  tokenDialog.showModal();
});
$('clear-token').addEventListener('click', () => {
  token = '';
  sha = undefined;
  const cleared = storeToken('');
  $('auth').textContent = '设置 GitHub 令牌';
  $('message').textContent = cleared ? '已清除令牌。' : '无法清除浏览器保存的令牌，请清除此网站的数据。';
  tokenForm.reset();
  tokenDialog.close();
});
tokenForm.addEventListener('submit', event => {
  event.preventDefault();
  const value = tokenForm.elements.token.value.trim();
  if (!value) {
    tokenForm.elements.token.value = '';
    tokenForm.elements.token.reportValidity();
    return;
  }
  const remember = tokenForm.elements.remember.checked;
  tokenForm.reset();
  tokenDialog.close();
  void connectToken(value, remember);
});
for (const control of document.querySelectorAll('[data-close]')) {
  control.addEventListener('click', () => $(control.dataset.close).close());
}
for (const [label, filename, accelerated] of [
  ['多仓聚合', '多仓订阅.json', false],
  ['单仓聚合', '单仓聚合.json', false],
  ['多仓 · 加速', '多仓订阅.json', true],
  ['单仓 · 加速', '单仓聚合.json', true],
]) {
  const url = `${accelerated ? 'https://gh-proxy.org/' : ''}${raw}/output/${encodeURIComponent(filename)}`;
  const row = element('div', '');
  row.className = 'subscription-row';
  const badge = element('span', label);
  badge.className = accelerated ? 'route accelerated' : 'route';
  const address = element('code', url);
  address.title = url;
  const copy = button('复制', async () => {
    try {
      await navigator.clipboard.writeText(url);
      copy.textContent = '已复制';
      window.setTimeout(() => { copy.textContent = '复制'; }, 1500);
    } catch {
      $('message').textContent = url;
    }
  });
  copy.setAttribute('aria-label', `复制${label}`);
  row.append(badge, address, copy);
  $('subscriptions').append(row);
}
$('search').addEventListener('input', render);
const statusFilter = $('filter');
const statusTrigger = statusFilter.querySelector('summary');

statusFilter.addEventListener('click', event => {
  const option = event.target.closest('[data-filter]');
  if (!option) return;
  statusFilter.querySelector('[aria-pressed="true"]').setAttribute('aria-pressed', 'false');
  option.setAttribute('aria-pressed', 'true');
  $('filter-label').textContent = option.textContent;
  statusFilter.open = false;
  statusTrigger.focus();
  render();
});

statusFilter.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || !statusFilter.open) return;
  event.preventDefault();
  statusFilter.open = false;
  statusTrigger.focus();
});

document.addEventListener('click', event => {
  if (!statusFilter.contains(event.target)) statusFilter.open = false;
});
const latencySortButtons = document.querySelectorAll('[data-latency-sort]');
for (const control of latencySortButtons) {
  control.addEventListener('click', () => {
    const descending = latencySort === 'ascending';
    latencySort = descending ? 'descending' : 'ascending';
    $('latency-heading').setAttribute('aria-sort', latencySort);
    for (const sortButton of latencySortButtons) {
      sortButton.textContent = descending ? '延迟 ↓' : '延迟 ↑';
      sortButton.setAttribute('aria-label', descending ? '延迟降序，点击切换升序' : '延迟升序，点击切换降序');
    }
    render();
  });
}
$('add').addEventListener('click', () => openEditor());

function showUpdated(timestamp) {
  const badge = $('updated');
  const absolute = `${timestamp}（北京时间）`;
  const instant = Date.parse(`${timestamp.replace(' ', 'T')}+08:00`);
  const refresh = () => {
    const minutes = Math.floor((Date.now() - instant) / 60000);
    let label = absolute;
    if (minutes >= 0 && minutes < 1440) {
      label = minutes === 0 ? '刚刚' : minutes < 60 ? `${minutes} 分钟前` : `${Math.floor(minutes / 60)} 小时前`;
    }
    badge.textContent = `上次更新 ${label}`;
  };
  badge.title = absolute;
  refresh();
  window.setInterval(refresh, 60000);
}

async function start() {
  const [sources, status] = await Promise.allSettled([
    readJson('../config/sources.json'), readJson('../output/status.json'),
  ]);
  if (status.status === 'fulfilled') {
    for (const entry of status.value.sources) statusById.set(entry.id, entry);
    showUpdated(status.value.updated_at);
  } else {
    $('updated').textContent = '暂时无法读取更新状态';
  }
  if (sources.status === 'fulfilled') {
    config ??= sources.value;
    render();
  } else if (!config) {
    $('message').textContent = '无法读取配置源，请刷新后重试。';
  }
}
start();
const savedToken = rememberedToken();
if (savedToken) void connectToken(savedToken, true, true);
