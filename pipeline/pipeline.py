"""
HF-only ambivalent-emotion pipeline.

Dissertation anchors (historical eras E1–E4; Hugging Face IDs):
  E1 microsoft/DialoGPT-medium
  E2 facebook/blenderbot-400M-distill
  E3 microsoft/Phi-3-mini-4k-instruct
  E4 Qwen/Qwen2.5-3B-Instruct

Protocol:
  - One cell per process for E3/E4 (load → generate → exit)
  - Skip cells already on disk
  - GoEmotions on CPU
  - TEMPERATURE in this file is None (greedy / DialoGPT beam search);
    the evaluated 96-cell batch is heterogeneous (see the dissertation generation table)
  - Invalid cells are regenerated in place until a reply is accepted;
    the retry count was not logged. The published batch is the final 96 cells
  - DialoGPT (E1) uses beam search (num_beams=5); instruct anchors use greedy

Modules:
  emotion_analyzer.py  GoEmotions + ambivalence (τ)
  prompts.py           baseline / pipeline prompts per architecture
  generator.py         HFGenerator (E1–E4)
  quality.py           response QA heuristics
  cells.py             run_cell, merge, blind CSV

Examples:
  python pipeline.py --epoch E3 --stimulus s01 --condition baseline
  python pipeline.py --epoch E3 --stimulus s01 --condition pipeline
  bash run_cells_one_by_one.sh E3
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cells import cell_path, export_blind_csv, load_stimuli, merge_results, run_cell
from emotion_analyzer import (
    GOEMOTIONS_MODEL,
    NEGATIVE_EMOTIONS,
    POSITIVE_EMOTIONS,
    TAU,
    EmotionAnalyzer,
    EmotionalContext,
)
from generator import (
    EPOCH_MODELS,
    MAX_NEW_TOKENS_LARGE,
    MAX_NEW_TOKENS_SMALL,
    SEED,
    TEMPERATURE,
    HFGenerator,
    free_memory,
    pick_device,
    pick_dtype,
    set_seed,
)
from prompts import build_contextual_prompt, build_direct_prompt
from quality import is_response_acceptable, response_quality_issues

# Re-exports for qa_and_regen.sh (`from pipeline import response_quality_issues`)
# and for callers that imported protocol symbols from this module.


__all__ = [
    "EPOCH_MODELS",
    "GOEMOTIONS_MODEL",
    "MAX_NEW_TOKENS_LARGE",
    "MAX_NEW_TOKENS_SMALL",
    "NEGATIVE_EMOTIONS",
    "POSITIVE_EMOTIONS",
    "SEED",
    "TAU",
    "TEMPERATURE",
    "EmotionAnalyzer",
    "EmotionalContext",
    "HFGenerator",
    "build_contextual_prompt",
    "build_direct_prompt",
    "cell_path",
    "export_blind_csv",
    "free_memory",
    "is_response_acceptable",
    "load_stimuli",
    "merge_results",
    "pick_device",
    "pick_dtype",
    "response_quality_issues",
    "run_cell",
    "set_seed",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HF ambivalent emotion pipeline (one cell at a time)"
    )
    parser.add_argument("--stimuli", type=Path, default=Path(__file__).with_name("stimuli.json"))
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path(__file__).with_name("outputs"),
        help="Scratch cells if regenerating. The evaluated 96-cell batch is ../data/all_results.json",
    )
    parser.add_argument("--epoch", type=str, default=None, help="Single epoch, e.g. E3")
    parser.add_argument("--epochs", nargs="*", default=None, help="Multiple epochs")
    parser.add_argument("--stimulus", type=str, default=None, help="Single stimulus id, e.g. s01")
    parser.add_argument(
        "--condition",
        type=str,
        choices=["baseline", "pipeline"],
        default=None,
        help="Single condition",
    )
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--no-skip-existing", action="store_false", dest="skip_existing")
    parser.add_argument(
        "--regen-bad",
        action="store_true",
        help="Overwrite cells whose response fails QA (empty/short/truncated)",
    )
    parser.add_argument(
        "--qa-only",
        action="store_true",
        help="Only audit existing outputs and print unsatisfactory cells",
    )
    parser.add_argument("--pause", type=float, default=2.0, help="Seconds to pause after each cell")
    parser.add_argument("--merge-only", action="store_true", help="Only rebuild all_results.json + CSV")
    parser.add_argument(
        "--filter-ambivalent-only",
        action="store_true",
        default=True,
    )
    parser.add_argument("--no-filter-ambivalent-only", action="store_false", dest="filter_ambivalent_only")
    args = parser.parse_args()

    set_seed(SEED)
    args.outdir.mkdir(parents=True, exist_ok=True)

    if args.merge_only:
        rows = merge_results(args.outdir)
        export_blind_csv(rows, args.outdir / "questionnaire_items.csv")
        print(f"Merged {len(rows)} cells")
        return

    if args.qa_only:
        bad = 0
        total = 0
        for path in sorted(args.outdir.glob("s*__E*__*.json")):
            total += 1
            try:
                row = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print(f"[bad-json] {path.name}")
                bad += 1
                continue
            issues = response_quality_issues(row.get("response", ""), epoch_id=row.get("epoch_id"))
            if issues:
                bad += 1
                prev = (row.get("response") or "")[:90].replace("\n", " ")
                print(f"[bad] {path.name}: {issues} | {prev!r}")
        print(f"\nQA: {bad}/{total} unsatisfactory")
        raise SystemExit(1 if bad else 0)

    # Resolve epoch list
    if args.epoch:
        epochs = [args.epoch]
    elif args.epochs:
        epochs = args.epochs
    else:
        epochs = list(EPOCH_MODELS.keys())

    for e in epochs:
        if e not in EPOCH_MODELS:
            raise SystemExit(f"Unknown epoch: {e}")

    # Warn if trying to run many large-model cells in one process
    large_epochs = [e for e in epochs if EPOCH_MODELS[e].get("large")]
    if large_epochs and args.stimulus is None and args.condition is None:
        print(
            "AVISO: modelos grandes (E3/E4) devem correr UMA célula por processo.\n"
            "Exemplo:\n"
            "  python pipeline.py --epoch E3 --stimulus s01 --condition baseline\n"
            "Ou:\n"
            "  bash run_cells_one_by_one.sh E3\n"
            "A continuar neste processo pode travar o macOS."
        )

    analyzer = EmotionAnalyzer()
    stimuli = load_stimuli(args.stimuli)

    kept: List[Dict[str, str]] = []
    for s in stimuli:
        analysis = analyzer.analyze(s["text"], tau=TAU)
        s["precheck_ambivalent"] = analysis["emotional_context"].ambivalent
        s["precheck_context"] = asdict(analysis["emotional_context"])
        if args.filter_ambivalent_only and not analysis["emotional_context"].ambivalent:
            print(f"[skip] {s['id']} not ambivalent under tau={TAU}")
            continue
        if args.stimulus and s["id"] != args.stimulus:
            continue
        kept.append(s)

    if not kept:
        raise SystemExit("No stimuli selected.")

    (args.outdir / "stimuli_precheck.json").write_text(
        json.dumps(stimuli, ensure_ascii=False, indent=2), encoding="utf-8")

    conditions = [args.condition] if args.condition else ["baseline", "pipeline"]

    for epoch_id in epochs:
        print(f"\n=== {epoch_id}: {EPOCH_MODELS[epoch_id]['model_id']} ===")
        generator = HFGenerator(epoch_id)
        try:
            for s in kept:
                for condition in conditions:
                    out = cell_path(args.outdir, s["id"], epoch_id, condition)
                    if out.exists() and args.skip_existing and not args.regen_bad:
                        print(f"  [exists] {out.name}")
                        continue
                    if out.exists() and args.regen_bad:
                        try:
                            old = json.loads(out.read_text(encoding="utf-8"))
                            old_issues = response_quality_issues(
                                old.get("response", ""), epoch_id=old.get("epoch_id", epoch_id)
                            )
                        except Exception:
                            old_issues = ["unreadable"]
                        if not old_issues:
                            print(f"  [qa-ok keep] {out.name}")
                            continue
                        print(f"  [qa-regen] {out.name}: {old_issues}", flush=True)
                        out.unlink(missing_ok=True)
                    print(f"  -> {s['id']} / {condition} ...", flush=True)
                    row = run_cell(analyzer, generator, s["id"], s["text"], condition)
                    out.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
                    preview = (row.get("response") or "")[:160].replace("\n", " ")
                    print(f"     OK ({len(row.get('response') or '')} chars): {preview}")
                    if args.pause > 0:
                        time.sleep(args.pause)
        finally:
            generator.close()
            free_memory(pick_device())
            print(f"=== unloaded {epoch_id} ===")

    rows = merge_results(args.outdir)
    export_blind_csv(rows, args.outdir / "questionnaire_items.csv")
    print(f"\nTotal cells on disk: {len(rows)}")


if __name__ == "__main__":
    main()
