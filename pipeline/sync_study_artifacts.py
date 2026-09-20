#!/usr/bin/env python3
"""Sync canonical cells in data/all_results.json to CSVs and, if present, the dissertation appendices.

Default dissertation paths are this repo's documento/ folder.
Use --skip-latex to refresh CSVs without rewriting appendixB.tex.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
DISSERTATION = REPO / "documento"
DEFAULT_RESULTS = REPO / "data" / "all_results.json"
DEFAULT_CACHE = REPO / "data" / "translation_cache.json"
DEFAULT_TEX = DISSERTATION / "appendices" / "appendixB.tex"
DEFAULT_JSON_COPY = DISSERTATION / "appendices" / "data" / "all_results.json"
DEFAULT_SITE_CSV = REPO / "site" / "data" / "questionnaire_items_i18n.csv"
DEFAULT_PIPELINE_CSV = REPO / "data" / "questionnaire_items.csv"
SEED = 42


def text_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def stable_item_id(stimulus_id: str, epoch_id: str, condition: str) -> str:
    return f"{stimulus_id}__{epoch_id}__{condition}"


def capitalize_start(text: str) -> str:
    """Normalize leading lowercase so display casing does not bias raters."""
    if not text:
        return text
    i = 0
    while i < len(text) and text[i].isspace():
        i += 1
    if i >= len(text):
        return text
    up = text[i].upper()
    if up == text[i]:
        return text
    return text[:i] + up + text[i + 1 :]


def load_cache(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def translate_batch(texts: list[str], cache: dict, do_translate: bool) -> list[str]:
    """Translate EN→PT with cache. Uses deep_translator when available."""
    out: list[str] = []
    missing: list[tuple[int, str, str]] = []
    for i, t in enumerate(texts):
        h = text_hash(t)
        if h in cache and cache[h].get("en") == t:
            out.append(cache[h]["pt"])
            continue
        # Legacy cache after leading-capital normalization
        if t and t[0].isupper():
            alt = t[0].lower() + t[1:]
            h_alt = text_hash(alt)
            if h_alt in cache and cache[h_alt].get("en") == alt:
                pt = capitalize_start(cache[h_alt]["pt"])
                out.append(pt)
                cache[h] = {"en": t, "pt": pt}
                continue
        out.append("")  # placeholder
        missing.append((i, t, h))

    if not missing:
        return out

    if not do_translate:
        for i, t, h in missing:
            out[i] = t  # fallback: keep EN
            cache[h] = {"en": t, "pt": t}
        return out

    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        print(
            "WARN: deep_translator not installed; PT fields copy EN. "
            "pip install deep-translator",
            file=sys.stderr,
        )
        for i, t, h in missing:
            out[i] = t
            cache[h] = {"en": t, "pt": t}
        return out

    translator = GoogleTranslator(source="en", target="pt")
    for i, t, h in missing:
        try:
            # Google has length limits; split long texts lightly
            if len(t) < 4500:
                pt = translator.translate(t)
            else:
                parts = re.split(r"(?<=[.!?])\s+", t)
                pt = " ".join(translator.translate(p) if p.strip() else p for p in parts)
            if not pt:
                pt = t
        except Exception as exc:  # noqa: BLE001
            print(f"WARN translate failed: {exc!r}; keeping EN", file=sys.stderr)
            pt = t
        out[i] = pt
        cache[h] = {"en": t, "pt": pt}
        print(f"  translated [{h}] ({len(t)} chars)")
    return out


def build_rows(results: list[dict]) -> list[dict]:
    rows = []
    for r in sorted(
        results,
        key=lambda x: (x["stimulus_id"], x["epoch_id"], x["condition"]),
    ):
        rows.append(
            {
                "item_id": stable_item_id(r["stimulus_id"], r["epoch_id"], r["condition"]),
                "stimulus_id": r["stimulus_id"],
                "user_message_en": capitalize_start((r.get("input") or "").strip()),
                "assistant_response_en": capitalize_start((r.get("response") or "").strip()),
                "epoch_id": r["epoch_id"],
                "model_id": r.get("model_id", ""),
                "condition": r["condition"],
            }
        )
    return rows


def write_csvs(rows: list[dict], site_csv: Path, pipeline_csv: Path) -> None:
    site_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "item_id",
        "stimulus_id",
        "user_message_en",
        "assistant_response_en",
        "user_message_pt",
        "assistant_response_pt",
        "epoch_id",
        "model_id",
        "condition",
    ]
    with site_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})

    # Blind questionnaire CSV (same order as site, plus shuffled presentation helper)
    shuffled = list(rows)
    random.Random(SEED).shuffle(shuffled)
    pipe_fields = [
        "item_id",
        "stimulus_id",
        "user_message",
        "assistant_response",
        "epoch_id",
        "model_id",
        "condition",
    ]
    pipeline_csv.parent.mkdir(parents=True, exist_ok=True)
    with pipeline_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pipe_fields)
        w.writeheader()
        for row in shuffled:
            w.writerow(
                {
                    "item_id": row["item_id"],
                    "stimulus_id": row["stimulus_id"],
                    "user_message": row["user_message_en"],
                    "assistant_response": row["assistant_response_en"],
                    "epoch_id": row["epoch_id"],
                    "model_id": row["model_id"],
                    "condition": row["condition"],
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--tex-out", type=Path, default=DEFAULT_TEX)
    parser.add_argument("--copy-json", type=Path, default=DEFAULT_JSON_COPY)
    parser.add_argument("--site-csv", type=Path, default=DEFAULT_SITE_CSV)
    parser.add_argument("--pipeline-csv", type=Path, default=DEFAULT_PIPELINE_CSV)
    parser.add_argument(
        "--translate-pt",
        action="store_true",
        help="Translate missing EN→PT via deep_translator (updates cache)",
    )
    parser.add_argument(
        "--skip-latex",
        action="store_true",
        help="Do not regenerate appendixB.tex",
    )
    args = parser.parse_args()

    results = json.loads(args.results.read_text(encoding="utf-8"))
    print(f"Loaded {len(results)} cells from {args.results}")

    if not args.skip_latex:
        # Reuse existing exporter
        from export_appendix_responses import build_tex

        args.tex_out.parent.mkdir(parents=True, exist_ok=True)
        args.tex_out.write_text(build_tex(results), encoding="utf-8")
        print(f"Wrote {args.tex_out}")
        if args.copy_json:
            args.copy_json.parent.mkdir(parents=True, exist_ok=True)
            args.copy_json.write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"Wrote {args.copy_json}")

    rows = build_rows(results)
    cache = load_cache(args.cache)

    user_ens = [r["user_message_en"] for r in rows]
    resp_ens = [r["assistant_response_en"] for r in rows]
    print("Resolving PT translations (cache + optional API)...")
    user_pts = translate_batch(user_ens, cache, do_translate=args.translate_pt)
    resp_pts = translate_batch(resp_ens, cache, do_translate=args.translate_pt)
    save_cache(args.cache, cache)

    for r, up, rp in zip(rows, user_pts, resp_pts):
        r["user_message_pt"] = capitalize_start(up)
        r["assistant_response_pt"] = capitalize_start(rp)

    write_csvs(rows, args.site_csv, args.pipeline_csv)
    print(f"Wrote {args.site_csv} ({len(rows)} items)")
    print(f"Wrote {args.pipeline_csv}")
    print("Done.")


if __name__ == "__main__":
    main()
