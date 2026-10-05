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
        model_version: Optional[str] = None,
    ):
        self.device = device
        self.use_paraphrase = use_paraphrase
        self.threshold = 0.50
        self.method = "per-tool question"
        self.weights: Optional[list[float]] = None
        self.band_half_width = 0.05
        self.agent: Any = None
        self._load_error: Optional[str] = None
        self.version = "v0"                     # v0 = original checkpoint; v2 = fine-tuned (opt-in, see _load_v2)
        self._v2: Optional[dict[str, Any]] = None
        self._v2_error: Optional[str] = None

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

        # Opt-in fine-tuned model. Off unless asked for; any problem leaves the original model in place.
        want = (model_version or os.environ.get("BLACKONYX_LAYA_MODEL", "")).strip().lower()
        if want == "v2" and self.agent is not None:
            self._load_v2()

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
                self.method = str(entry.get("method", "per-tool question"))
                self.weights = entry.get("weights")
                self.band_half_width = float(entry.get("band_half_width", 0.05))
            except Exception:
                self.threshold = 0.50

    def _load_v2(self) -> None:
        """Load the fine-tuned top layers (v2) on top of the original model. Validates everything before touching
        the model, so a failure leaves the original checkpoint exactly as it was."""
        try:
            import torch  # type: ignore
            d = Path(os.environ.get("BLACKONYX_LAYA_V2_DIR", r"D:\Buildathon-Toolkit\laya-ft"))
            meta = json.loads((d / "v2.json").read_text(encoding="utf-8"))
            sd = torch.load(d / "v2.pt", map_location="cpu")
            model = self.agent.model
            have = model.state_dict()
            for k, v in sd.items():
                if k not in have or tuple(have[k].shape) != tuple(v.shape):
                    raise ValueError(f"v2 weights do not match the model at '{k}'")
            model.load_state_dict(sd, strict=False)
            model.eval()
            internal = {"g": self.agent._to_internal({"type": "noul", "instructions": GENERIC_QUESTION})}
            self._v2 = {"threshold": float(meta["threshold"]), "internal": internal, "meta": meta}
            self.version = "v2"
        except Exception as exc:
            self._v2 = None
            self._v2_error = str(exc)

    def _build_state(self, task: str, tool: str, args: Mapping[str, Any]) -> str:
        arg_items = []
        for k, v in args.items():
            v_str = str(v)
            if len(v_str) > 60:
                v_str = v_str[:57] + "..."
            arg_items.append(f"{k}={v_str}")
        args_str = ", ".join(arg_items)[:120]
        truncated_task = str(task).strip()[:160]
        return "\n".join([f"User request: {truncated_task}", f"Tool: {tool}", f"Args: {args_str}"])[:290]

    def _score_v2(self, task: str, tool: str, args: Mapping[str, Any], t0: float) -> SentinelResult:
        import torch  # type: ignore
        from laya.common import collate_items  # type: ignore
        state = self._build_state(task, tool, args)
        item = self.agent._encode_state(state, ["g"], self._v2["internal"])[0]
        b = collate_items([[item]], self.agent.tok.pad_token_id)
        with torch.no_grad():
            out = self.agent.model(b["input_ids"], b["attention_mask"], b["marker_pos"], b["marker_mask"], b["qtype"])
        p = float(torch.softmax(out[0].float()[:, :2], -1)[0, 1])
        ms = (time.perf_counter() - t0) * 1000
        return SentinelResult(score=round(p, 4), ms=round(ms, 2), warn=p < self._v2["threshold"])

    def score(self, task: str, tool: str, args: Mapping[str, Any]) -> SentinelResult:
        """Score whether a tool call fits the user task. Never raises."""
        t0 = time.perf_counter()
        if self.agent is None:
            ms = (time.perf_counter() - t0) * 1000
            return SentinelResult(score=None, ms=round(ms, 2), warn=None)

        try:
            if self._v2 is not None:
                return self._score_v2(task, tool, args, t0)

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

            # 2. Questions for the calibrated method (see eval/laya_ladder.py)
            qs: dict[str, Any] = {}
            m = self.method
            stacked = m.startswith("stacked") and self.weights
            if stacked or m in ("generic question", "generic + per-tool", "all questions averaged"):
                qs["g"] = {"type": "noul", "instructions": GENERIC_QUESTION}
            if stacked or m in ("per-tool question", "generic + per-tool", "all questions averaged"):
                qs["t"] = {"type": "noul", "instructions": TOOL_QUESTIONS.get(tool, GENERIC_QUESTION)}
            if stacked or m in ("paraphrase average", "all questions averaged"):
                try:
                    from eval.sentinel_data import PARAPHRASE_QUESTIONS
                    for k, q in enumerate(PARAPHRASE_QUESTIONS.get(tool, [])):
                        qs[f"p{k}"] = {"type": "noul", "instructions": q}
                except Exception:
                    pass
            if not qs:
                qs["t"] = {"type": "noul", "instructions": TOOL_QUESTIONS.get(tool, GENERIC_QUESTION)}

            # 3. Predict probability (mean over the questions asked)
            res = self.agent.predict(state, qs)
            answers = res.get("answers", {})
            if stacked:
                import math
                from eval.calibrate_laya import KEYWORD_MAP
                g = float(answers.get("g", {}).get("noul", 0.5))
                t_ = float(answers.get("t", {}).get("noul", 0.5))
                ps = [float(v["noul"]) for k, v in answers.items() if k.startswith("p") and v.get("noul") is not None]
                kw = 1.0 if any(k in str(task).lower() for k in KEYWORD_MAP.get(tool, [tool])) else 0.0
                x = [g, t_, (sum(ps) / len(ps)) if ps else 0.5, kw, 1.0]
                z = sum(a * b for a, b in zip(self.weights, x))
                p = 1 / (1 + math.exp(-max(-30.0, min(30.0, z))))
            else:
                vals = [float(v["noul"]) for v in answers.values() if isinstance(v, dict) and v.get("noul") is not None]
                p = (sum(vals) / len(vals)) if vals else None

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
