/*
 * FleetPlanSync — /projects 页面计划同步客户端（fe-2 · W2）
 * =============================================================
 * 目标：计划/任务状态变化后不依赖整页刷新，实时刷新
 *   · 整体完成百分比 / 已完成 / 总数 / 剩余数 / 整体进度条
 *   · 每个任务条（进度条 + 展开详情）
 *   · 同步状态：「同步中 / 已断线 / 最后更新时间」
 *
 * 传输策略：优先 SSE（EventSource /api/stream），断线指数退避重连；
 *   任一通道失败即回退到 2 秒增量轮询 GET /api/plan + GET /api/events
 *   （轮询用 If-None-Match 带 ETag 比对，无变化时服务端 304 → 不渲染）。
 *
 * 后端契约（W1 提供；上线前 404 属预期，客户端按「已断线 + 退避」处理，不中断页面）：
 *   GET  /api/plan?project=<pid>          -> 见 normalizePlan 的兼容形状
 *   GET  /api/events?project=<pid>&since=<n>&limit=<n>
 *                                            -> {nextCursor, events:[...]} 或 [...]
 *   GET  /api/stream?project=<pid>        -> text/event-stream（可选）
 *   POST /api/plan   {project, task}      -> {ok, task, error}
 *   POST /api/tasks/<id> {title, detail, verify_cmd, assignee, reviewer, order}
 *                                                                -> {ok, task, error}
 *
 * 安全边界：客户端只做展示与字段编辑请求；state / project / id 一律不进表单，
 *   由后端做状态机、目录白名单、危险命令黑名单、角色权限与 audit。
 *
 * 零依赖：纯标准库级别 DOM API，不引任何 CDN。可在无 window 的 Node 环境装载
 *   （供 node:test 隔离测试）。
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    var ns = factory();
    if (typeof root !== 'undefined') {
      root.FleetPlanSync = ns;
    }
  }
})(typeof self !== 'undefined' ? self : typeof window !== 'undefined' ? window : null, function () {

  'use strict';

  var DEFAULTS = {
    intervalMs: 2000,          // 增量轮询间隔（需求：2 秒）
    jitter: 0.15,              // 抖动比例，避免多标签页同拍
    maxBackoffMs: 30000,       // 退避上限
    initialBackoffMs: 1000,
    eventLimit: 200,           // 单轮拉取的事件上限
    useSse: true,              // 是否尝试 EventSource（不支持/失败即回退轮询）
    ssePath: '/api/stream',
    planPath: '/api/plan',
    eventsPath: '/api/events'
  };

  var PILL_CLASS = {
    DONE: 'p-ok', PASS: 'p-ok',
    DOING: 'p-info', ASSIGNED: 'p-info', REVIEWING: 'p-info', SUBMITTED: 'p-info', DRAFT: 'p-info',
    REWORK: 'p-warn', PARTIAL: 'p-warn',
    BLOCKED: 'p-bad', FAILED: 'p-bad', offline: 'p-bad'
  };

  var STATE_WEIGHT = {
    DONE: 1.0, PARTIAL: 0.7, REVIEWING: 0.5, SUBMITTED: 0.4,
    DOING: 0.2, REWORK: 0.15, BLOCKED: 0.1, DRAFT: 0, ASSIGNED: 0, FAILED: 0
  };

  var MAX_FORM_LEN = 8192;
  var MAX_CMD_LEN = 1024;
  var TITLE_REQUIRED_MSG = '标题不能为空';
  var CMD_REQUIRED_MSG = '验收命令不能为空';

  /* ---------------- 通用小工具 ---------------- */

  function pick(obj, keys) {
    // 注意：数值 0 是合法值（如 progress:0、weight:0），不可按 falsy 丢弃。
    if (!obj || typeof obj !== 'object') return undefined;
    for (var i = 0; i < keys.length; i++) {
      var v = obj[keys[i]];
      if (v === undefined || v === null || v === '') continue;
      // assignee/reviewer 可能是 {id, duty} 之类对象：取 id 或 name，避免返回 [object Object]
      if (typeof v === 'object' && (v.id !== undefined || v.name !== undefined)) {
        return v.id !== undefined ? v.id : v.name;
      }
      return v;
    }
    return undefined;
  }

  function toNum(v, fallback) {
    var n = typeof v === 'number' ? v : parseFloat(v);
    if (n === null || n === undefined || !isFinite(n)) return fallback;
    return n;
  }

  function toInt(v, fallback) {
    var n = toNum(v, NaN);
    if (!isFinite(n)) return fallback;
    return Math.round(n);
  }

  function pct(v) {
    var n = toNum(v, 0);
    if (n < 0) n = 0;
    if (n > 1) n = n / 100;      // 0..1 小数归一到百分数
    return Math.min(100, Math.max(0, Math.round(n * 100)));
  }

  function esc(v) {
    var s = v === undefined || v === null ? '' : String(v);
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function pillClass(state) {
    return PILL_CLASS[state] || 'p-info';
  }

  function pillHtml(state) {
    return '<span class="pill ' + pillClass(state) + '"><i></i>' + esc(state || '—') + '</span>';
  }

  function dash(v) {
    return v === undefined || v === null || v === '' ? '—' : v;
  }

  function hhmmss(d) {
    if (d === null || d === undefined) return '—';
    d = d instanceof Date ? d : new Date(d);
    if (!(d instanceof Date) || isNaN(d.getTime())) return '—';
    function p(n) { return (n < 10 ? '0' : '') + n; }
    return p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }

  /* ---------------- 契约归一化（兼容 W1 多种字段命名） ---------------- */

  // 解数据信封：返回真正承载 tasks/total 的那一层。
  // 顶层已有任务数组 → 原样返回；否则按候选键逐个下探（限一层，避免误拆）。
  var ENVELOPE_KEYS = ['plan', 'data', 'result', 'payload', 'body'];

  function unwrapEnvelope(src) {
    if (!src || typeof src !== 'object') return {};
    var hasTasks = Array.isArray(src.tasks) || Array.isArray(src.plan_items) || Array.isArray(src.items);
    if (hasTasks) return src;
    for (var i = 0; i < ENVELOPE_KEYS.length; i++) {
      var v = src[ENVELOPE_KEYS[i]];
      if (v && typeof v === 'object' && !Array.isArray(v) &&
          (Array.isArray(v.tasks) || Array.isArray(v.plan_items) || Array.isArray(v.items) ||
           v.total !== undefined || v.done !== undefined || v.progress !== undefined)) {
        return v;
      }
    }
    return src;
  }

  // normalizePlan(raw) -> {project, name, total, done, remaining, progress, tasks:[], etag}
  function normalizePlan(raw) {
    var src = raw || {};
    // 数据信封兼容：{plan:{...}} / {data:{...}} / {result:{...}} / {payload:{...}}
    // 规则：顶层已有任务数组则直接用；否则若某个信封键下带任务数组则取该层。
    // 避免把 {project:{id,name}, total, tasks} 之类「顶层即数据」的形状误拆。
    src = unwrapEnvelope(src);

    var tasksRaw = Array.isArray(src.tasks) ? src.tasks
      : (Array.isArray(src.plan_items) ? src.plan_items
        : (Array.isArray(src.items) ? src.items : []));

    var total = pick(src, ['total', 'task_total', 'count']);
    var tasks = tasksRaw.map(normalizeTask);
    if (total === undefined) total = tasks.length;

    var done = pick(src, ['done', 'completed', 'finished', 'done_count']);
    if (done === undefined) {
      done = tasks.reduce(function (n, t) { return n + (t.state === 'DONE' || t.state === 'PARTIAL' ? 1 : 0); }, 0);
    }
    total = toInt(total, tasks.length);
    // 显式 done 不做钳制：快照里的 completed 是权威口径（任务被移除后计数仍可能更大）；
    // 仅 remaining 兜底非负。
    done = toInt(done, 0);
    var remaining = (src.remaining !== undefined ? toInt(src.remaining, 0) : Math.max(0, total - done));

    var progress = pick(src, ['progress', 'progress_pct', 'percent', 'completion']);
    if (progress === undefined) {
      progress = total ? Math.round(tasks.reduce(function (s, t) { return s + t.weight; }, 0) / total) : 0;
    }
    // progress 可能是百分数(0..100)也可能是小数(0..1)，统一按 pct 归一；
    // 不能直接用 toInt，否则 0.4(40%) 会被四舍五入成 0。
    progress = pct(progress);

    return {
      project: pick(src, ['project', 'pid', 'projectId', 'project_id']) || '',
      name: pick(src, ['name', 'project_name', 'title']) || '',
      total: total,
      done: done,
      remaining: remaining,
      progress: progress,
      tasks: tasks,
      etag: src.etag || src.ETag || src.etags || (src.cache && src.cache.etag) || null
    };
  }

  // normalizeTask(raw) -> {id,title,state,weight,detail,assignee,reviewer,verifyCmd,reworkCount,note,url,order,after}
  function normalizeTask(raw) {
    var t = raw || {};
    var id = String(pick(t, ['id', 'taskId', 'task_id']) || '');
    var state = String(pick(t, ['state', 'status', 'taskState']) || 'DRAFT').toUpperCase();
    var title = pick(t, ['title', 'name', 'summary']) || '未命名任务';
    var assignee = pick(t, ['assignee', 'executor', 'owner', 'actor'])
      || (t.assignee && t.assignee.id) || (t.assignee && t.assignee.name) || '';
    var reviewer = pick(t, ['reviewer', 'reviewer_id', 'qareviewer'])
      || (t.reviewer && t.reviewer.id) || (t.reviewer && t.reviewer.name) || '';
    var verifyCmd = pick(t, ['verify_cmd', 'verifyCmd', 'verification', 'verify']);
    var rework = toInt(pick(t, ['rework_count', 'reworkCount', 'rework']), 0);

    var url = t.url || (id ? '/tasks/' + encodeURIComponent(id) : '');
    var weight = pct(pick(t, ['weight', 'percent', 'pct', 'progress']));
    if (weight === 0 && state) weight = Math.round((STATE_WEIGHT[state] || 0) * 100);

    return {
      id: id,
      title: title,
      state: state,
      weight: weight,
      detail: pick(t, ['detail', 'detail_note', 'goal', 'objective']) || '',
      assignee: String(assignee),
      reviewer: String(reviewer),
      verifyCmd: verifyCmd || '',
      reworkCount: rework,
      note: pick(t, ['state_note', 'stateNote', 'note', 'description']) || '',
      url: url,
      order: pick(t, ['order', 'seq', 'index', 'sort']),
      after: Array.isArray(t.after) ? t.after.slice() : []
    };
  }

  /* ---------------- 事件解析 ---------------- */

  // parseEvents(raw) -> {events:[...], nextCursor:Number|null}
  function parseEvents(raw) {
    var list = Array.isArray(raw) ? raw : (raw && raw.events) || (raw && raw.items) || [];
    if (!Array.isArray(list)) list = [];
    var nextCursor = (raw && (raw.nextCursor !== undefined ? raw.nextCursor
      : raw.next_cursor !== undefined ? raw.next_cursor
        : raw.cursor !== undefined ? raw.cursor
          : raw.since !== undefined ? raw.since : null));
    return { events: list.map(normalizeEvent), nextCursor: toInt(nextCursor, null) };
  }

  function normalizeEvent(raw) {
    var e = raw || {};
    var actor = pick(e, ['actor', 'user', 'who']) || 'console';
    var action = String(pick(e, ['action', 'event', 'type']) || '');
    var from = e.from !== undefined ? e.from : e.from_state;
    var to = e.to !== undefined ? e.to : e.to_state;
    var taskId = pick(e, ['taskId', 'task_id', 'task', 'id']) || '';
    var assignee = pick(e, ['assignee', 'executor']) || '';
    var reviewer = pick(e, ['reviewer']) || '';
    var detail = pick(e, ['detail', 'summary', 'message', 'note']) || '';
    var summary = pick(e, ['summary']) || (detail
      ? (actor + ' · ' + action + (taskId ? ' ' + taskId : '') + '：' + detail)
      : (actor + ' · ' + action + (taskId ? ' ' + taskId : '') + (from || to ? '（' + dash(from) + ' → ' + dash(to) + '）' : '')));
    var url = e.url || (taskId ? '/tasks/' + encodeURIComponent(taskId) : '');
    return {
      seq: toInt(e.seq, toInt(e.index, toInt(e.cursor, null))),
      timestamp: pick(e, ['timestamp', 'ts', 'time', 'created_at']) || '',
      actor: String(actor),
      action: action,
      taskId: String(taskId),
      from: from || '',
      to: to || '',
      assignee: String(assignee),
      reviewer: String(reviewer),
      detail: detail,
      summary: summary,
      url: url
    };
  }

  /* ---------------- 退避重连 ---------------- */

  // 指数退避：1s → 2s → 4s … 上限 max；每次抖动 ±jitter
  function backoffMs(attempt, o) {
    var d = o || DEFAULTS;
    var base = Math.min(d.maxBackoffMs, d.initialBackoffMs * Math.pow(2, attempt));
    var j = (Math.random() * 2 - 1) * d.jitter * base;
    return Math.max(50, Math.round(base + j));
  }

  /* ---------------- 渲染：局部更新，不重建 DOM ---------------- */

  function barHtml(width) {
    return '<div class="bar"><i style="width:' + width + '%"></i></div>';
  }

  function rowDetailHtml(t) {
    return (
      barHtml(t.weight) +
      '<p><b>执行者：</b>' + esc(dash(t.assignee)) + '　<b>审查者：</b>' + esc(dash(t.reviewer)) + '</p>' +
      '<p><b>规划目标：</b>' + esc(t.detail || '未填写') + '</p>' +
      '<p><b>验收标准：</b><span class="mono">' + esc(t.verifyCmd || '未填写') + '</span></p>' +
      '<p><b>当前说明：</b>' + esc(t.note || '暂无') + '　<b>返工：</b>' + t.reworkCount + ' 次' +
      '　<b>状态：</b>' + pillHtml(t.state) + '</p>' +
      '<div class="plan-actions">' +
      '<a class="btn mini" href="' + esc(t.url) + '">打开任务详情</a> ' +
      '<button type="button" class="btn mini" data-edit="' + esc(t.id) + '">✎ 编辑计划</button>' +
      '</div>'
    );
  }

  function taskRowHtml(t, open) {
    return '<details class="plan-task" data-row="' + esc(t.id) + '" data-state="' + esc(t.state) + '"' +
      (open ? ' open' : '') + '>' +
      '<summary><span class="plan-state">' + pillHtml(t.state) + '</span>' +
      '<strong>' + esc(t.id) + '</strong> ' + esc(t.title) +
      '<span class="plan-percent">' + t.weight + '%</span></summary>' +
      '<div class="plan-detail">' + rowDetailHtml(t) + '</div></details>';
  }

  function syncLabelHtml(state, lastTs, extra) {
    var cls = state === 'online' ? 'p-ok' : (state === 'syncing' ? 'p-info' : 'p-bad');
    var text = state === 'online' ? '已同步' : (state === 'syncing' ? '同步中' : '已断线');
    var stamp = hhmmss(lastTs);
    return '<span class="pill ' + cls + '"><i></i>' + esc(text) + '</span>' +
      '<span class="sync-meta">最后更新 ' + esc(stamp) + (extra ? '　' + extra : '') + '</span>';
  }

  function metricsSummary(m) {
    return '<div class="metric">' + m.progress + '%</div>' + barHtml(m.progress) +
      '<div class="sub">已完成 <span data-m-done>' + m.done + '</span> / 共 ' +
      '<span data-m-total>' + m.total + '</span> 项，剩余 <span data-m-remaining>' + m.remaining + '</span> 项</div>' +
      '<div class="sub">整体完成百分比：<span data-m-progress>' + m.progress + '%</span></div>';
  }

  // 就地更新已存在的指标节点；缺失节点则整块替换（首次渲染）。
  function renderMetrics(host, m) {
    var bar = host && host.querySelector('[data-m-bar]');
    var el = function (k) { return host && host.querySelector('[data-' + k + ']'); };
    var patch = function (sel, val) {
      var n = host && host.querySelector(sel);
      if (n) n.textContent = val;
    };
    if (!bar) {
      host.innerHTML = '<div class="plan-sync" data-pid="' + esc(m.project) + '">' +
        '<div class="plan-head"><div><h3>整体任务计划</h3>' +
        '<div class="metric" data-m-progress-val>' + m.progress + '%</div>' +
        '<div class="bar" data-m-bar><i style="width:' + m.progress + '%"></i></div>' +
        '<div class="sub">已完成 <span data-m-done>' + m.done + '</span> / 共 ' +
        '<span data-m-total>' + m.total + '</span> 项，剩余 <span data-m-remaining>' + m.remaining + '</span> 项</div>' +
        '<div class="sub">整体完成百分比：<span data-m-progress>' + m.progress + '%</span></div>' +
        '<div class="sync-state" data-sync><span class="sub">尚未同步</span></div>' +
        '</div><div class="plan-summary"></div></div>' +
        '<div class="plan-rows" data-rows></div></div>';
      host.__metricsReady = true;
      return host;
    }
    var fill = bar && bar.querySelector('i');
    if (fill && fill.setAttribute) fill.setAttribute('style', 'width:' + m.progress + '%');
    patch('[data-m-progress-val]', m.progress + '%');
    patch('[data-m-progress]', m.progress + '%');
    patch('[data-m-done]', String(m.done));
    patch('[data-m-total]', String(m.total));
    patch('[data-m-remaining]', String(m.remaining));
    return host;
  }

  // 按 taskId 就地更新任务条：只改既有节点的 DOM，不整体重建 <details>，
  // 因此用户已展开的详情保持展开状态；新增任务追加，消失任务移除。
  function renderRows(container, tasks) {
    if (!container) return container;
    var next = {};
    for (var i = 0; i < tasks.length; i++) {
      var t = tasks[i];
      next[t.id] = t;
      var existing = container.querySelector('[data-row="' + t.id + '"]');
      if (existing) {
        existing.setAttribute('data-state', t.state);
        var pct = existing.querySelector('.plan-percent');
        if (pct) pct.textContent = t.weight + '%';
        var detail = existing.querySelector('.plan-detail');
        if (detail) detail.innerHTML = rowDetailHtml(t);
        var summary = existing.querySelector('summary');
        if (summary) {
          summary.innerHTML = '<span class="plan-state">' + pillHtml(t.state) + '</span>' +
            '<strong>' + esc(t.id) + '</strong> ' + esc(t.title) +
            '<span class="plan-percent">' + t.weight + '%</span>';
        }
      } else {
        var frag = container.ownerDocument
          ? container.ownerDocument.createElement('div')
          : { innerHTML: '' };
        frag.innerHTML = taskRowHtml(t, false);
        var row = frag.children && frag.children[0];
        if (row) container.appendChild(row);
        else {
          // 无文档上下文（测试 stub）：退回整体重建一次，保证行被创建
          rebuildRows(container, tasks);
          container.__last = next;
          return container;
        }
      }
    }
    // 移除本轮已不存在于计划中的任务条（后端不允许删除任务，仅防御）
    var rows = container.querySelectorAll('[data-row]');
    for (var r = 0; r < rows.length; r++) {
      if (!next[rows[r].getAttribute('data-row')]) rows[r].remove();
    }
    if (!container.children.length) {
      container.innerHTML = '<div class="sub">暂无任务计划。</div>';
    }
    container.__last = next;
    return container;
  }

  function rebuildRows(container, tasks) {
    container.innerHTML = tasks.map(function (t) { return taskRowHtml(t, false); }).join('')
      || '<div class="sub">暂无任务计划。</div>';
  }

  function setStatus(host, state, lastTs, extra) {
    if (!host) return;
    var label = syncLabelHtml(state, lastTs, extra);
    var n = host.querySelector('[data-sync]');
    if (n) { n.innerHTML = label; return; }
    // 指标块尚未渲染（首轮请求失败等）：兜底建一个同步状态节点，保证「已断线」可见
    var doc = host.ownerDocument || (typeof document !== 'undefined' ? document : null);
    if (doc && doc.createElement) {
      n = doc.createElement('div');
      n.className = 'sync-state';
      n.setAttribute('data-sync', '');
      host.appendChild(n);
      n.innerHTML = label;
    } else if (typeof host.innerHTML === 'string') {
      host.innerHTML = host.innerHTML + '<div class="sync-state" data-sync>' + label + '</div>';
    }
  }

  function setToast(host, html) {
    var n = host && host.querySelector('[data-toast]');
    if (n) n.innerHTML = html;
  }

  /* ---------------- 装载器：后端最小注入点 ---------------- */

  // 测试接缝：默认使用真实 createClient；node:test 可替换为注入版以便控制定时器/网络。
  var createClientForBoot = null;

  // 后端只需在 /projects 页面 body 里加一行 <script src="/static/js/plan-sync-client.js">
  // 即可自动发现 .plan 区块并启动同步；不改动后端任何函数。
  // 区块需带 data-pid（后端 project_plan 已输出）；无 data-pid 的区块跳过，不猜测项目。
  function boot(rootEl) {
    var doc = rootEl || (typeof document !== 'undefined' ? document : null);
    if (!doc || !doc.querySelectorAll) return [];
    var plans = doc.querySelectorAll('.plan:not([data-sync-bound])');
    var started = [];
    var ctor = createClientForBoot || createClient;
    for (var i = 0; i < plans.length; i++) {
      var sec = plans[i];
      var pid = sec.getAttribute('data-pid') || '';
      if (!pid) {
        var link = sec.querySelector('[data-pid]');
        pid = link ? link.getAttribute('data-pid') : '';
      }
      if (!pid) continue;
      sec.setAttribute('data-sync-bound', '1');
      var client = ctor(sec, pid);
      client.start();
      started.push(client);
    }
    return started;
  }

  /* ---------------- 编辑计划表单 ---------------- */

  function fieldRow(label, key, value, max, placeholder, mono) {
    return '<div class="field"><label for="plan-f-' + key + '">' + label + '</label>' +
      '<input id="plan-f-' + key + '" data-field="' + key + '" maxlength="' + max + '" class="' +
      (mono ? 'mono' : '') + '" value="' + esc(value == null ? '' : value) + '" placeholder="' +
      esc(placeholder || '') + '"></div>';
  }

  function buildForm(t, extra) {
    extra = extra || {};
    var assignees = Array.isArray(extra.assignees) ? extra.assignees : [];
    var reviewers = Array.isArray(extra.reviewers) ? extra.reviewers : [];
    var asels = assignees.length
      ? assignees.map(function (r) {
          var rid = String(r.id || r);
          return '<option value="' + esc(rid) + '"' + (rid === t.assignee ? ' selected' : '') + '>' +
            esc(rid + ' · ' + (r.duty || '')) + '</option>';
        }).join('')
      : '<option' + (t.assignee ? '' : ' selected') + ' value="">—不变—</option>';
    if (assignees.length && !assignees.some(function (r) { return String(r.id || r) === t.assignee; })) {
      asels += '<option value="' + esc(t.assignee) + '" selected>' + esc(t.assignee) + '</option>';
    }
    var rsels = reviewers.length
      ? reviewers.map(function (r) {
          var rid = String(r.id || r);
          return '<option value="' + esc(rid) + '"' + (rid === t.reviewer ? ' selected' : '') + '>' +
            esc(rid + ' · ' + (r.duty || '')) + '</option>';
        }).join('')
      : '<option selected value="">—不变—</option>';
    if (reviewers.length && !reviewers.some(function (r) { return String(r.id || r) === t.reviewer; })) {
      rsels += '<option value="' + esc(t.reviewer) + '" selected>' + esc(t.reviewer) + '</option>';
    }
    return '<form data-form="plan-edit" data-task-id="' + esc(t.id) + '">' +
      '<div class="field"><label>任务编号（只读）</label>' +
      '<input value="' + esc(t.id) + '" readonly tabindex="-1" style="opacity:.6"></div>' +
      '<div class="field"><label>当前状态（只读）</label>' + pillHtml(t.state) +
      '<span class="sub">状态由后端状态机迁移，此处不可修改。</span></div>' +
      fieldRow('标题', 'title', t.title, MAX_FORM_LEN, '如：实现登录页', false) +
      fieldRow('规划目标 / 详情', 'detail', t.detail, MAX_FORM_LEN, '目标与约束', false) +
      '<div class="field"><label>验收标准 verify_cmd</label>' +
      '<input id="plan-f-verify_cmd" data-field="verify_cmd" maxlength="' + MAX_CMD_LEN + '" class="mono" ' +
      'value="' + esc(t.verifyCmd) + '" placeholder="grep:相对路径:令牌1,令牌2"></div>' +
      '<div class="field"><label>执行者</label><select id="plan-f-assignee" data-field="assignee">' + asels + '</select></div>' +
      '<div class="field"><label>审查者</label><select id="plan-f-reviewer" data-field="reviewer">' + rsels + '</select></div>' +
      fieldRow('排序（可空）', 'order', t.order == null ? '' : t.order, 8, '留空=不调整顺序', false) +
      fieldRow('前置依赖 after（逗号分隔任务ID，可空）', 'after',
        Array.isArray(t.after) ? t.after.join(',') : (t.after == null ? '' : String(t.after)), 200, '如 T-001,T-002；留空=无前置', true) +
      '<div class="form-actions"><button class="btn primary" type="submit">💾 保存计划</button> ' +
      '<button class="btn" type="button" data-cancel>取消</button></div>' +
      '<p class="sub" data-form-note>仅提交变更字段；后端会做角色权限、目录白名单与危险命令黑名单校验。</p>' +
      '<div data-form-msg></div>' +
      '</form>';
  }

  // 客户端字段级校验（后端仍会独立复校；这里只做即时反馈）。
  function validateForm(form) {
    var v = readForm(form);
    if (!v.title.trim()) return { ok: false, error: TITLE_REQUIRED_MSG };
    if (!v.verify_cmd.trim()) return { ok: false, error: CMD_REQUIRED_MSG };
    if (v.title.length > MAX_FORM_LEN) return { ok: false, error: '标题超过 ' + MAX_FORM_LEN + ' 字符上限' };
    if (v.detail && v.detail.length > MAX_FORM_LEN) return { ok: false, error: '详情超过 ' + MAX_FORM_LEN + ' 字符上限' };
    if (v.verify_cmd.length > MAX_CMD_LEN) return { ok: false, error: '验收命令超过 ' + MAX_CMD_LEN + ' 字符上限' };
    return { ok: true, payload: v };
  }

  function readForm(form) {
    var out = {};
    var nodes = form.querySelectorAll('[data-field]');
    for (var i = 0; i < nodes.length; i++) {
      out[nodes[i].getAttribute('data-field')] = nodes[i].value;
    }
    // 计划表单的 after（前置依赖）：字符串→逗号分隔，后端归一为数组。
    var afterRaw = out.after;
    if (afterRaw !== undefined && Array.isArray(afterRaw)) {
      out.after = afterRaw.join(',');
    }
    return out;
  }

  function openEditor(host, taskId, extra) {
    var wrap = host.querySelector('[data-editor]') || host;
    var t = (host.__plan && host.__plan.tasks.filter(function (x) { return x.id === taskId; })[0]) ||
            ((host.__plan && host.__plan.tasks[0]) || { id: taskId, title: '', state: '', weight: 0 });
    wrap.innerHTML = '<div class="plan-edit card">' + buildForm(t, extra) + '</div>';
    var form = wrap.querySelector('[data-form]');
    if (!form) return null;
    form.__task = t;

    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      var r = validateForm(form);
      var msg = form.querySelector('[data-form-msg]');
      if (!r.ok) {
        msg.innerHTML = '<span class="pill p-bad"><i></i>❌ ' + esc(r.error) + '</span>';
        return;
      }
      host.__submit(r.payload, form);
    });
    var cancel = form.querySelector('[data-cancel]');
    if (cancel) cancel.addEventListener('click', function () { closeEditor(host); });
    return form;
  }

  function closeEditor(host) {
    var wrap = host.querySelector('[data-editor]') || host;
    if (wrap) wrap.innerHTML = '<p class="sub">编辑完成，可在下方大纲中展开任务继续修改。</p>';
    setToast(host, '');
  }

  /* ---------------- 客户端主体 ---------------- */

  function createClient(host, pid, opts) {
    var o = {};
    for (var k in DEFAULTS) o[k] = DEFAULTS[k];
    if (opts) for (var k2 in opts) o[k2] = opts[k2];

    var s = {
      host: host, pid: pid, options: o,
      plan: null, etag: null, cursor: 0,
      status: 'syncing', lastTs: null, backoff: 0, attempts: 0,
      timer: null, sse: null, closed: false,
      events: [],
      fetchImpl: null, setTimeoutImpl: null, clearTimeoutImpl: null,
      EventSourceImpl: null, submitImpl: null,
      assignees: [], reviewers: []
    };

    // 定时器在调用时惰性解析：测试在 createClient 之后注入 setTimeoutImpl
    // 也必须生效；否则真实 setTimeout 驱动的轮询会在失败路径上无限自排程，
    // 使 node --test 永不退出（曾经真实的 2s 定时器泄漏成死循环）。
    function schedule(ms) {
      var impl = s.setTimeoutImpl || (typeof setTimeout !== 'undefined' ? setTimeout : null);
      var clr = s.clearTimeoutImpl || (typeof clearTimeout !== 'undefined' ? clearTimeout : null);
      if (clr && s.timer !== null && s.timer !== undefined) clr(s.timer);
      var h = null;
      if (impl) h = impl(function () { if (!s.closed) tick(); }, ms);
      s.timer = h;
    }

    function interval() {
      var ms = o.intervalMs;
      if (o.jitter) ms += Math.round((Math.random() * 2 - 1) * o.jitter * ms);
      return Math.max(250, Math.round(ms));
    }

    function paintStatus(state, extra) {
      if (state !== s.status || extra) s.status = state;
      setStatus(host, state, s.lastTs, extra);
    }

    function markOk() {
      s.lastTs = new Date();
      if (s.attempts > 0) { s.attempts = 0; s.backoff = 0; }
      paintStatus('online', '');
    }

    function markDown(extra) {
      s.attempts += 1;
      s.backoff = backoffMs(s.attempts - 1, o);
      paintStatus('offline', '第 ' + s.attempts + ' 次重试 · 退避 ' + Math.round(s.backoff / 1000) + 's' +
        (extra ? ' · ' + extra : ''));
    }

    function getJson(path, headers, cb) {
      var fn = s.fetchImpl || fetch;
      if (typeof fn !== 'function') return cb(new Error('fetch 不可用'), null);
      fn(path, { method: 'GET', credentials: 'same-origin', headers: headers || {} })
        .then(function (resp) {
          if (resp.status === 304) return cb(null, { notModified: true });
          if (!resp.ok) return cb(new Error('HTTP ' + resp.status), null);
          return resp.text().then(function (txt) {
            if (headers && headers.Accept && headers.Accept.indexOf('text/event-stream') >= 0) return cb(null, { raw: txt });
            try { return cb(null, JSON.parse(txt)); }
            catch (e) { return cb(new Error('响应不是合法 JSON'), null); }
          });
        })
        .catch(function (e) { cb(e, null); });
    }

    function applyPlan(plan) {
      if (!plan) return;
      s.plan = plan;
      host.__plan = plan;
      if (plan.etag) s.etag = plan.etag;
      renderMetrics(host, plan);
      renderRows(host.querySelector('[data-rows]') || host, plan.tasks);
      bindEditButtons(host);
      host.__lastSync = s.lastTs;
    }

    // 计划行「编辑计划」按钮接线：后端渲染的行（无 data-row 时按任务 id 锚点）
    // 与前端局部渲染的行统一走 openEditor；只允许已有行触发，不自造任务。
    function bindEditButtons(root) {
      if (!root || typeof root.querySelectorAll !== 'function') return;
      var btns;
      try { btns = root.querySelectorAll('[data-edit]'); } catch (e) { return; }
      if (!btns || !btns.length) return;
      for (var i = 0; i < btns.length; i++) {
        (function (btn) {
          if (!btn || btn.__boundEdit || typeof btn.getAttribute !== 'function' ||
              typeof btn.addEventListener !== 'function') return;
          btn.__boundEdit = true;
          var tid = btn.getAttribute('data-edit');
          if (!tid) return;
          btn.addEventListener('click', function (ev) {
            if (ev && typeof ev.preventDefault === 'function') ev.preventDefault();
            try {
              openEditor(host, tid, { assignees: s.assignees, reviewers: s.reviewers });
            } catch (e) { /* 编辑器异常不阻断轮询 */ }
          });
        })(btns[i]);
      }
    }

    // 保存计划：只提交变更字段到 /tasks/<id>/plan（x-www-form-urlencoded）；
    // 后端做状态机/角色权限/白名单/黑名单复校，客户端只做成功刷新与失败展示。
    function submitPlan(taskId, payload, form) {
      var msg = form && form.querySelector ? form.querySelector('[data-form-msg]') : null;
      var fail = function (text) {
        if (msg) msg.innerHTML = '<span class="pill p-bad"><i></i>❌ ' + esc(text) + '</span>';
      };
      var done = function (respText) {
        var ok = /已更新|成功|ok/i.test(String(respText || ''));
        if (ok) { closeEditor(host); tickPlan(); }
        else fail('保存失败：' + String(respText || '').replace(/<[^>]*>/g, '').slice(0, 200));
      };
      var transport = s.submitImpl || s.fetchImpl ||
        (typeof fetch !== 'undefined' ? fetch : null);
      if (typeof transport !== 'function') { fail('提交通道不可用'); return; }
      var body = 'actor=' + encodeURIComponent('web-edit');
      for (var k in payload) {
        if (payload[k] === undefined || payload[k] === null || payload[k] === '') continue;
        body += '&' + encodeURIComponent(k) + '=' + encodeURIComponent(String(payload[k]));
      }
      try {
        var r = transport('/tasks/' + encodeURIComponent(taskId) + '/plan',
          { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: body, credentials: 'same-origin' });
        if (r && typeof r.then === 'function') {
          r.then(function (resp) {
            if (resp && typeof resp.text === 'function') return resp.text().then(done);
            done(String((resp && resp.body) || 'ok'));
          }).catch(function (e) { fail(e && e.message ? e.message : String(e)); });
        } else done('ok');
      } catch (e) { fail(e && e.message ? e.message : String(e)); }
    }

    host.__submit = function (payload, form) {
      var tid = (form && form.__task && form.__task.id) ||
                (form && form.getAttribute && form.getAttribute('data-task-id')) || '';
      submitPlan(tid, payload, form);
    };

    function onEventList(list) {
      if (!Array.isArray(list) || !list.length) return;
      var rowsHost = host.querySelector('[data-rows]') || host;
      for (var i = 0; i < list.length; i++) {
        var e = list[i];
        if (e.seq !== null && e.seq !== undefined && e.seq <= s.cursor) continue;
        if (e.seq !== null && e.seq !== undefined) s.cursor = Math.max(s.cursor, e.seq);
        if (e.taskId) {
          var t = rowsHost.querySelector('[data-row="' + e.taskId + '"]');
          if (t && (e.from || e.to)) t.dataset.state = e.to || e.from;
        }
      }
      host.__events = (host.__events || []).concat(list).slice(-o.eventLimit);
    }

    function tickPlan() {
      var headers = { Accept: 'application/json' };
      if (s.etag) { headers['If-None-Match'] = s.etag; headers['If-Modified-Since'] = new Date().toUTCString(); }
      getJson(o.planPath + '?project=' + encodeURIComponent(s.pid), headers, function (err, data) {
        if (err) return markDown(err.message);
        if (!data || data.notModified) { markOk(); return; }
        var plan = normalizePlan(data);
        applyPlan(plan);
        markOk();
      });
    }

    function tickEvents() {
      getJson(o.eventsPath + '?project=' + encodeURIComponent(s.pid) +
        '&since=' + encodeURIComponent(s.cursor) + '&limit=' + o.eventLimit,
        { Accept: 'application/json' }, function (err, data) {
          if (err) return markDown(err.message);
          if (!data) return;
          var r = parseEvents(data);
          onEventList(r.events);
          if (r.nextCursor !== null && r.nextCursor !== undefined) s.cursor = Math.max(s.cursor, r.nextCursor);
          markOk();
        });
    }

    function tick() {
      paintStatus('syncing');
      tickPlan();
      tickEvents();
      schedule(interval());
    }

    function startSse() {
      if (!o.useSse) return false;
      var Ctor = s.EventSourceImpl || (typeof EventSource !== 'undefined' ? EventSource : null);
      if (typeof Ctor !== 'function') return false;
      var es = null;
      try {
        es = new Ctor(o.ssePath + '?project=' + encodeURIComponent(s.pid));
      } catch (e) { return false; }
      s.sse = es;
      es.addEventListener('open', function () { s.attempts = 0; markOk(); });
      es.addEventListener('message', function (ev) {
        var d = ev && ev.data;
        if (!d) return;
        try {
          var obj = JSON.parse(d);
          if (obj.plan) applyPlan(normalizePlan(obj.plan));
          else if (obj.events || Array.isArray(obj)) {
            var r = parseEvents(obj);
            onEventList(r.events);
            if (r.nextCursor !== null && r.nextCursor !== undefined) s.cursor = Math.max(s.cursor, r.nextCursor);
          } else {
            applyPlan(normalizePlan(obj));
          }
          markOk();
        } catch (e) { /* 非 JSON 帧忽略 */ }
      });
      es.addEventListener('error', function () {
        try { es.close(); } catch (e) { }
        s.sse = null;
        markDown('SSE 断线，改用 ' + (o.intervalMs / 1000) + 's 轮询');
        schedule(o.intervalMs);
      });
      return true;
    }

    return {
      start: function () {
        if (s.closed) return s;
        paintStatus('syncing');
        if (startSse()) return s;      // SSE 成功后由 error 事件回退轮询
        // 先排程再执行，保证 start() 返回时已有一个待触发的轮询，
        // 避免调用方在「排程之前」观察到空队列。
        schedule(interval());
        tick();
        return s;
      },
      stop: function () {
        s.closed = true;
        var clr = s.clearTimeoutImpl || (typeof clearTimeout !== 'undefined' ? clearTimeout : null);
        if (clr && s.timer !== null && s.timer !== undefined) clr(s.timer);
        s.timer = null;
        if (s.sse) { try { s.sse.close(); } catch (e) { } s.sse = null; }
        return s;
      },
      get state() { return s; },
      applyPlan: applyPlan,
      _normalize: normalizePlan,
      _normalizeTask: normalizeTask,
      _parseEvents: parseEvents,
      _renderMetrics: function (m) { return renderMetrics(host, m); },
      _renderRows: function (ts) { return renderRows(host.querySelector('[data-rows]') || host, ts); },
      _setStatus: function (st, ts, extra) {
        return setStatus(host, st, ts || s.lastTs, extra || '');
      },
      _backoffMs: function (n) { return backoffMs(n, o); },
      _boot: function (rootEl) { return boot(rootEl); },
      _buildForm: function (t, extra) { return buildForm(t, extra); },
      _validateForm: function (form) { return validateForm(form); },
      _readForm: function (form) { return readForm(form); },
      _openEditor: function (taskId, extra) { return openEditor(host, taskId, extra); },
      _closeEditor: function () { return closeEditor(host); },
      _setToast: function (h) { return setToast(host, h); },
      _syncLabelHtml: syncLabelHtml,
      _metricsSummary: function (m) { return metricsSummary(m); },
      _taskRowHtml: function (t, open) { return taskRowHtml(t, open); },
      _rowDetailHtml: rowDetailHtml
    };
  }

  /* ---------------- 导出（供 Node 测试与页面加载复用） ---------------- */

  return {
    DEFAULTS: DEFAULTS,
    STATE_WEIGHT: STATE_WEIGHT,
    MAX_FORM_LEN: MAX_FORM_LEN,
    MAX_CMD_LEN: MAX_CMD_LEN,
    TITLE_REQUIRED_MSG: TITLE_REQUIRED_MSG,
    CMD_REQUIRED_MSG: CMD_REQUIRED_MSG,
    pick: pick,
    toNum: toNum,
    toInt: toInt,
    pct: pct,
    esc: esc,
    pillClass: pillClass,
    pillHtml: pillHtml,
    hhmmss: hhmmss,
    backoffMs: backoffMs,
    normalizePlan: normalizePlan,
    normalizeTask: normalizeTask,
    parseEvents: parseEvents,
    normalizeEvent: normalizeEvent,
    renderMetrics: renderMetrics,
    renderRows: renderRows,
    setStatus: setStatus,
    syncLabelHtml: syncLabelHtml,
    metricsSummary: metricsSummary,
    taskRowHtml: taskRowHtml,
    rowDetailHtml: rowDetailHtml,
    buildForm: buildForm,
    validateForm: validateForm,
    readForm: readForm,
    boot: boot,
    createClient: createClient,
    // 测试接缝：允许注入 createClient 以便控制定时器/网络（生产恒为 null）
    setBootFactory: function (fn) { createClientForBoot = fn || null; },
    // 页面内便捷入口
    mount: function (host, pid, opts) { return createClient(host, pid, opts).start(); },
    start: function (opts) { return boot(typeof document !== 'undefined' ? document : null); }
  };
});
