// FleetPlanSync 前端隔离测试（fe-2 · W2）
// 运行：node --test console/static/js/plan-sync-client.test.mjs
//
// 说明：本仓库无 jsdom（Node v24 亦可 `node --experimental-test-domic` 但 Windows
// 下不可靠），故用最小 DOM stub 装载真实模块文件并断言渲染输出；
// 纯逻辑（契约归一化 / 退避 / 事件游标 / 表单校验）不依赖任何 DOM。
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = join(HERE, 'plan-sync-client.js');
const CODE = fs.readFileSync(SRC, 'utf8');

/* ---------------- 最小 DOM stub（仅覆盖被测代码用到的 API） ----------------
 * 约定：元素节点维护「子节点数组 + 文本片段」混合内容（contents），
 * innerHTML getter 由其序列化得到，保证与真实 DOM 一致的「活树」语义：
 * 就地修改子节点（renderRows 的 in-place 更新）后祖先的 innerHTML 自动反映变更。
 */
const TEXT = Symbol('text');

class El {
  constructor(tag) {
    this.tagName = (tag || 'div').toUpperCase();
    this.children = [];
    this.contents = [];
    this.attrs = {};
    this.style = {};
    this.dataset = {};
    this.classList = { add() { }, remove() { }, contains() { return false; } };
    this.value = '';
    this.__listeners = {};
    this.parentElement = null;
  }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  appendChild(c) {
    if (typeof c === 'string') { this.contents.push({ [TEXT]: c }); return c; }
    this.contents.push(c); c.parentElement = this; this.children.push(c); return c;
  }
  remove() {
    if (!this.parentElement) return;
    const p = this.parentElement;
    p.contents = p.contents.filter((c) => c !== this);
    const i = p.children.indexOf(this);
    if (i >= 0) p.children.splice(i, 1);
    this.parentElement = null;
  }
  querySelector(sel) { return collect(this).find((n) => match(n, sel)) || null; }
  querySelectorAll(sel) { return collect(this).filter((n) => match(n, sel)); }
  addEventListener(t, fn) { (this.__listeners[t] = this.__listeners[t] || []).push(fn); }
  removeEventListener() { }
  dispatchEvent(e) {
    (this.__listeners[e.type] || []).forEach((f) => f(e));
    return true;
  }
  get innerHTML() { return serializeContents(this.contents); }
  set innerHTML(v) {
    this.contents = parse(String(v == null ? '' : v), this);
    this.children = this.contents.filter((c) => c instanceof El);
    this.children.forEach((c) => (c.parentElement = this));
  }
  get textContent() {
    return this.contents.map((c) => (c instanceof El ? c.textContent : (c[TEXT] || ''))).join('');
  }
  set textContent(v) {
    this.contents = [{ [TEXT]: String(v == null ? '' : v) }];
    this.children = [];
  }
  get outerHTML() {
    const a = Object.keys(this.attrs).map((k) => `${k}="${this.attrs[k]}"`).join(' ');
    return `<${this.tagName.toLowerCase()}${a ? ' ' + a : ''}>${this.innerHTML}</${this.tagName.toLowerCase()}>`;
  }
}

