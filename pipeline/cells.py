"""One experimental cell: analyze, prompt, generate until QA accepts, persist."""

from __future__ import annotations

import csv
import hashlib
import json
import random
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from emotion_analyzer import TAU, EmotionAnalyzer, EmotionalContext
from generator import SEED, TEMPERATURE, HFGenerator, set_seed
from prompts import build_contextual_prompt, build_direct_prompt
from quality import response_quality_issues


def cell_path(outdir: Path, stimulus_id: str, epoch_id: str, condition: str) -> Path:
    return outdir / f"{stimulus_id}__{epoch_id}__{condition}.json"


def run_cell(
    analyzer: EmotionAnalyzer,
    generator: HFGenerator,
    stimulus_id: str,
    user_text: str,
    condition: str,
) -> Dict[str, Any]:
    analysis = analyzer.analyze(user_text, tau=TAU)
    ctx: EmotionalContext = analysis["emotional_context"]
    arch = generator.arch
    if condition == "baseline":
        prompt = build_direct_prompt(user_text, arch=arch)
    elif condition == "pipeline":
        prompt = build_contextual_prompt(user_text, ctx, arch=arch)
    else:
        raise ValueError(condition)

    response = ""
    issues: List[str] = ["empty"]
    attempt = 0
    while issues:
        cell_key = f"{stimulus_id}|{condition}|{generator.epoch_id}".encode()
        cell_salt = int(hashlib.md5(cell_key).hexdigest(), 16) % 1000
        set_seed(SEED + attempt * 17 + cell_salt)
        response = generator.generate(prompt, user_text, attempt=attempt)
        issues = response_quality_issues(response, epoch_id=generator.epoch_id)
        if issues:
            print(f"     QA reject try={attempt + 1}: {issues} | {response[:100]!r}", flush=True)
        attempt += 1

    return {
        "stimulus_id": stimulus_id,
        "epoch_id": generator.epoch_id,
        "model_id": generator.model_id,
        "condition": condition,
        "input": user_text,
        "prompt": prompt,
        "response": response,
        "emotion_model": analysis["emotion_model"],
        "emotional_context": asdict(ctx),
        "raw_emotions": analysis["raw_emotions"],
        "temperature": TEMPERATURE,
        "tau": TAU,
        "seed": SEED,  # protocol seed; retries derive from this and were not logged
        "device": generator.device,
        "qa_ok": True,
    }


def load_stimuli(path: Path) -> List[Dict[str, str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def merge_results(outdir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in sorted(outdir.glob("s*__E*__*.json")):
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    results_path = outdir / "all_results.json"
    results_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows


def export_blind_csv(rows: List[Dict[str, Any]], out_csv: Path) -> None:
    shuffled = list(rows)
    random.Random(SEED).shuffle(shuffled)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "item_id",
                "stimulus_id",
                "user_message",
                "assistant_response",
                "epoch_id",
                "model_id",
                "condition",
            ],
        )
        writer.writeheader()
        for i, row in enumerate(shuffled, start=1):
            writer.writerow(
                {
                    "item_id": f"item_{i:03d}",
                    "stimulus_id": row["stimulus_id"],
                    "user_message": row["input"],
                    "assistant_response": row["response"],
                    "epoch_id": row["epoch_id"],
                    "model_id": row["model_id"],
                    "condition": row["condition"],
                }
            )
