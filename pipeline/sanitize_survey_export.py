#!/usr/bin/env python3
"""Higieniza um export administrativo para o CSV público (IDs opacos, sem timestamps).

Usage:
  python sanitize_survey_export.py caminho/exportacao_questionario.csv \\
      --out data/classificacoes_publicas.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

DROP = {"início", "conclusão", "última actualização", "respondido em"}


def pid_key(x: str) -> tuple:
    try:
        return (0, int(x))
    except ValueError:
        return (1, x)


def sanitize(src: Path, dst: Path) -> dict:
    with src.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit("CSV sem cabeçalhos.")
        fieldnames = [c for c in reader.fieldnames if c not in DROP]
        rows = list(reader)

    pids: list[str] = []
    seen: set[str] = set()
    for r in rows:
        pid = (r.get("participante") or "").strip()
        if pid and pid not in seen:
            seen.add(pid)
            pids.append(pid)
    mapping = {p: f"P{i:03d}" for i, p in enumerate(sorted(pids, key=pid_key), start=1)}

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            out = {c: r.get(c, "") for c in fieldnames}
            out["participante"] = mapping.get((r.get("participante") or "").strip(), "")
            writer.writerow(out)
    return {"n_rows": len(rows), "n_participants": len(mapping), "path": str(dst)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    info = sanitize(args.csv_path, args.out)
    print(f"Escreveu {info['path']} ({info['n_rows']} linhas, {info['n_participants']} participantes)")


if __name__ == "__main__":
    main()
