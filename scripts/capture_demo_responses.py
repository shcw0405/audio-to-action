"""Capture real LLM responses for the GitHub Pages demo.

For each demo affordance (classify / A / B / C / D / E), call the configured
LLM with the canonical 60s transcript and the matching prompt template. Save
all responses to docs/demo_responses.json so the static site can show real
model outputs without a server.

Usage::

    export DEMO_API_KEY=...
    python scripts/capture_demo_responses.py

Reads:  prompts/*.md
Writes: docs/demo_responses.json

The API key MUST come from environment. We never commit it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
OUT_PATH = ROOT / "docs" / "demo_responses.json"

DEFAULT_API_URL = "https://uni-api.cstcloud.cn/v1/chat/completions"
DEFAULT_MODEL = "minimax-m27-gw"

# Path to a UTF-8 text file holding the canonical transcript. Override with
# --transcript-file. The file is a single paragraph; no segments / no
# diarization is assumed (the realistic case for many ASR providers).
DEFAULT_TRANSCRIPT_FILE = "/tmp/demo2_transcript.txt"


def strip_think(text: str) -> str:
    """Reasoning models wrap their chain-of-thought in <think>...</think>.
    The site only wants the final answer."""
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()


def strip_outer_fence(text: str) -> str:
    """Remove a single outer ```language ... ``` markdown code fence if present.

    Some models still wrap whole responses in a fence even when asked not to.
    The website wants raw markdown / JSON for downstream rendering.
    """
    s = text.strip()
    m = re.match(r"^```(?:json|markdown|md)?\s*\n(.*)\n```\s*$", s, re.DOTALL)
    return m.group(1).strip() if m else s


def clean_response(text: str) -> str:
    return strip_outer_fence(strip_think(text))


def load_prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


class LLM:
    def __init__(self, url: str, key: str, model: str) -> None:
        self.url = url
        self.key = key
        self.model = model

    def call(self, system: str, user: str, max_tokens: int = 2000) -> str:
        t0 = time.time()
        r = requests.post(
            self.url,
            headers={
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.2,
            },
            timeout=300,
        )
        r.raise_for_status()
        elapsed = time.time() - t0
        body = r.json()
        content = body["choices"][0]["message"]["content"]
        usage = body.get("usage", {})
        return {
            "content": clean_response(content),
            "raw_content": content,
            "elapsed_s": round(elapsed, 1),
            "usage": usage,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_API_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--key-env", default="DEMO_API_KEY",
                        help="env-var name holding the API key")
    parser.add_argument("--transcript-file", default=DEFAULT_TRANSCRIPT_FILE,
                        help="UTF-8 text file with the transcript to feed the LLM")
    parser.add_argument("--only", default=None,
                        help="run only this single key (e.g. classify, A, B...)")
    args = parser.parse_args()

    key = os.environ.get(args.key_env)
    if not key:
        sys.exit(
            f"missing env var {args.key_env}. Set it before running:\n"
            f"  export {args.key_env}=<your-key>"
        )

    transcript_path = Path(args.transcript_file)
    if not transcript_path.is_file():
        sys.exit(f"transcript file not found: {transcript_path}")
    transcript = transcript_path.read_text(encoding="utf-8").strip()
    if not transcript:
        sys.exit(f"transcript file is empty: {transcript_path}")
    print(f"[in] transcript {transcript_path}: {len(transcript)} chars")

    llm = LLM(args.url, key, args.model)

    # Each task pairs a system-prompt template with the user-side message.
    # The user side narrates the realistic situation: "this transcript came
    # from a recording with no segments and no diarization; please serve
    # the user's request despite the gaps."
    transcript_block = f"```\n{transcript}\n```"
    no_segments_note = (
        "本次 ASR 输出**没有 segments、没有 diarization**（provider 仅返回 text）。"
        "按修订后的服务姿态：尽力输出，不确定的字段显式标注（推测 / 待确认 / 占位符），"
        "不要因为缺时间戳或缺 speaker 就拒绝。"
    )

    tasks = {
        "classify": {
            "system": load_prompt("classify_audio_content.md"),
            "user": (
                f"以下是 ASR 转写的全文：\n\n{transcript_block}\n\n"
                "{no_segments_note}\n\n"
                "请按 prompt 契约输出**严格 JSON**（不要 markdown 围栏，不要前后缀）。"
            ).format(no_segments_note=no_segments_note),
            "max_tokens": 1200,
        },
        "A": {
            "system": load_prompt("clean_transcript.md"),
            "user": (
                f"原始 ASR 全文：\n\n{transcript_block}\n\n"
                f"{no_segments_note}\n\n"
                "请输出清理后的版本（去填充词、整理标点、合并段落）。"
                "由于没有时间戳，**不要**输出 [SPEAKER_xx | mm:ss] 形式的标头；"
                "直接输出纯净的 markdown 段落即可。不要加 markdown 围栏。"
            ),
            "max_tokens": 800,
        },
        "B": {
            "system": (
                "你是一个忠实记录、谨慎推测的研究助手。"
                "下面是一段已被分类为 `casual_discussion`（置信度 0.55）的录音转写。"
                "请按 casual_discussion preset 输出 markdown 报告，分以下小节："
                "一、讨论背景；二、核心观点；三、达成共识；四、未解决问题；五、下一步行动。"
                "凡不是录音中明确说出的内容，必须打 `（推测）` 标。"
                "不要 markdown 围栏。"
            ),
            "user": f"转写全文：\n\n{transcript_block}",
            "max_tokens": 1800,
        },
        "C": {
            "system": load_prompt("extract_tasks.md"),
            "user": (
                "用户希望从下面这段录音里**提取待办事项**（C 选项）。\n\n"
                f"{no_segments_note}\n\n"
                f"转写：\n\n{transcript_block}\n\n"
                "尽力输出。即使没有明确的接收人 / 截止时间，也写出方向性 todo，"
                "并对所有非显式字段标注 `（推测）` / `（待确认）`。"
                "owner 不明时使用 `临时-1` 占位符。不要 markdown 围栏。"
            ),
            "max_tokens": 3000,
        },
        "D": {
            "system": load_prompt("extract_tasks.md"),
            "user": (
                "用户希望**按参与人拆分任务**（D 选项）。\n\n"
                f"{no_segments_note}\n\n"
                f"转写：\n\n{transcript_block}\n\n"
                "尽力服务用户：用 `SPEAKER_01`、`临时-1` 等占位符代替不可知的姓名，"
                "把任务列出来。不确定的字段（收件人、截止时间、验收）显式标注。"
                "**不要**拒绝输出。不要 markdown 围栏。"
            ),
            "max_tokens": 1800,
        },
        "E": {
            "system": load_prompt("build_student_messages.md"),
            "user": (
                "用户希望生成**一份可发送的消息草稿**（E 选项）。\n\n"
                f"{no_segments_note}\n\n"
                f"转写：\n\n{transcript_block}\n\n"
                "请输出 **1 份**完整草稿（不需要多人多份）。收件人未知 → 使用 `SPEAKER_01` "
                "或 `临时-1` 占位，并在不确定项里加一条 [请确认收件人姓名] 说明。"
                "草稿正文中文 2-5 句，附依据和不确定项。**不要**拒绝输出。不要 markdown 围栏。"
            ),
            "max_tokens": 1800,
        },
    }

    if args.only:
        if args.only not in tasks:
            sys.exit(f"unknown task {args.only}; choose from {sorted(tasks)}")
        tasks = {args.only: tasks[args.only]}

    results: dict[str, Any] = {}
    for key_name, spec in tasks.items():
        print(f"[llm] {key_name} ... ", flush=True, end="")
        try:
            r = llm.call(spec["system"], spec["user"], max_tokens=spec["max_tokens"])
            results[key_name] = r
            print(
                f"ok ({r['elapsed_s']}s, "
                f"{r['usage'].get('completion_tokens', '?')} comp tokens, "
                f"content: {len(r['content'])} chars)"
            )
        except Exception as e:  # noqa: BLE001
            print(f"FAILED: {e}")
            results[key_name] = {"error": str(e)}

    # Merge with existing file (so re-running with --only doesn't wipe other tasks)
    if OUT_PATH.exists() and not args.only:
        # Full re-run: replace
        existing: dict[str, Any] = {}
    elif OUT_PATH.exists():
        existing = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    else:
        existing = {}

    existing.update(results)
    existing["_meta"] = {
        "model": args.model,
        "endpoint": args.url,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "transcript": transcript,
        "transcript_chars": len(transcript),
        "captured_keys": sorted(k for k in existing if k != "_meta"),
    }

    OUT_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[done] saved → {OUT_PATH}")


if __name__ == "__main__":
    main()
