/* audio-to-action — interactive demo state machine
 *
 * Drives:
 *   1. Step buttons   ▶ run → spinner → ✓ done, with dependents unlocked
 *   2. Diarization side-step  (synthetic example reveal)
 *   3. A–F choice menu — every option SERVES the user. No refusals.
 *   4. E's draft → confirm → send flow (the only place "拦动作" actually
 *      enforces — sending is irreversible, so we ask twice)
 *
 * Real LLM outputs come from docs/demo_responses.json, captured via
 * `scripts/capture_demo_responses.py` against minimax-m27-gw on a real
 * lab transcript. No pre-canned strings. No framework.
 */

(() => {
  'use strict';

  // ---------- helpers ---------- //

  const sleep = ms => new Promise(r => setTimeout(r, ms));

  /** UI-compressed simulation delays. The "real" wall-clock numbers are surfaced
   *  via the [data-elapsed] indicator inside each step's output. */
  const STEP_DELAYS = {
    probe:     350,
    asr:       1600,
    normalize: 300,
    diarize:   600,
    classify:  1400,
    route:     250,
  };

  let LLM_DATA = null;  // populated from fetch on load

  function realTime(stepId) {
    if (stepId === 'asr') return '实际 wall-clock 898s · 0.83× 实时 · 12 分 29 秒音频（动画压缩到 ~1.6s）';
    if (stepId === 'classify' && LLM_DATA?.classify?.elapsed_s) {
      return `LLM 调用 ${LLM_DATA.classify.elapsed_s}s · model: ${LLM_DATA._meta?.model || '?'} · ${LLM_DATA.classify.usage?.completion_tokens || '?'} comp tokens`;
    }
    return '';
  }

  // ---------- markdown renderer (light, ~50 lines) ---------- //

  function escapeHtml(s) {
    return s
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function inlineFormat(s) {
    s = escapeHtml(s);
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/（推测[^）]*）/g, m => `<span class="warn">${m}</span>`);
    s = s.replace(/（待确认[^）]*）/g, m => `<span class="warn">${m}</span>`);
    s = s.replace(/（占位[^）]*）/g, m => `<span class="warn">${m}</span>`);
    return s;
  }

  function renderMarkdown(md) {
    if (!md) return '';
    const lines = md.replace(/\r\n/g, '\n').split('\n');
    const out = [];
    let inList = false;
    let inBlockquote = false;

    const closeList = () => { if (inList) { out.push('</ul>'); inList = false; } };
    const closeBlockquote = () => { if (inBlockquote) { out.push('</blockquote>'); inBlockquote = false; } };

    for (const raw of lines) {
      const line = raw.replace(/\s+$/, '');

      let m;
      if ((m = line.match(/^####\s+(.*)$/))) {
        closeList(); closeBlockquote();
        out.push(`<h5>${inlineFormat(m[1])}</h5>`);
      } else if ((m = line.match(/^###\s+(.*)$/))) {
        closeList(); closeBlockquote();
        out.push(`<h4>${inlineFormat(m[1])}</h4>`);
      } else if ((m = line.match(/^##\s+(.*)$/))) {
        closeList(); closeBlockquote();
        out.push(`<h3>${inlineFormat(m[1])}</h3>`);
      } else if ((m = line.match(/^#\s+(.*)$/))) {
        closeList(); closeBlockquote();
        out.push(`<h3>${inlineFormat(m[1])}</h3>`);
      } else if ((m = line.match(/^[-*]\s+(.*)$/))) {
        closeBlockquote();
        if (!inList) { out.push('<ul>'); inList = true; }
        out.push(`<li>${inlineFormat(m[1])}</li>`);
      } else if ((m = line.match(/^>\s*(.*)$/))) {
        closeList();
        if (!inBlockquote) { out.push('<blockquote>'); inBlockquote = true; }
        out.push(`<p>${inlineFormat(m[1])}</p>`);
      } else if (/^---+$/.test(line)) {
        closeList(); closeBlockquote();
        out.push('<hr>');
      } else if (line === '') {
        closeList(); closeBlockquote();
      } else {
        closeList(); closeBlockquote();
        out.push(`<p>${inlineFormat(line)}</p>`);
      }
    }
    closeList();
    closeBlockquote();
    return out.join('\n');
  }

  /** Pretty-print + syntax-tint a JSON string. Falls back to raw text. */
  function renderJson(s) {
    try {
      const obj = JSON.parse(s);
      const pretty = JSON.stringify(obj, null, 2);
      return escapeHtml(pretty)
        .replace(/&quot;([^&]+?)&quot;(\s*:)/g, '<span class="k">"$1"</span>$2')
        .replace(/:\s*&quot;([^&]*?)&quot;/g, ': <span class="s">"$1"</span>')
        .replace(/:\s*(-?\d+\.?\d*)/g, ': <span class="n">$1</span>')
        .replace(/:\s*(true|false|null)/g, ': <span class="a">$1</span>');
    } catch (_) {
      return escapeHtml(s);
    }
  }

  // ---------- init: fetch real LLM responses, lock dependent steps ---------- //

  fetch('demo_responses.json')
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => { LLM_DATA = data; })
    .catch(err => { console.warn('demo_responses.json not loaded:', err); });

  document.querySelectorAll('.demo-step[data-requires]').forEach(el => {
    el.classList.add('locked');
  });

  // ---------- click delegation ---------- //

  document.body.addEventListener('click', e => {
    const btn = e.target.closest('[data-action], .choice');
    if (!btn) return;
    if (btn.dataset.action === 'run-step')      runStep(btn);
    else if (btn.dataset.action === 'run-diarize') runDiarize(btn);
    else if (btn.dataset.action === 'send-msg')    openSendConfirm();
    else if (btn.dataset.action === 'confirm-send') confirmSend();
    else if (btn.dataset.action === 'cancel-send') cancelSend();
    else if (btn.classList.contains('choice'))     handleChoice(btn);
  });

  // ---------- main step runner ---------- //

  async function runStep(btn) {
    if (btn.disabled && !btn.classList.contains('done')) return;
    const id = btn.dataset.target;
    const stepEl = document.querySelector(`.demo-step[data-step="${id}"]`);
    const output = stepEl.querySelector('.step-output');
    const elapsedEl = output.querySelector('[data-elapsed]');
    const isRerun = btn.classList.contains('done');

    btn.classList.remove('done');
    btn.classList.add('running');
    btn.disabled = true;
    btn.textContent = '运行中';

    if (isRerun) {
      output.classList.remove('visible');
      await sleep(120);
    }

    await sleep(STEP_DELAYS[id] || 400);

    // Hydrate any [data-content="..."] nodes from LLM_DATA.
    const contentEls = output.querySelectorAll('[data-content]');
    contentEls.forEach(el => {
      const key = el.dataset.content;
      if (key === 'classify' && LLM_DATA?.classify?.content) {
        el.innerHTML = renderJson(LLM_DATA.classify.content);
      }
    });

    if (elapsedEl) {
      const t = realTime(id);
      if (t) elapsedEl.textContent = t;
    }
    output.classList.add('visible');

    btn.classList.remove('running');
    btn.classList.add('done');
    btn.disabled = false;
    btn.textContent = '✓ 已运行（点击重跑）';

    document.querySelectorAll(`.demo-step[data-requires="${id}"]`).forEach(dep => {
      dep.classList.remove('locked');
      const depBtn = dep.querySelector('.step-btn');
      if (depBtn) depBtn.disabled = false;
    });

    if (!isRerun && id !== 'probe') {
      const rect = output.getBoundingClientRect();
      const offset = rect.bottom - window.innerHeight;
      if (offset > 0) {
        window.scrollBy({ top: offset + 24, behavior: 'smooth' });
      }
    }
  }

  // ---------- diarization side-step ---------- //

  async function runDiarize(btn) {
    if (btn.disabled && !btn.classList.contains('done')) return;
    const stepEl = btn.closest('.demo-step');
    const output = stepEl.querySelector('.step-output');
    const isRerun = btn.classList.contains('done');

    btn.classList.remove('done');
    btn.classList.add('running');
    btn.disabled = true;
    btn.textContent = '加载示例';

    if (isRerun) {
      output.classList.remove('visible');
      await sleep(120);
    }

    await sleep(STEP_DELAYS.diarize);
    output.classList.add('visible');

    btn.classList.remove('running');
    btn.classList.add('done');
    btn.disabled = false;
    btn.textContent = '✓ 已展示（点击重看）';
  }

  // ---------- choice handler — every option SERVES, no refusals ---------- //

  function buildHeader(label, subtitle, badge) {
    return `
      <div class="verdict ${badge.tone}">${badge.text}</div>
      <h4>${label}</h4>
      <p class="meta">${subtitle}</p>
    `;
  }

  function llmBlock(key) {
    if (!LLM_DATA) {
      return '<p class="choice-placeholder">加载 demo_responses.json 中…刷新一下页面试试。</p>';
    }
    const r = LLM_DATA[key];
    if (!r || r.error) {
      return `<p class="choice-placeholder">该选项的 LLM 响应未捕获${r?.error ? `：${escapeHtml(r.error)}` : ''}。</p>`;
    }
    const meta = `
      <p class="meta">
        模型 <code>${LLM_DATA._meta?.model || '?'}</code> ·
        ${r.elapsed_s}s ·
        ${r.usage?.completion_tokens || '?'} comp tokens ·
        采集于 ${LLM_DATA._meta?.captured_at || '?'}
      </p>
    `;
    return `<div class="llm-output">${renderMarkdown(r.content)}</div>${meta}`;
  }

  function handleChoice(btn) {
    const choice = btn.dataset.choice;
    document.querySelectorAll('.choice').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');

    const out = document.getElementById('choice-output');

    let html;
    if (choice === 'A') {
      html = buildHeader('A. 全文整理',
        '不依赖时间戳引文，按 prompts/clean_transcript.md 输出清理后的纯净文本。',
        { tone: 'ok', text: '✓ LLM 已生成' }) + llmBlock('A');
    } else if (choice === 'B') {
      html = buildHeader('B. 总结核心观点',
        '按 casual_discussion preset 输出五个小节。所有"建议 / 下一步"都打 （推测） 标。',
        { tone: 'ok', text: '✓ LLM 已生成' }) + llmBlock('B');
    } else if (choice === 'C') {
      html = buildHeader('C. 提取待办事项',
        '即便没明确接收人和截止时间，也输出方向性 todo。owner 用 临时-N 占位，不确定字段显式标注。',
        { tone: 'ok', text: '✓ LLM 已生成' }) + llmBlock('C');
    } else if (choice === 'D') {
      html = buildHeader('D. 按参与人拆分任务',
        '没 diarization 没关系：用 SPEAKER_01 / 临时-N 占位，把任务拆出来；不确定项里写"待确认收件人"，让用户决定要不要替换。',
        { tone: 'ok', text: '✓ LLM 已生成（修订前会拒绝）' }) + llmBlock('D');
    } else if (choice === 'E') {
      html = buildEDraftFlow();
    } else if (choice === 'F') {
      html = buildHeader('F. 自定义处理方式',
        '不预设输出形态。告诉 skill 你想要什么。仍然遵守"不编造、推测必标注"。',
        { tone: 'ok', text: '✓ 等待你的输入' }) + `
        <ul>
          <li>"提取这段录音里关于'对比表'的所有原话片段"</li>
          <li>"判断这段讨论的口吻是哪一方在指导哪一方"</li>
          <li>"找出说话人提到的每一个学术概念，给出 30 字以内的解释"</li>
          <li>"把这段话改写成给学生的书面反馈意见"</li>
        </ul>
        <p class="meta">这次 demo 没替 F 预先调 LLM —— 因为目标空间是开放的。把上面任一句话或你自己的需求贴给真实 skill 即可。</p>
      `;
    }

    out.classList.remove('swap');
    void out.offsetWidth;
    out.classList.add('swap');
    out.innerHTML = html;
  }

  // ---------- E: draft → confirm → send flow ---------- //

  function buildEDraftFlow() {
    const r = LLM_DATA?.E;
    if (!r || r.error) return llmBlock('E');

    const draftHtml = renderMarkdown(r.content);
    const meta = `
      <p class="meta">
        模型 <code>${LLM_DATA._meta?.model || '?'}</code> ·
        ${r.elapsed_s}s ·
        ${r.usage?.completion_tokens || '?'} comp tokens
      </p>
    `;

    return buildHeader('E. 消息草稿（草稿 → 确认 → 发送）',
      '草稿编辑好后，点 ▶ 发送 → 弹确认对话框 → 用户点击 ✓ 确认发送 → 才出去。这是 skill 唯一拦动作的地方。',
      { tone: 'partial', text: '✓ LLM 已生成草稿，等你确认' }) + `
      <div class="send-flow">
        <div class="llm-output draft-display">${draftHtml}</div>
        ${meta}
        <div class="send-bar">
          <p class="send-warn">⚠️ 收件人 <code>SPEAKER_01</code> 真实身份未确认。点发送前请先在心里确认这个映射对不对（在真实 skill 里这一步会 prompt 你提供 speaker map）。</p>
          <button class="send-btn" data-action="send-msg">▶ 发送</button>
        </div>
      </div>
      <div id="confirm-overlay" class="confirm-overlay" hidden>
        <div class="confirm-dialog">
          <h4>确认发送？</h4>
          <p>这条消息会发送给 <strong>SPEAKER_01</strong>（真实身份未确认）。</p>
          <p>点击"确认发送"后<strong>不可撤销</strong>。</p>
          <div class="confirm-buttons">
            <button class="cancel" data-action="cancel-send">取消</button>
            <button class="confirm" data-action="confirm-send">✓ 确认发送</button>
          </div>
        </div>
      </div>
    `;
  }

  function openSendConfirm() {
    const overlay = document.getElementById('confirm-overlay');
    if (overlay) overlay.hidden = false;
  }

  function cancelSend() {
    const overlay = document.getElementById('confirm-overlay');
    if (overlay) overlay.hidden = true;
  }

  function confirmSend() {
    const overlay = document.getElementById('confirm-overlay');
    if (overlay) overlay.hidden = true;

    // Replace the send bar with a "sent" indicator.
    const flow = document.querySelector('.send-flow');
    if (!flow) return;
    const sendBar = flow.querySelector('.send-bar');
    if (!sendBar) return;
    const ts = new Date().toLocaleString('zh-CN', { hour12: false });
    const msgId = 'demo-' + Math.random().toString(36).slice(2, 10);
    sendBar.outerHTML = `
      <div class="sent-indicator">
        <div class="sent-icon">✓</div>
        <div>
          <p class="sent-title">已发送（演示）</p>
          <p class="sent-detail">→ <code>SPEAKER_01</code> · ${ts} · message_id: <code>${msgId}</code></p>
          <p class="sent-note">真实 skill 里这条会调用 messaging adapter（飞书 / Slack / 邮件），目前 MVP 只演示流程，无实际外发。</p>
        </div>
      </div>
    `;
  }

})();
