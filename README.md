# audio-to-action

> 一个**懂办公流程**的语音 Skill：收到录音后，它知道下一步该做什么。

🌐 **Live demo & docs** → [**caixu.me/audio-to-action**](https://caixu.me/audio-to-action/) — 包含一段真实实验室录音的端到端运行展示。

普通 ASR 工具只做一件事：

```
音频 → 一大块文字
```

然后你坐下来，从头读到尾，把任务拎出来、按人拆开、记进备忘录、起草要发给同学的消息。一周三个会，光读 transcript 就要一晚上。

`audio-to-action` 把这整段流程**固化下来**：

```
音频
  → 语音转写
  → 清理
  → 判断这是哪种录音（5 种之一，或"我不确定"）
  → 套对应的 preset，输出结构化结果
  → 待审查的消息草稿（永远不会自动发）
```

它**不是**一个"聪明的 agent"。聪明的 agent 会乱编学生姓名、乱猜截止时间、热心地把组会摘要群发给所有人。这个 skill 的设计目标恰恰相反：**把流程钉死，把不确定的地方明确标出来，把对外的动作拦在人工审查之前**。

---

## 它解决的问题

研究所/课题组里录音随处可见：

- **组会**（导师 + 多个学生，有项目同步、有任务分派）
- **导师 + 单个学生** 的讨论（有指导意见、有下一步任务）
- **临时讨论 / coffee chat**（有想法但没形成任务）
- **语音备忘录**（一个人对自己说话）
- **学生进展汇报**（汇报上周做了什么）

每种场景需要的处理**不一样**。把组会模板套到临时聊天上，会得出"张同学需要在周五前完成 X"这种**根本没人说过**的"任务"。这是普通 LLM workflow 最常见的失败模式。

`audio-to-action` 给每种场景一个 preset，配一套 prompt，明确**什么能输出、什么必须先问用户**。

---

## 你会拿到什么

跑完一段录音，你会得到：

1. **`transcript.json`** —— 统一 schema 的转写结果。任何 ASR provider 进来都归一化成同一种结构。
2. **`transcript.cleaned.md`** —— 去掉"嗯/啊/那个"、断好句、按 speaker 分段的可读版本。
3. **一份 preset 报告**，根据录音类型自动选模板：
   - 组会 → 摘要、本周核心、按人拆分的任务、待审查消息清单、待确认问题
   - 临时讨论 → 背景、核心观点、达成共识、未解决问题
   - 语音备忘录 → 笔记整理、Todo、后续可展开方向
   - 等等。
4. **如果生成了消息草稿**：每条都附"依据时间戳 + 简引"和"不确定项"，给你审查。**永远不会自动发**。

---

## 一个具体的例子

输入是一段 5 分钟的组会录音片段，cleaned transcript 长这样：

```
[SPEAKER_01 | 00:48] 下周三之前 ImageNet baseline 跑通，
                     code 整理一下发我。
[SPEAKER_02 | 01:05] 可以，下周三前应该没问题。
[SPEAKER_01 | 01:48] 李同学这边，head 数从 8、12、16、24
                     都跑一组，每组三个 seed，下周组会讲。
```

skill 输出的 preset 报告（节选）：

```markdown
## 三、按人拆分的任务

### SPEAKER_02
- 任务：在 ImageNet 上跑通 baseline，对齐 paper 精度
- 截止时间：下周三之前（依据：00:48）
- 验收标准：未明确（仅说"发我一份"）
- 不确定项：
  - 验收标准是否需要附实验报告？（待确认）

### SPEAKER_03
- 任务：head 数消融 8/12/16/24，每组 3 seed
- 截止时间：下周组会前（推测，未给出具体日期）
- 不确定项：下周组会的具体日期需要导师确认

## 四、待审查消息清单

### 1. 发给 SPEAKER_02
**消息草稿：**
同学你好，本周请把 ImageNet 上的 baseline 跑通……

**依据：**
- 录音 00:48-01:05：下周三之前 ImageNet baseline，code 整理

**不确定项：**
- 收件人真实身份未确认（SPEAKER_02 → ?）
```

注意三件事：

1. **`SPEAKER_02` 没有变成"张同学"**。Diarization 给的是 `SPEAKER_02`，没人告诉过 skill 这是谁，所以它就保持 `SPEAKER_02`。要发的时候你把映射告诉它，它才会替换。
2. **每条任务都附时间戳引用**。没引用的不是任务，会被挪到"待确认问题"里。
3. **"下周组会"被标成"推测"**，因为录音里没说具体哪天。你看到这个标记，就知道要去补一个真实日期才能发。

完整的输入/输出对照看 [`examples/`](examples/)。

---

## "不确定的时候问，不要猜"

这是这个 skill 最重要的设计原则。

如果转写出来的内容，分类置信度低于 0.6，或者根本不像任何一个 preset，skill 不会硬套模板。它会回你：

```
我已完成转写（约 14 分钟，47 段）。
这段录音看起来更像 一次临时讨论，置信度 0.55。

你希望我怎么处理？

A. 只整理全文转写
B. 总结核心观点
C. 提取待办事项
D. 按参与人拆分任务
E. 生成可发送给他人的消息草稿（**会先给你审查，不会自动发送**）
F. 自定义处理方式（请告诉我具体目标）
```

把"组会摘要"自动套到 coffee chat 上是这个 skill 最想避免的失败模式。

---

## 五条硬规则

这些规则在 prompt 和 settings 两层冗余实现，即便 LLM 当下被你说服，配置层也会兜住：

| 规则 | 为什么 |
| --- | --- |
| 不编造 speaker 身份 | `SPEAKER_01` 保持 `SPEAKER_01`，直到你给映射 |
| 不编造学生姓名、截止时间、任务归属 | 推测的内容必须打 `（推测）`，不能伪装成事实 |
| 不自动发送任何东西 | MVP 只生成草稿，发送是另一个明确审批的工具 |
| 不在个人草稿里夹带完整 transcript | 草稿只引用与本人有关的段落，不漏会议全貌 |
| 任务必须附时间戳引文 | 没引文 → 不是任务，挪到"待确认问题" |

---

## 5 分钟上手

```bash
# 1. 把 skill 放到 Claude Code 的 skills 目录
git clone https://github.com/shcw0405/audio-to-action.git
cp -r audio-to-action ~/.claude/skills/

# 2. 装运行依赖
cd audio-to-action
pip install -r requirements.txt

# 3. 配置 ASR endpoint
#    编辑 settings.yaml::asr.openai_compatible.base_url
#    设置 API key（环境变量名在 settings.yaml 里指定，默认 ASR_API_KEY）
export ASR_API_KEY=sk-...

# 4. 在 Claude Code 里丢一个音频文件
#    "整理一下这段录音 ./meeting.mp3"
```

skill 会自动：

1. 检查文件（格式、大小、时长）
2. 调你配的 ASR provider 转写
3. 归一化成统一 schema
4. 分类（5 种之一，或 unknown）
5. 套 preset，**或者**不确定时弹菜单问你
6. 把 `transcript.json` / `transcript.cleaned.md` / `report.md` 写到音频同目录的 `out/`

---

## 架构

```
audio-to-action/
├── SKILL.md          ← Claude 触发后读这一份（流程契约）
├── README.md         ← 你正在读的这一份（项目叙事）
├── settings.yaml     ← ASR + 分类阈值 + 安全开关
├── prompts/          ← 6 份纯 markdown prompt，每份职责明确
├── tools/            ← Python 运行时（schema、ASR adapter、归一化）
├── examples/         ← 真实示例：输入 cleaned transcript / 4 种输出
├── tests/            ← 契约测试，不打网络
└── scripts/          ← 跑 ASR pipeline 的 Python 入口（批处理用）
```

三层解耦：

- **Prompts 层**（`prompts/*.md`）—— LLM 行为契约，纯 markdown，可审查、可 diff、可 PR。
- **Tools 层**（`tools/*.py`）—— 数据契约，类型严格。schema 验证、provider 注册、归一化、ffmpeg 包装、密钥脱敏。
- **配置层**（`settings.yaml`）—— 切 provider、调阈值、开关安全策略，不动代码。

---

## 切 ASR provider

只改 `settings.yaml::asr.provider`：

| value | 状态 | 说明 |
| --- | --- | --- |
| `openai_compatible` | ✅ 已实装 | 适用于 OpenAI、faster-whisper-server、vLLM、本地 Doubao 等任何 `POST /v1/audio/transcriptions` 兼容形式 |
| `faster_whisper_local` | 🟡 接口预留 | 实装 `_FasterWhisperLocal.transcribe` |
| `custom_http` | 🟡 接口预留 | 实装 `_CustomHTTP.transcribe` |
| Deepgram / Azure / Google / AssemblyAI | 🔲 未做 | 三步：写一个 `ASRProvider` 子类，加 `@register_provider` 装饰，在 `transcript_normalizer.py` 加一段 `_normalize_<name>` |

无 auth 的 endpoint 也支持 —— `api_key_env` 指向不存在的环境变量时，不会发 `Authorization` header。

---

## 加新 preset / 新内容类型

1. 把新 label 加到 `settings.yaml::classification.labels` 和 `tools/schema.py::ALLOWED_LABELS`
2. 在 `prompts/classify_audio_content.md` 加一段"如何识别这种类型"
3. 写一份新的 preset 模板（在 `SKILL.md` §6 里加一节，或单独 `prompts/preset_<name>.md`）
4. 加一个 `examples/<name>_output.md`
5. 在 `tests/test_content_classification.py` 加一条断言

---

## 跑测试

```bash
pip install pytest
pytest tests/ -v
```

测试**不打网络**，全是契约校验。把它们当作 skill 公开 API 的规格说明，不是覆盖率指标。

---

## MVP 不做什么

明确写出来的边界，免得给人不切实际的期望：

- ❌ **真实发送**（飞书/Slack/微信）—— 只生成草稿。发送是另一个工具，需要单独审批通道。
- ❌ **真实 speaker diarization** —— `tools/diarization_client.py` 接口在，唯一的 provider 是 `none`。pyannote / WhisperX 的钩子留好了。
- ❌ **超长音频自动切片** —— 默认拒绝超过 6 小时的录音。如果你的 ASR backend 是单线程的、对长输入会 hang，需要你在调用前自己切片。
- ❌ **跨会议状态保留** —— 每段录音独立处理，不会"延续上周未完成的任务"。
- ❌ **流式转写** —— 全是离线批处理。

这些扩展点都在代码里留好了接口，README 和 SKILL.md 都标了具体在哪扩。

---

## 设计原则（按优先级排序）

1. **固定流程优先**，不做花哨的 agent 人格
2. 收到音频后**知道下一步该做什么**，不只是转写
3. **ASR 与 LLM 后处理解耦**，两边都可以单独换
4. **熟悉的场景套 preset，陌生场景问用户**
5. 输出**为人工审查而设计**，不是为下游自动化
6. **对外消息必须显式人工批准**
7. **不确定的内容必须显式标注**

---

## License

MIT。详见 [LICENSE](LICENSE)。