function escAttr(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function serializeContents(contents) {
  return (contents || []).map((c) => {
    if (c instanceof El) {
      const a = Object.keys(c.attrs).map((k) => `${k}="${escAttr(c.attrs[k])}"`).join(' ');
      return `<${c.tagName.toLowerCase()}${a ? ' ' + a : ''}>${serializeContents(c.contents)}</${c.tagName.toLowerCase()}>`;
    }
    return c[TEXT] || '';
  }).join('');
}

function parse(html, parent) {
  // 支持成对标签（含嵌套）与文本交错：构造「元素/文本混合内容」，
  // 使 innerHTML getter 与 querySelector 都与真实 DOM 语义一致。
  const out = [];
  const SELF = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
  const stack = [];
  const re = /<!--[\s\S]*?-->|(<\/?)([a-zA-Z][\w-]*)((?:"[^"]*"|'[^']*'|[^>"'])*)>|([^<]+)/g;
  let m;
  function fill(el, src) {
    const are = /([\w-]+)="([^"]*)"|([\w-]+)='([^']*)'|([\w-]+)(?=\s|$)/g;
    let a;
    while ((a = are.exec(src)) !== null) {
      const k = a[1] || a[3] || a[5];
      const v = a[2] !== undefined ? a[2] : (a[4] !== undefined ? a[4] : '');
      el.attrs[k] = v;
      if (/^data-/.test(k)) el.dataset[k.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = v;
    }
  }
  function pushNode(el) {
    if (stack.length) {
      const top = stack[stack.length - 1];
      top.contents.push(el);
      if (el instanceof El) { top.children.push(el); el.parentElement = top; }
    } else {
      out.push(el);
      if (el instanceof El) el.parentElement = parent || null;
    }
  }
  while ((m = re.exec(html)) !== null) {
    if (m[4] !== undefined) {           // 文本片段（含空白），原样保留
      pushNode({ [TEXT]: m[4] });
      continue;
    }
    if (m[0].startsWith('<!--')) continue;
    const closing = m[1] === '</';
    const tag = (m[2] || '').toLowerCase();
    if (!tag) continue;
    if (closing) {
      let el = null;
      while (stack.length) { el = stack.pop(); if (el.tagName.toLowerCase() === tag) break; el = null; }
      if (!el) continue;
      pushNode(el);
    } else {
      const el = new El(m[2]);
      fill(el, m[3] || '');
      if (SELF.has(tag) || m[0].endsWith('/>')) {
        pushNode(el);                  // 自闭合：直接挂出
      } else {
        stack.push(el);                // 成对标签：等闭合
      }
    }
  }
  while (stack.length) pushNode(stack.shift());   // 未闭合容错挂出
  return out;
}

function collect(root) {
  // 深度优先收集自身与全部后代（含 innerHTML 解析出的子节点）
  const acc = [root];
  (function walk(n) {
    if (!n.children) return;
    for (const c of n.children) { acc.push(c); walk(c); }
  })(root);
  return acc;
}

function match(el, sel) {
  // 支持：tag / .class / [attr] / [attr="v"] / 逗号 OR / :not([attr])
  // 形如 ".plan:not([data-sync-bound])"
  return sel.split(',').some((part) => matchOne(el, part.trim()));
}

function matchOne(el, sel) {
  if (sel === '*') return true;
  let rest = sel;
  // 反复剥离 :not([attr]) 子句
  for (;;) {
    const m = rest.match(/:not\(\[([\w-]+)\]\)$/);
    if (!m) break;
    if (m[1] in el.attrs) return false;
    rest = rest.slice(0, m.index).trim();
  }
  let ok = false;
  const cls = rest.match(/\.([\w-]+)/);
  const tag = rest.match(/^([a-zA-Z][\w-]*)/);
  const attrs = rest.match(/\[([\w-]+)(?:="([^"]*)")?\]/);
  if (tag && el.tagName) {
    if (el.tagName.toLowerCase() !== tag[1].toLowerCase()) return false;
  }
  if (cls) {
    const list = String(el.attrs.class || '').split(/\s+/);
    if (!list.includes(cls[1])) return false;
  }
  if (attrs) {
    if (!(attrs[1] in el.attrs)) return false;
    if (attrs[2] !== undefined && el.attrs[attrs[1]] !== attrs[2]) return false;
  }
  if (tag) ok = true;
  else if (cls) ok = true;
  else if (attrs) ok = true;
  else if (rest === '') ok = true;
  return ok;
}

// 用 vm 装载真实模块（CommonJS 形态）
function load() {
  const sandbox = {
    module: { exports: {} },
    console,
    setTimeout, clearTimeout,
    Date, Math, JSON, Object, Array, String, Number, Boolean, RegExp, Error, isFinite, isNaN, parseFloat, parseInt,
    encodeURIComponent, decodeURIComponent
  };
  vm.createContext(sandbox);
  vm.runInContext(CODE, sandbox, { filename: 'plan-sync-client.js' });
  return sandbox.module.exports;
}

const S = load();

/* ---------------- 1. 模块装载 ---------------- */

test('模块可在无 window 的 Node 环境装载并导出核心 API', () => {
  assert.equal(typeof S.normalizePlan, 'function');
  assert.equal(typeof S.parseEvents, 'function');
  assert.equal(typeof S.backoffMs, 'function');
  assert.equal(typeof S.createClient, 'function');
  assert.equal(typeof S.buildForm, 'function');
  assert.equal(typeof S.boot, 'function');
  assert.equal(typeof S.esc, 'function');
  assert.equal(S.DEFAULTS.intervalMs, 2000, '轮询间隔应为 2 秒（需求）');
});

/* ---------------- 2. HTML 转义 ---------------- */

test('esc 转义全部 5 个危险字符，防 XSS', () => {
  assert.equal(S.esc('<script>alert(1)</script>'), '&lt;script&gt;alert(1)&lt;/script&gt;');
  assert.equal(S.esc('a&b"c\'d'), 'a&amp;b&quot;c&#39;d');
  assert.equal(S.esc(null), '');
  assert.equal(S.esc(undefined), '');
});

/* ---------------- 3. /api/plan 契约归一化 ---------------- */

test('normalizePlan：W1 规范形状（total/done/progress/tasks）', () => {
  const p = S.normalizePlan({
    project: 'P-004', name: 'AideanBot', total: 11, done: 3, progress: 45,
    tasks: [{ id: 'T-001', title: '实现登录', state: 'DONE', detail: '目标A', assignee: 'worker-a',
              reviewer: 'reviewer-1', verify_cmd: 'grep:a.txt:x,y', rework_count: 1 }]
  });
  assert.equal(p.project, 'P-004');
  assert.equal(p.name, 'AideanBot');
  assert.equal(p.total, 11);
  assert.equal(p.done, 3);
  assert.equal(p.remaining, 8, '剩余数应可由 total-done 推导');
  assert.equal(p.progress, 45);
  assert.equal(p.tasks.length, 1);
  assert.equal(p.tasks[0].id, 'T-001');
  assert.equal(p.tasks[0].verifyCmd, 'grep:a.txt:x,y');
  assert.equal(p.tasks[0].reworkCount, 1);
  assert.equal(p.tasks[0].url, '/tasks/T-001');
});

test('normalizePlan：progress 为 0..1 小数时正确换算为百分数', () => {
  const p = S.normalizePlan({ project: 'P-001', total: 5, done: 2, progress: 0.4, tasks: [] });
  assert.equal(p.progress, 40, '0.4 应表示 40%，不得被四舍五入成 0');
  const p2 = S.normalizePlan({ project: 'P-001', total: 5, done: 2, progress: 100, tasks: [] });
  assert.equal(p2.progress, 100);
  const p3 = S.normalizePlan({ project: 'P-001', total: 1, done: 1, progress: 0, tasks: [] });
  assert.equal(p3.progress, 0, '合法的 0 不得被丢弃');
});

test('normalizePlan：progress 超界钳制到 0..100', () => {
  assert.equal(S.normalizePlan({ total: 1, done: 1, progress: 150, tasks: [] }).progress, 100);
  assert.equal(S.normalizePlan({ total: 1, done: 0, progress: -20, tasks: [] }).progress, 0);
});

test('normalizePlan：total/done 缺失时从 tasks 推导；weight 按状态派生', () => {
  const p = S.normalizePlan({
    project: 'P-002',
    tasks: [
      { id: 'A', title: 'a', state: 'DONE' },
      { id: 'B', title: 'b', state: 'DOING' },
      { id: 'C', title: 'c', state: 'REVIEWING' }
    ]
  });
  assert.equal(p.total, 3, 'total 缺失时应取 tasks 长度');
  assert.equal(p.done, 1, 'done 缺失时按 DONE 计数');
  assert.equal(p.remaining, 2);
  assert.equal(p.tasks[0].weight, 100, 'DONE → 100%');
  assert.equal(p.tasks[1].weight, 20, 'DOING → 20%');
  assert.equal(p.tasks[2].weight, 50, 'REVIEWING → 50%');
  assert.equal(p.progress, 57, '整体进度按 (100+20+50)/3 四舍五入');
});

test('normalizePlan：兼容别名与包裹形状（snake_case / data 包裹 / plan_items）', () => {
  const a = S.normalizePlan({ plan_items: [{ id: 'X', taskState: 'DOING' }], task_total: '1' });
  assert.equal(a.total, 1);
  assert.equal(a.tasks[0].id, 'X');
  assert.equal(a.tasks[0].state, 'DOING');
  const b = S.normalizePlan({ data: { project_id: 'P-9', completed: 2, tasks: [{ id: 'Y', status: 'DONE', executor: 'fe-2' }] } });
  assert.equal(b.project, 'P-9');
  assert.equal(b.done, 2);
  assert.equal(b.tasks[0].assignee, 'fe-2');
  const c = S.normalizePlan({ project: 'P-7', tasks: [{ id: 'Z', state: 'DRAFT' }] });
  assert.equal(c.tasks[0].weight, 0, 'DRAFT 权重 0');
});

test('normalizePlan：任务字段嵌套对象与空数据', () => {
  const p = S.normalizePlan({
    project: 'P-003', total: 1, done: 0, progress: 0,
    tasks: [{ taskId: 'T-9', name: '标题', assignee: { id: 'worker-b', duty: '后端' },
              reviewer: { id: 'reviewer-1' }, verification: 'grep:a:b', state_note: '说明' }]
  });
  assert.equal(p.tasks[0].id, 'T-9');
  assert.equal(p.tasks[0].assignee, 'worker-b', '嵌套对象应取 id');
  assert.equal(p.tasks[0].reviewer, 'reviewer-1');
  assert.equal(p.tasks[0].verifyCmd, 'grep:a:b');
  assert.equal(p.tasks[0].note, '说明');
  const empty = S.normalizePlan({});
  assert.equal(empty.total, 0);
  assert.equal(empty.done, 0);
  assert.equal(empty.remaining, 0);
  assert.equal(empty.progress, 0);
  assert.deepEqual([...empty.tasks], []);
});

test('normalizePlan：保留 ETag 供增量轮询复用', () => {
  assert.equal(S.normalizePlan({ project: 'P-001', total: 0, done: 0, progress: 0, tasks: [], etag: '"abc"' }).etag, '"abc"');
  assert.equal(S.normalizePlan({ project: 'P-001', total: 0, done: 0, progress: 0, tasks: [], cache: { etag: 'v2' } }).etag, 'v2');
  assert.equal(S.normalizePlan({ project: 'P-001', total: 0, done: 0, progress: 0, tasks: [] }).etag, null);
});

/* ---------------- 4. /api/events 解析与增量游标 ---------------- */

test('parseEvents：规范形状 + 兼容数组形状', () => {
  const r = S.parseEvents({
    nextCursor: 7,
    events: [{ seq: 5, ts: '2026-09-14 12:00:00', actor: 'manager', action: 'state:SUBMITTED',
                task: 'T-014', from: 'DOING', to: 'SUBMITTED', assignee: 'worker-a',
                reviewer: 'reviewer-1', detail: '回执已收到', url: '/tasks/T-014' }]
  });
  assert.equal(r.nextCursor, 7);
  assert.equal(r.events.length, 1);
  const e = r.events[0];
  assert.equal(e.seq, 5);
  assert.equal(e.timestamp, '2026-09-14 12:00:00');
  assert.equal(e.actor, 'manager');
  assert.equal(e.action, 'state:SUBMITTED');
  assert.equal(e.taskId, 'T-014');
  assert.equal(e.from, 'DOING');
  assert.equal(e.to, 'SUBMITTED');
  assert.equal(e.assignee, 'worker-a');
  assert.equal(e.reviewer, 'reviewer-1');
  assert.equal(e.url, '/tasks/T-014');
  const bare = S.parseEvents([{ seq: 1, actor: 'console', action: 'task_created', task: 'T-001' }]);
  assert.equal(bare.events.length, 1);
  assert.equal(bare.nextCursor, null);
  assert.deepEqual([...S.parseEvents(null).events], []);
});

test('parseEvents：summary 自动生成且含 actor/action/taskId/from/to', () => {
  const e = S.normalizeEvent({ ts: 't', actor: 'machine-gate', action: 'verify', task: 'T-002' });
  assert.ok(e.summary.includes('machine-gate'), 'summary 应含 actor');
  assert.ok(e.summary.includes('verify'), 'summary 应含 action');
  assert.ok(e.summary.includes('T-002'), 'summary 应含 taskId');
  const e2 = S.normalizeEvent({ ts: 't', actor: 'console', action: 'state:DONE', task: 'T-003',
                                from: 'REVIEWING', to: 'DONE', url: '/tasks/T-003' });
  assert.ok(e2.summary.includes('REVIEWING → DONE'), 'summary 应含状态迁移');
  assert.equal(e2.url, '/tasks/T-003');
});

test('parseEvents：url 缺失时按 taskId 回退生成任务详情 URL', () => {
  const e = S.normalizeEvent({ actor: 'console', action: 'state:DOING', task: 'T-040' });
  assert.equal(e.url, '/tasks/T-040');
  const none = S.normalizeEvent({ actor: 'console', action: 'role_added' });
  assert.equal(none.url, '', '无 taskId 的事件不生成 URL');
});

test('parseEvents：别名与 cursor 字段兼容', () => {
  const r = S.parseEvents({ cursor: 12, items: [{ index: 9, who: 'reviewer-1', type: 'review_reply', task_id: 'T-005' }] });
  assert.equal(r.nextCursor, 12);
  assert.equal(r.events[0].seq, 9);
  assert.equal(r.events[0].actor, 'reviewer-1');
  assert.equal(r.events[0].taskId, 'T-005');
});

/* ---------------- 5. 退避重连 ---------------- */

test('backoffMs：指数增长且不超过上限，最小 50ms', () => {
  const b0 = S.backoffMs(0, S.DEFAULTS);
  const b1 = S.backoffMs(1, S.DEFAULTS);
  const b2 = S.backoffMs(2, S.DEFAULTS);
  assert.ok(b0 >= 50, '下界 50ms');
  assert.ok(b1 >= 50 && b2 >= 50);
  assert.ok(b0 <= S.DEFAULTS.initialBackoffMs * 1.15 * 2, 'attempt 0 应≈1s');
  assert.ok(b1 <= S.DEFAULTS.initialBackoffMs * 2 * 1.15 * 2, 'attempt 1 应≈2s');
  assert.ok(b2 <= S.DEFAULTS.initialBackoffMs * 4 * 1.15 * 2, 'attempt 2 应≈4s');
  for (let i = 0; i < 200; i++) {
    assert.ok(S.backoffMs(i, S.DEFAULTS) <= S.DEFAULTS.maxBackoffMs * 1.15 + 1, '不得超过退避上限（含抖动）');
  }
  assert.ok(S.backoffMs(30, S.DEFAULTS) <= S.DEFAULTS.maxBackoffMs * 1.15 + 1, 'attempt 极大时钳制在 30s 内');
});

test('backoffMs：自定义上限生效', () => {
  const opts = Object.assign({}, S.DEFAULTS, { maxBackoffMs: 1000, jitter: 0 });
  assert.equal(S.backoffMs(5, opts), 1000, 'jitter=0 时严格等于上限');
});

/* ---------------- 6. 同步状态徽标 ---------------- */

test('syncLabelHtml：三种状态文案 + 最后更新时间', () => {
  const d = new Date(2026, 8, 14, 12, 34, 5);
  assert.ok(S.syncLabelHtml('online', d).includes('已同步'), 'online → 已同步');
  assert.ok(S.syncLabelHtml('syncing', d).includes('同步中'), 'syncing → 同步中');
  assert.ok(S.syncLabelHtml('offline', d).includes('已断线'), 'offline → 已断线');
  assert.ok(S.syncLabelHtml('online', d).includes('12:34:05'), '应含最后更新时间');
  assert.ok(S.syncLabelHtml('offline', d, '第 2 次重试 · 退避 2s').includes('退避'), '应含重试信息');
});

test('hhmmss：非法日期显示占位符', () => {
  assert.equal(S.hhmmss(new Date('bad')), '—');
  assert.equal(S.hhmmss(null), '—');
  assert.match(S.hhmmss(new Date(2026, 0, 1, 3, 4, 5)), /^03:04:05$/);
});

/* ---------------- 7. 渲染：局部更新，不整页重建 ---------------- */

test('renderMetrics：首次渲染生成指标块，二次渲染只做局部更新', () => {
  const host = new El('div');
  S.renderMetrics(host, { project: 'P-001', progress: 40, total: 5, done: 2, remaining: 3 });
  assert.ok(host.innerHTML.includes('40%'), '首次渲染含百分比');
  assert.ok(host.innerHTML.includes('data-m-done'), '含 done 节点');
  assert.ok(host.innerHTML.includes('data-rows'), '含任务行容器');
  assert.ok(host.innerHTML.includes('data-sync'), '含同步状态节点');
  assert.ok(host.innerHTML.includes('data-pid="P-001"'), '区块应带 data-pid');

  const before = host.innerHTML;
  S.renderMetrics(host, { project: 'P-001', progress: 60, total: 5, done: 3, remaining: 2 });
  assert.ok(host.innerHTML !== before, '数值变化');
  assert.ok(host.innerHTML.includes('60%'), '百分比更新');
  assert.equal((host.innerHTML.match(/data-m-done/g) || []).length, 1, '不应重复插入指标块');
  assert.ok(!host.innerHTML.includes('40%'), '旧百分比被替换');
});

test('renderRows：按 taskId 就地更新，保留已展开状态', () => {
  const host = new El('div');
  const rows = new El('div');
  rows.className = 'plan-rows';
  host.appendChild(rows);
  S.renderRows(rows, [
    { id: 'T-1', title: '任务一', state: 'DOING', weight: 20, detail: 'd1', assignee: 'a',
      reviewer: '', verifyCmd: 'grep:x:y', reworkCount: 0, note: '', url: '/tasks/T-1' }
  ]);
  assert.ok(rows.innerHTML.includes('data-row="T-1"'), '行应带 data-row');
  assert.ok(rows.innerHTML.includes('data-edit="T-1"'), '行内应有编辑入口');
  assert.ok(rows.innerHTML.includes('grep:x:y'), '含验收命令');

  S.renderRows(rows, [
    { id: 'T-1', title: '任务一（改）', state: 'DONE', weight: 100, detail: 'd2', assignee: 'b',
      reviewer: 'r1', verifyCmd: 'grep:x:z', reworkCount: 2, note: '已收口', url: '/tasks/T-1' }
  ]);
  assert.ok(rows.innerHTML.includes('任务一（改）'), '标题就地更新');
  assert.ok(rows.innerHTML.includes('100%'), '权重就地更新');
  assert.ok(rows.innerHTML.includes('已收口'), '当前说明就地更新');
  assert.ok(rows.innerHTML.includes('2 次'), '返工次数就地更新');
  assert.equal((rows.innerHTML.match(/data-row="T-1"/g) || []).length, 1, '不得重复建行');

  S.renderRows(rows, []);
  assert.ok(rows.innerHTML.includes('暂无任务计划'), '空数据应有占位文案');
});

test('taskRowHtml：转义用户内容且含 URL 与编辑按钮', () => {
  const h = S.taskRowHtml({
    id: 'T-7', title: '<img src=x onerror=alert(1)>', state: 'DRAFT', weight: 0,
    detail: 'a"b', assignee: '', reviewer: '', verifyCmd: '', reworkCount: 0,
    note: '', url: '/tasks/T-7', order: null
  }, false);
  assert.ok(!h.includes('<img src=x'), '标题必须被转义');
  assert.ok(h.includes('&lt;img'), '转义后保留可读文本');
  assert.ok(h.includes('href="/tasks/T-7"'), '含可访问 URL');
  assert.ok(h.includes('data-edit="T-7"'), '含编辑入口');
  assert.ok(h.includes('data-state="DRAFT"'), '含状态标记');
});

test('rowDetailHtml：缺省值显示占位符而非空', () => {
  const h = S.rowDetailHtml({ id: 'T-8', title: 't', state: 'DRAFT', weight: 0, detail: '',
    assignee: '', reviewer: '', verifyCmd: '', reworkCount: 0, note: '', url: '/tasks/T-8' });
  assert.ok(h.includes('未填写'), '目标/验收缺省占位');
  assert.ok(h.includes('暂无'), '当前说明缺省占位');
  assert.ok(h.includes('0 次'), '返工 0 次');
});

/* ---------------- 8. 编辑计划表单：权限与字段边界 ---------------- */

test('buildForm：只读 id/state，仅暴露可编辑字段', () => {
  const html = S.buildForm({
    id: 'T-10', title: '标题', state: 'REVIEWING', weight: 50, detail: '详情',
    assignee: 'worker-a', reviewer: 'reviewer-1', verifyCmd: 'grep:a:b', reworkCount: 1,
    note: '', url: '/tasks/T-10', order: 2
  }, { assignees: [{ id: 'worker-a', duty: '前端' }, { id: 'worker-b', duty: '后端' }],
       reviewers: [{ id: 'reviewer-1', duty: '审查' }] });
  assert.ok(html.includes('data-field="title"'), '可编辑：title');
  assert.ok(html.includes('data-field="detail"'), '可编辑：detail');
  assert.ok(html.includes('data-field="verify_cmd"'), '可编辑：verify_cmd');
  assert.ok(html.includes('data-field="assignee"'), '可编辑：assignee');
  assert.ok(html.includes('data-field="reviewer"'), '可编辑：reviewer');
  assert.ok(html.includes('data-field="order"'), '可编辑：order');
  assert.ok(!/data-field="state"/.test(html), '不可编辑：state');
  assert.ok(!/data-field="project"/.test(html), '不可编辑：project');
  assert.ok(!/data-field="id"/.test(html), '不可编辑：id');
  assert.ok(html.includes('readonly'), '任务编号只读');
  assert.ok(html.includes('maxlength="8192"'), 'title/detail 有长度上限');
  assert.ok(html.includes('maxlength="1024"'), 'verify_cmd 有长度上限');
  assert.ok(html.includes('worker-a') && html.includes('worker-b'), '执行者下拉来自角色清单');
});

test('validateForm：拒绝空标题与空验收命令，并校验长度上限', () => {
  const fake = (vals) => {
    const nodes = Object.keys(vals).map((k) => {
      const i = new El('input'); i.attrs['data-field'] = k; i.value = vals[k]; return i;
    });
    return { querySelectorAll: () => nodes };
  };
  const base = { title: 'ok', detail: '', verify_cmd: 'grep:a:b', assignee: '', reviewer: '', order: '' };
  assert.equal(S.validateForm(fake({ ...base, title: '   ' })).error, S.TITLE_REQUIRED_MSG, '空白标题应被拒');
  assert.equal(S.validateForm(fake({ ...base, title: '' })).error, S.TITLE_REQUIRED_MSG, '空标题应被拒');
  assert.equal(S.validateForm(fake({ ...base, verify_cmd: '' })).error, S.CMD_REQUIRED_MSG, '空验收命令应被拒');
  assert.equal(S.validateForm(fake({ ...base, verify_cmd: '   ' })).error, S.CMD_REQUIRED_MSG, '空白验收命令应被拒');
  assert.equal(S.validateForm(fake(base)).ok, true, '合法输入应通过');
  assert.equal(S.validateForm(fake({ ...base, title: 'x'.repeat(8193) })).ok, false, '标题超长应被拒');
  assert.equal(S.validateForm(fake({ ...base, detail: 'x'.repeat(8193) })).ok, false, '详情超长应被拒');
  assert.equal(S.validateForm(fake({ ...base, verify_cmd: 'x'.repeat(1025) })).ok, false, '验收命令超长应被拒');
  assert.equal(S.validateForm(fake({ ...base, title: 'x'.repeat(8192), verify_cmd: 'x'.repeat(1024) })).ok, true, '恰好等于上限应放行');
});

test('validateForm：payload 不含 state/project/id（前端不越权提交）', () => {
  const vals = { title: 't', detail: 'd', verify_cmd: 'grep:a:b', assignee: 'worker-a', reviewer: '', order: '3' };
  const nodes = Object.keys(vals).map((k) => {
    const i = new El('input'); i.attrs['data-field'] = k; i.value = vals[k]; return i;
  });
  const r = S.validateForm({ querySelectorAll: () => nodes });
  assert.equal(r.ok, true);
  assert.deepEqual(Object.keys(r.payload).sort(), ['assignee', 'detail', 'order', 'reviewer', 'title', 'verify_cmd'].sort());
  assert.equal(r.payload.state, undefined);
  assert.equal(r.payload.project, undefined);
  assert.equal(r.payload.id, undefined);
});

/* ---------------- 9. 客户端：2 秒轮询 / 304 短路 / 失败退避 ---------------- */

function fakeTimer() {
  const q = [];
  let n = 0;
  return {
    queue: q,
    setTimeout: (fn, ms) => { const h = ++n; q.push({ h, fn, ms }); return h; },
    clearTimeout: (h) => {
      const i = q.findIndex((x) => x.h === h);
      if (i >= 0) q.splice(i, 1);
    },
    flush(count) {
      // 执行队列中最多 count 个排程回调（默认全部）；回调会自行重新排程下一次轮询。
      const cur = q.splice(0, q.length);
      cur.slice(0, count == null ? cur.length : count).forEach((x) => x.fn());
    }
  };
}

function fakeFetch(routes) {
  const calls = [];
  return { calls, fn: async (path, opts) => {
    calls.push({ path, opts });
    const r = routes.find((x) => path.startsWith(x.path));
    if (!r) return { ok: false, status: 404, text: async () => '{ "error": "404" }' };
    return r.handler({ path, opts });
  } };
}

test('createClient：启动即请求 /api/plan + /api/events 并渲染', async () => {
  const host = new El('div');
  const f = fakeFetch([
    { path: '/api/plan', handler: () => ({ ok: true, text: async () => JSON.stringify({
      project: 'P-001', total: 2, done: 1, progress: 50,
      tasks: [{ id: 'T-1', title: '甲', state: 'DONE', weight: 100 }, { id: 'T-2', title: '乙', state: 'DOING', weight: 20 }]
    }) }) },
    { path: '/api/events', handler: () => ({ ok: true, text: async () => JSON.stringify({ nextCursor: 3, events: [{ seq: 3, actor: 'console', action: 'state:DONE', task: 'T-1', from: 'DOING', to: 'DONE' }] }) }) }
  ]);
  const tm = fakeTimer();
  const c = S.createClient(host, 'P-001', {
    useSse: false, intervalMs: 2000, jitter: 0, EventSourceImpl: null
  });
  c.state.fetchImpl = f.fn;
  c.state.setTimeoutImpl = tm.setTimeout;
  c.state.clearTimeoutImpl = tm.clearTimeout;
  c.start();
  assert.ok(tm.queue.length >= 1, '启动后应排程下一次轮询（实际 '+tm.queue.length+'）');
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  assert.ok(f.calls.some((x) => x.path.startsWith('/api/plan?project=P-001')), '应请求 /api/plan?project=');
  assert.ok(f.calls.some((x) => x.path.startsWith('/api/events?project=P-001')), '应请求 /api/events?project=');
  assert.ok(f.calls.some((x) => x.path.includes('since=')), '事件请求应带 since 游标');
  assert.ok(host.innerHTML.includes('50%'), '整体百分比已渲染');
  assert.ok(host.innerHTML.includes('T-1') && host.innerHTML.includes('T-2'), '任务条已渲染');
  assert.equal(c.state.cursor, 3, '游标应推进到 nextCursor');
  assert.ok(host.innerHTML.includes('已同步'), '状态徽标应显示已同步');
  const ms = tm.queue[0].ms;
  assert.ok(ms >= 1900 && ms <= 2100, `轮询间隔应≈2000ms（实际 ${ms}）`);
  c.stop();
});

test('createClient：ETag 命中时发送 If-None-Match 并处理 304（不重复渲染）', async () => {
  const host = new El('div');
  let n = 0;
  const f = fakeFetch([
    { path: '/api/plan', handler: () => {
      n++;
      if (n === 1) return { ok: true, headers: { etag: '"v1"' }, text: async () => JSON.stringify({
        project: 'P-001', total: 1, done: 1, progress: 100, etag: 'v1',
        tasks: [{ id: 'T-1', title: 'x', state: 'DONE', weight: 100 }]
      }) };
      return { ok: false, status: 304, text: async () => '' };
    } },
    { path: '/api/events', handler: () => ({ ok: true, text: async () => JSON.stringify({ nextCursor: 1, events: [] }) }) }
  ]);
  const tm = fakeTimer();
  const c = S.createClient(host, 'P-001', { useSse: false, intervalMs: 2000, jitter: 0 });
  c.state.fetchImpl = f.fn;
  c.state.setTimeoutImpl = tm.setTimeout;
  c.state.clearTimeoutImpl = tm.clearTimeout;
  c.start();
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  assert.equal(c.state.etag, 'v1', '应从响应缓存 ETag');
  tm.flush();      // 触发第二轮
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  const second = f.calls.filter((x) => x.path.startsWith('/api/plan') && x.opts && x.opts.headers && x.opts.headers['If-None-Match']).pop();
  assert.ok(second, '第二轮 /api/plan 请求应带 If-None-Match 头');
  assert.equal(second.opts.headers['If-None-Match'], 'v1', '第二轮应带 If-None-Match');
  assert.equal(host.innerHTML.includes('100%'), true);
  c.stop();
});

test('createClient：接口失败显示「已断线」并按指数退避重连', async () => {
  const host = new El('div');
  const f = fakeFetch([]);   // 全部 404
  const tm = fakeTimer();
  const c = S.createClient(host, 'P-999', { useSse: false, intervalMs: 2000, jitter: 0 });
  c.state.fetchImpl = f.fn;
  c.state.setTimeoutImpl = tm.setTimeout;
  c.state.clearTimeoutImpl = tm.clearTimeout;
  c.start();
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  assert.ok(host.innerHTML.includes('已断线'), '失败应显示已断线');
  assert.ok(host.innerHTML.includes('退避'), '应显示退避信息');
  assert.ok(c.state.attempts >= 1, '重试计数应递增');
  c.stop();
  assert.equal(c.state.closed, true, 'stop 应标记关闭');
});

test('createClient：轮询不整页刷新——只更新指标与行内容', async () => {
  const host = new El('div');
  let state = 'DOING';
  const f = fakeFetch([
    { path: '/api/plan', handler: () => ({ ok: true, text: async () => JSON.stringify({
      project: 'P-001', total: 1, done: state === 'DONE' ? 1 : 0, progress: state === 'DONE' ? 100 : 20,
      tasks: [{ id: 'T-1', title: '任务', state, weight: state === 'DONE' ? 100 : 20, assignee: 'worker-a', verifyCmd: 'grep:a:b' }]
    }) }) },
    { path: '/api/events', handler: () => ({ ok: true, text: async () => JSON.stringify({ nextCursor: 1, events: [] }) }) }
  ]);
  const tm = fakeTimer();
  const c = S.createClient(host, 'P-001', { useSse: false, intervalMs: 2000, jitter: 0 });
  c.state.fetchImpl = f.fn;
  c.state.setTimeoutImpl = tm.setTimeout;
  c.state.clearTimeoutImpl = tm.clearTimeout;
  c.start();
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  const first = host.innerHTML;
  assert.ok(first.includes('20%'));
  state = 'DONE';
  tm.flush();
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  const second = host.innerHTML;
  assert.ok(second.includes('100%'), '状态迁移后进度条更新');
  assert.ok(!second.includes('20%'), '旧进度不再出现');
  assert.equal((second.match(/data-row="T-1"/g) || []).length, 1, '任务行被就地更新而非重建');
  c.stop();
});

/* ---------------- 10. SSE 通道与回退 ---------------- */

test('createClient：EventSource 可用时优先 SSE，断线回退轮询', async () => {
  const host = new El('div');
  const f = fakeFetch([{ path: '/api/plan', handler: () => ({ ok: true, text: async () => JSON.stringify({
    project: 'P-001', total: 1, done: 0, progress: 0, tasks: [{ id: 'T-1', title: 'x', state: 'DRAFT', weight: 0 }]
  }) }) }]);
  const tm = fakeTimer();
  const esHandlers = {};
  const fakeES = function (url) {
    this.url = url;
    this.closed = false;
    this.addEventListener = (t, fn) => { esHandlers[t] = fn; };
    this.close = () => { this.closed = true; };
  };
  const c = S.createClient(host, 'P-001', { useSse: true, intervalMs: 2000, jitter: 0, ssePath: '/api/stream' });
  c.state.fetchImpl = f.fn;
  c.state.setTimeoutImpl = tm.setTimeout;
  c.state.clearTimeoutImpl = tm.clearTimeout;
  c.state.EventSourceImpl = fakeES;
  c.start();
  assert.ok(f.calls.length === 0, 'SSE 路径下不应立即发起轮询');
  esHandlers.message({ data: JSON.stringify({ plan: { project: 'P-001', total: 1, done: 1, progress: 100, tasks: [{ id: 'T-1', title: 'x', state: 'DONE', weight: 100 }] } }) });
  assert.ok(host.innerHTML.includes('100%'), 'SSE 帧应驱动渲染');
  assert.equal(c.state.status, 'online', 'SSE 数据到达应为 online');
  esHandlers.error();
  assert.equal(c.state.sse, null, 'SSE 断开应释放实例');
  assert.equal(c.state.status, 'offline', 'SSE 断开应标记已断线');
  assert.ok(tm.queue.length >= 1, 'SSE 断开后应排程轮询兜底');
  c.stop();
});

test('createClient：EventSource 不存在或抛错时直接走轮询', async () => {
  const host = new El('div');
  const f = fakeFetch([{ path: '/api/plan', handler: () => ({ ok: true, text: async () => JSON.stringify({
    project: 'P-001', total: 0, done: 0, progress: 0, tasks: []
  }) }) }, { path: '/api/events', handler: () => ({ ok: true, text: async () => JSON.stringify({ events: [] }) }) }]);
  const tm = fakeTimer();
  const bad = function () { throw new Error('EventSource not available'); };
  const c = S.createClient(host, 'P-001', { useSse: true, intervalMs: 2000, jitter: 0 });
  c.state.fetchImpl = f.fn;
  c.state.setTimeoutImpl = tm.setTimeout;
  c.state.clearTimeoutImpl = tm.clearTimeout;
  c.state.EventSourceImpl = bad;
  c.start();
  assert.ok(tm.queue.length >= 1, '构造抛错应回退轮询并排程');
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  assert.ok(f.calls.some((x) => x.path.startsWith('/api/plan')), '应回退到轮询');
  c.stop();
});

/* ---------------- 11. 装载器：无需修改后端函数即可启用 ---------------- */

test('boot：自动发现 .plan 区块并按 data-pid 启动，跳过无 data-pid 区块', () => {
  const tm = fakeTimer();
  const seen = [];
  S.setBootFactory(function (host, pid) {
    seen.push({ pid, marked: host.getAttribute('data-sync-bound') });
    return {
      start: () => tm.setTimeout(() => { }, 2000),
      stop: () => { },
      state: {}
    };
  });
  const root = new El('div');
  const p1 = new El('section'); p1.attrs.class = 'plan'; p1.attrs['data-pid'] = 'P-001';
  const p2 = new El('section'); p2.attrs.class = 'plan';                 // 无 data-pid，应跳过
  const p3 = new El('section'); p3.attrs.class = 'plan';
  const inner = new El('div'); inner.attrs['data-pid'] = 'P-003';        // 嵌套发现
  p3.appendChild(inner);
  root.appendChild(p1); root.appendChild(p2); root.appendChild(p3);

  const started = S.boot(root);
  assert.equal(started.length, 2, '应绑定 2 个可识别区块（P-001 与 P-003 嵌套发现），跳过 P-002');
  assert.deepEqual(seen.map((x) => x.pid), ['P-001', 'P-003']);
  assert.equal(p1.getAttribute('data-sync-bound'), '1', '绑定后打标记');
  assert.equal(p2.getAttribute('data-sync-bound'), null, '无 data-pid 的区块不得被绑定');
  assert.equal(p3.getAttribute('data-sync-bound'), '1');

  // 已绑定的区块不应重复启动（防刷新时重复建定时器）
  assert.equal(S.boot(root).length, 0, '二次 boot 不得重复绑定');
  S.setBootFactory(null);
});

test('启动钩子不依赖 document（无 DOM 环境下安全）', () => {
  S.setBootFactory(null);
  assert.equal(S.boot(null).length, 0, 'rootEl 为 null 时应返回空数组');
  assert.equal(S.start({ querySelectorAll: () => [] }).length, 0);
});
