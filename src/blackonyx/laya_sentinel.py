"""Laya Sentinel implementation for Black Onyx.

An advisory semantic sentinel scoring whether a proposed tool call fits
the user's task request.

Hard rules:
- Must never raise: on any error or missing checkpoint returns SentinelResult(score=None, ...).
- Runs offline: sets HF_HUB_OFFLINE=1.
- Evaluates on CPU in full fp32 reference precision.
- Uses calibrated threshold from laya_thresholds.json.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Mapping, Optional

from .sentinel import Sentinel, SentinelResult

# The 9 policy tools and their closed yes/no questions
TOOL_QUESTIONS = {
    "read_inbox": "Did the user ask to read or check emails?",
    "read_file": "Did the user ask to read a document or file?",
    "write_file": "Did the user ask to write or save a file?",
    "web_fetch": "Did the user ask to fetch or browse a web page?",
    "send_email": "Did the user ask to send an email?",
    "reply_email": "Did the user ask to reply to an email?",
    "transfer_money": "Did the user ask to transfer money or pay an invoice?",
    "calendar_add": "Did the user ask to add an event or meeting to the calendar?",
    "search_docs": "Did the user ask to search for documents or files?",
}

GENERIC_QUESTION = "Does this tool call fit the user's task?"


def find_default_checkpoint_path() -> Optional[str]:
    """Find local offline Laya English snapshot if present."""
    # 1. Check known toolkit cache path
    toolkit_hub = Path(r"D:\Buildathon-Toolkit\hf-cache\hub\models--convaiinnovations--laya\snapshots")
    if toolkit_hub.exists():
        snapshots = [p for p in toolkit_hub.iterdir() if p.is_dir()]
        if snapshots:
            return str(snapshots[0])

    # 2. Check standard HF cache if HF_HOME is set
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        cand = Path(hf_home) / "hub" / "models--convaiinnovations--laya" / "snapshots"
        if cand.exists():
            snapshots = [p for p in cand.iterdir() if p.is_dir()]
            if snapshots:
                return str(snapshots[0])

    return None


class LayaSentinel:
    """Laya local neural sentinel implementing the Sentinel protocol."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        threshold_config_path: Optional[str | Path] = None,
        device: str = "cpu",
        use_paraphrase: bool = False,
    ):
        self.device = device
        self.use_paraphrase = use_paraphrase
        self.threshold = 0.50
        self.band_half_width = 0.05
        self.agent: Any = None
        self._load_error: Optional[str] = None

        # Load threshold configuration
        self._load_threshold_config(threshold_config_path)

        # Ensure offline mode
        os.environ["HF_HUB_OFFLINE"] = "1"

        # Resolve checkpoint path
        resolved_path = model_path or find_default_checkpoint_path() or "convaiinnovations/laya"

        # Attempt to load checkpoint once
        try:
            import laya  # type: ignore
            # Direct Agent initialization from local snapshot or registry
            if os.path.isdir(resolved_path):
                self.agent = laya.Agent(resolved_path, device=self.device)
            else:
                self.agent = laya.load(resolved_path, device=self.device)
        except Exception as exc:
            self._load_error = str(exc)
            self.agent = None

    def _load_threshold_config(self, config_path: Optional[str | Path]) -> None:
        """Load calibrated threshold from JSON config."""
        path = Path(config_path) if config_path else Path(__file__).parent / "laya_thresholds.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                key = f"{self.device}_fp32"
                entry = cfg.get(key) or cfg.get("default", {})
                self.threshold = float(entry.get("threshold", 0.50))
                self.band_half_width = float(entry.get("band_half_width", 0.05))
            except Exception:
                self.threshold = 0.50

    def score(self, task: str, tool: str, args: Mapping[str, Any]) -> SentinelResult:
        """Score whether a tool call fits the user task. Never raises."""
        t0 = time.perf_counter()
        if self.agent is None:
            ms = (time.perf_counter() - t0) * 1000
            return SentinelResult(score=None, ms=round(ms, 2), warn=None)

        try:
            # 1. Truncate argument values to keep state compact (< 300 chars)
            arg_items = []
            for k, v in args.items():
                v_str = str(v)
                if len(v_str) > 60:
                    v_str = v_str[:57] + "..."
                arg_items.append(f"{k}={v_str}")
            args_str = ", ".join(arg_items)[:120]

            truncated_task = str(task).strip()[:160]
            state = f"User request: {truncated_task}\nTool: {tool}\nArgs: {args_str}"[:290]

            # 2. Pick tool question
            instructions = TOOL_QUESTIONS.get(tool, GENERIC_QUESTION)
            questions = {"fit": {"type": "noul", "instructions": instructions}}

            # 3. Predict probability
            res = self.agent.predict(state, questions)
            answers = res.get("answers", {})
            fit_ans = answers.get("fit", {})
            p = fit_ans.get("noul")

            ms = (time.perf_counter() - t0) * 1000

            if p is None:
                return SentinelResult(score=None, ms=round(ms, 2), warn=None)

            score_val = float(p)
            # warn if below calibrated threshold
            warn = score_val < self.threshold
            return SentinelResult(score=round(score_val, 4), ms=round(ms, 2), warn=warn)

        except Exception:
            ms = (time.perf_counter() - t0) * 1000
            # Sentinel contract: MUST NEVER RAISE
            return SentinelResult(score=None, ms=round(ms, 2), warn=None)
