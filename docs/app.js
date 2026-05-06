/* audio-to-action — interactive demo state machine
 *
 * Drives:
 *   1. Step buttons   ▶ run → spinner → ✓ done, with dependents unlocked
 *   2. Diarization side-step  (synthetic example reveal)
 *   3. A–F choice menu  (different responses including hard refusals)
 *
 * No framework. ~3 KB minified. Lives at docs/app.js.
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
    classify:  900,
    safety:    300,
  };

  const REAL_TIMES = {
    asr:      '实际 wall-clock 72s · 0.83× 实时（动画压缩到 ~1.6s）',
    classify: 'LLM 推理 ≈ 2s',
  };

  // ---------- init: lock dependent steps ---------- //

  document.querySelectorAll('.demo-step[data-requires]').forEach(el => {
    el.classList.add('locked');
  });

  // ---------- click delegation ---------- //

  document.body.addEventListener('click', e => {
    const btn = e.target.closest('[data-action], .choice');
    if (!btn) return;
    if (btn.dataset.action === 'run-step')      runStep(btn);
    else if (btn.dataset.action === 'run-diarize') runDiarize(btn);
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

    if (elapsedEl && REAL_TIMES[id]) {
      elapsedEl.textContent = REAL_TIMES[id];
    }
    output.classList.add('visible');

    btn.classList.remove('running');
    btn.classList.add('done');
    btn.disabled = false;
    btn.textContent = '✓ 已运行（点击重跑）';

    // unlock direct dependents
    document.querySelectorAll(`.demo-step[data-requires="${id}"]`).forEach(dep => {
      dep.classList.remove('locked');
      const depBtn = dep.querySelector('.step-btn');
      if (depBtn) depBtn.disabled = false;
    });

    // gentle scroll-into-view for newly revealed output (only on first run)
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

  // ---------- choice responses ---------- //

  const CHOICE_RESPONSES = {

    A: `
      <div class="verdict ok">✓ 可执行</div>
      <h4>A. 全文转写整理</h4>
      <p>不依赖时间戳引文，可以直接输出清理后的全文：</p>
      <pre><code>是测了什么？我们测了什么，对吧？
我比别人更完备的在哪些地方？

你自己这个表，其实不换论文 ——
你这个得有知道。要不然现在就是，
你不是一个按照论文的作文方式去做。
因为现在又随机又走了。

嗯，我现在又变成了，那我……</code></pre>
      <p class="meta">按 prompts/clean_transcript.md：去除"嗯"等无意义填充，修整标点和段落，<strong>但不改写、不翻译、不增删内容</strong>。最后那句"那我……"原录音确实就是不完整的，没有补全。</p>
    `,

    B: `
      <div class="verdict ok">✓ 可执行</div>
      <h4>B. 临时讨论整理（casual_discussion preset · 节选）</h4>
      <pre><code><span class="k">## 二、核心观点</span>

  · "测了什么 / 我们测了什么"是核心问题：当前结果尚未清楚回答
    "我们与其他工作在哪些维度上更完备"。
  · 当前论文写作组织偏松散，缺少一张明确的对比维度表，导致论
    述"随机又走了"，读者难以抓住主线。

<span class="k">## 四、未解决问题</span>

  · 究竟用哪些维度作为"更完备"的衡量标准？录音中未明确。
  · 论文当前写作框架是否需要重写？讨论提到了缺陷未决断。

<span class="k">## 五、下一步行动 <span class="w">（建议，待确认）</span></span>

  <span class="w">> 模型整理（推测），不是录音中明确交代的任务。</span>
  · <span class="w">（推测）</span>先把"对比维度表"补齐再写正文。
  · <span class="w">（推测）</span>把"完备性差异"作为论文 §1 的锚点。</code></pre>
      <p class="meta">B 不依赖时间戳，可以执行。但所有"建议 / 下一步"都被标 <span class="warn">（推测）</span> —— 录音里只点出了问题，没给出建议。</p>
    `,

    C: `
      <div class="verdict partial">⚠ 部分降级</div>
      <h4>C. 待办事项提取</h4>
      <p>这段录音里<strong>没有</strong>明确的"X 在 Y 之前完成 Z"模式 —— 这是 <code>prompts/extract_tasks.md</code> 定义的"任务"。下面是<em>推测出来的方向性 todo</em>，不是任务：</p>
      <ul>
        <li><span class="warn">（推测）</span> 整理"对比维度表"作为论文写作前置；触发条件：录音里反复出现"测了什么"</li>
        <li><span class="warn">（推测）</span> 重新梳理论文 §1 论述顺序，避免"随机又走了"</li>
      </ul>
      <p>跳过的内容：</p>
      <ul>
        <li>"你这个得有知道" —— 没指定接收人，<strong>降级为待确认问题</strong>，不会进 todo</li>
      </ul>
      <p class="meta">所有条目均无 owner、无截止时间、无验收标准。skill 不会把这些当任务派发给任何人。</p>
    `,

    D: `
      <div class="verdict rejected">✗ 拒绝输出</div>
      <h4>D. 按参与人拆分任务</h4>
      <p><strong>无法生成。</strong>触发了两条硬规则：</p>
      <ol>
        <li><code>diarization=false</code> + <code>segments=[]</code> → 没有 <code>SPEAKER_xx</code> 标签可用，"参与人"概念不存在</li>
        <li><code>prompts/extract_tasks.md</code> 要求每条任务附时间戳引文（<code>录音 mm:ss-mm:ss</code>），但 <code>segments</code> 为空，时间戳不可获得</li>
      </ol>
      <p>要 unblock，下面任一项即可：</p>
      <ul>
        <li>切换到一个返回 <code>segments</code> 的 ASR provider（参考 settings.yaml::asr.provider）</li>
        <li>启用 pyannote / WhisperX diarization（settings.yaml::diarization.enable: true）</li>
      </ul>
      <p class="meta">这正是 skill <em>设计</em> 的拒绝行为，不是 bug。"宁愿拒绝也不要伪造任务"。</p>
    `,

    E: `
      <div class="verdict rejected">✗ 拒绝输出</div>
      <h4>E. 消息草稿</h4>
      <p><strong>无法生成。</strong>这是 skill 最严格的边界，触发三条硬规则（任一未满足都不行）：</p>
      <ol>
        <li>diarization=false → 收件人不可识别（不会编造"张同学"）</li>
        <li>segments=[] → 草稿引用无时间戳依据，<code>prompts/build_student_messages.md</code> 拒绝</li>
        <li><code>safety.require_speaker_map_for_per_person_drafts: true</code></li>
      </ol>
      <p>为什么这么严？因为草稿一旦发送是<strong>不可逆</strong>的。给错人、给错任务、给错截止时间，都是真实会让你被讨厌的事。所以这条边界宁严勿松。</p>
      <p class="meta">即使你坚持 "就用 SPEAKER_01 当临时占位"，skill 也会要求你<em>显式</em>提供 speaker_map → name 映射后才生成草稿。</p>
    `,

    F: `
      <div class="verdict ok">✓ 等待你的输入</div>
      <h4>F. 自定义处理方式</h4>
      <p>请告诉我具体目标。一些可能的方向：</p>
      <ul>
        <li>"提取这段录音里关于'对比表'的所有原话片段"</li>
        <li>"判断这段讨论的口吻是哪一方在指导哪一方"</li>
        <li>"找出说话人提到的每一个学术概念，给出 30 字以内的解释"</li>
        <li>"把这段话改写成给学生的书面反馈意见"</li>
      </ul>
      <p class="meta">F 不预设输出形态，但仍然遵守 skill 的所有硬规则：不编造、推测必标注、不发送、不夹带全文。</p>
    `,
  };

  function handleChoice(btn) {
    const choice = btn.dataset.choice;
    document.querySelectorAll('.choice').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');

    const out = document.getElementById('choice-output');
    out.classList.remove('swap');
    void out.offsetWidth;  // force reflow → restart fade animation
    out.classList.add('swap');
    out.innerHTML = (CHOICE_RESPONSES[choice] || '<p>未实现</p>').trim();
  }

})();
