#!/usr/bin/env python3
"""Analisa o CSV de exportação do questionário (painel de administração).

Usage:
  python analyze_survey_export.py caminho/exportacao_questionario_YYYYMMDD_HHMMSS.csv
  python analyze_survey_export.py export.csv --filter estrito
  python analyze_survey_export.py export.csv --filter atencao --json saida.json

Filtros:
  estrito      — concluídos + atenção = Sim + sem motivo de exclusão
                 (ritmo demasiado rápido / falha no item de atenção)
                 [filtro principal da dissertação]
  atencao      — participantes com atenção = Sim (sensibilidade)
  concluidos   — estado = concluído e atenção = Sim
  todos        — todas as linhas com código do item e classificação

O filtro por omissão é estrito. Os nomes em inglês (all, attention_ok, completed,
strict) continuam a ser aceites como aliases.

O ritmo demasiado rápido é calculado na exportação (mediana por item, ritmo relativo
do participante, limiar mediana − 2,5 × DAM); ver site/lib/export_survey.php.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


EPOCHS = ("E1", "E2", "E3", "E4")
COND_BASE = "linha de base"
COND_PIPE = "pipeline"
CONDITIONS = (COND_BASE, COND_PIPE)

COL_PARTICIPANT = "participante"
COL_ITEM = "código do item"
COL_SCORE = "classificação"
COL_ATT = "atenção"
COL_STATUS = "estado"
COL_EXCL = "motivo de exclusão"
COL_EPOCH = "época"
COL_COND = "condição"
COL_LANG = "idioma"

ATT_YES = "Sim"
STATUS_DONE = "concluído"
EXCL_FAST = "ritmo demasiado rápido"
EXCL_ATT = "falha no item de atenção"
EXCL_NONE = "(nenhum)"

FILTER_ALIASES = {
    "all": "todos",
    "attention_ok": "atencao",
    "completed": "concluidos",
    "strict": "estrito",
    "todos": "todos",
    "atencao": "atencao",
    "atenção": "atencao",
    "concluidos": "concluidos",
    "estrito": "estrito",
}

FILTER_LABELS = {
    "todos": "todos",
    "atencao": "atenção",
    "concluidos": "concluídos",
    "estrito": "estrito",
}


@dataclass
class CellStats:
    epoch: str
    condition: str
    n: int
    mean: float | None
    median: float | None
    sd: float | None


@dataclass
class DeltaStats:
    epoch: str
    n_baseline: int
    n_pipeline: int
    mean_baseline: float | None
    mean_pipeline: float | None
    delta: float | None
    cohens_d: float | None = None
    p_mannwhitney: float | None = None
    p_welch: float | None = None


def cohens_d(a: list[float], b: list[float]) -> float | None:
    """d de Cohen para a − b com desvio-padrão agrupado."""
    if len(a) < 2 or len(b) < 2:
        return None
    na, nb = len(a), len(b)
    va, vb = statistics.variance(a), statistics.variance(b)
    pooled = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    if pooled == 0:
        return 0.0
    return (statistics.fmean(a) - statistics.fmean(b)) / pooled


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv_path", type=Path, help="CSV de exportação do questionário")
    p.add_argument(
        "--filter",
        default="estrito",
        help="Classificações a manter: estrito, atencao, concluidos, todos (omissão: estrito)",
    )
    p.add_argument("--json", type=Path, default=None, help="Ficheiro JSON opcional com o resumo")
    return p.parse_args()


def resolve_filter(raw: str) -> str:
    key = (raw or "").strip()
    filt = FILTER_ALIASES.get(key) or FILTER_ALIASES.get(key.lower())
    if filt is None:
        raise SystemExit(
            "Filtro desconhecido. Use: todos, atencao, concluidos, estrito "
            "(ou all, attention_ok, completed, strict)."
        )
    return filt


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def participants_meta(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    meta: dict[str, dict[str, str]] = {}
    for r in rows:
        pid = (r.get(COL_PARTICIPANT) or "").strip()
        if pid:
            meta[pid] = r
    return meta


def is_rating(r: dict[str, str]) -> bool:
    return bool((r.get(COL_ITEM) or "").strip()) and bool((r.get(COL_SCORE) or "").strip())


def keep_row(r: dict[str, str], filt: str) -> bool:
    if not is_rating(r):
        return False
    att = (r.get(COL_ATT) or "").strip()
    status = (r.get(COL_STATUS) or "").strip()
    excl = (r.get(COL_EXCL) or "").strip()
    if filt == "todos":
        return True
    if filt == "atencao":
        return att == ATT_YES
    if filt == "concluidos":
        return status == STATUS_DONE and att == ATT_YES
    if filt == "estrito":
        return status == STATUS_DONE and att == ATT_YES and excl not in {EXCL_FAST, EXCL_ATT}
    return False


def mean(xs: list[float]) -> float | None:
    return statistics.fmean(xs) if xs else None


def median(xs: list[float]) -> float | None:
    return statistics.median(xs) if xs else None


def sd(xs: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    return statistics.stdev(xs)


def welch_t_p(a: list[float], b: list[float]) -> float | None:
    """Valor p bilateral do teste t de Welch (aproximação normal se não houver SciPy)."""
    if len(a) < 2 or len(b) < 2:
        return None
    try:
        from scipy import stats  # type: ignore

        return float(stats.ttest_ind(a, b, equal_var=False, nan_policy="omit").pvalue)
    except Exception:
        ma, mb = statistics.fmean(a), statistics.fmean(b)
        va, vb = statistics.variance(a), statistics.variance(b)
        na, nb = len(a), len(b)
        se = math.sqrt(va / na + vb / nb)
        if se == 0:
            return None
        t = (ma - mb) / se
        p = math.erfc(abs(t) / math.sqrt(2))
        return float(p)


def mannwhitney_p(a: list[float], b: list[float]) -> float | None:
    if len(a) < 1 or len(b) < 1:
        return None
    try:
        from scipy import stats  # type: ignore

        return float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue)
    except Exception:
        return None


def cell_stats(scores: dict[tuple[str, str], list[float]]) -> list[CellStats]:
    out: list[CellStats] = []
    for e in EPOCHS:
        for c in CONDITIONS:
            xs = scores.get((e, c), [])
            out.append(
                CellStats(
                    epoch=e,
                    condition=c,
                    n=len(xs),
                    mean=mean(xs),
                    median=median(xs),
                    sd=sd(xs),
                )
            )
    return out


def delta_stats(scores: dict[tuple[str, str], list[float]]) -> list[DeltaStats]:
    out: list[DeltaStats] = []
    for e in EPOCHS:
        b = scores.get((e, COND_BASE), [])
        p = scores.get((e, COND_PIPE), [])
        mb, mp = mean(b), mean(p)
        d = (mp - mb) if (mb is not None and mp is not None) else None
        out.append(
            DeltaStats(
                epoch=e,
                n_baseline=len(b),
                n_pipeline=len(p),
                mean_baseline=mb,
                mean_pipeline=mp,
                delta=d,
                cohens_d=cohens_d(p, b) if b and p else None,
                p_mannwhitney=mannwhitney_p(b, p),
                p_welch=welch_t_p(b, p),
            )
        )
    return out


def fmt(x: float | None, digits: int = 2) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x:.{digits}f}"


def participant_summary(rows: list[dict[str, str]]) -> dict:
    meta = participants_meta(rows)
    status = Counter((m.get(COL_STATUS) or "") for m in meta.values())
    att = Counter((m.get(COL_ATT) or "NA") for m in meta.values())
    excl = Counter((m.get(COL_EXCL) or EXCL_NONE) for m in meta.values())
    lang = Counter((m.get(COL_LANG) or "") for m in meta.values())
    ratings_per: Counter[str] = Counter()
    for r in rows:
        if is_rating(r):
            ratings_per[r[COL_PARTICIPANT]] += 1
    return {
        "n_participants": len(meta),
        "status": dict(status),
        "attention": dict(att),
        "excluded_reason": dict(excl),
        "lang": dict(lang),
        "ratings_total": sum(1 for r in rows if is_rating(r)),
        "participants_with_ratings": sum(1 for n in ratings_per.values() if n > 0),
    }


def analyse(rows: list[dict[str, str]], filt: str) -> dict:
    kept = [r for r in rows if keep_row(r, filt)]
    scores: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in kept:
        scores[(r.get(COL_EPOCH) or "", r.get(COL_COND) or "")].append(float(r[COL_SCORE]))

    cells = cell_stats(scores)
    deltas = delta_stats(scores)

    by_epoch: dict[str, list[float]] = defaultdict(list)
    for (e, _c), xs in scores.items():
        by_epoch[e].extend(xs)

    pattern_hint = interpret_pattern(deltas)

    return {
        "filter": filt,
        "n_ratings": len(kept),
        "n_participants_in_filter": len({r[COL_PARTICIPANT] for r in kept}),
        "coverage": participant_summary(rows),
        "cells": [asdict(c) for c in cells],
        "deltas": [asdict(d) for d in deltas],
        "epoch_means_pooled": {e: mean(by_epoch.get(e, [])) for e in EPOCHS},
        "pattern_hint": pattern_hint,
        "notes": notes_for_filter(filt, rows),
    }


def notes_for_filter(filt: str, rows: list[dict[str, str]]) -> list[str]:
    notes = [
        "Análise alinhada à dissertação (exportação em português; filtro principal: estrito).",
        "Escala Likert 1–7; Δ = média(pipeline) − média(linha de base) em cada época.",
        "Os testes Welch são de amostras independentes ao nível do rating (descritivo/suplementar).",
        "O ritmo demasiado rápido é calculado na exportação: mediana do tempo por item, "
        "ritmo relativo do participante, e limiar robusto (mediana − 2,5 × desvio absoluto mediano). "
        "Não se usa um tempo fixo.",
    ]
    meta = participants_meta(rows)
    n_fast = sum(1 for m in meta.values() if (m.get(COL_EXCL) or "") == EXCL_FAST)
    n_att = sum(1 for m in meta.values() if (m.get(COL_ATT) or "") == ATT_YES)
    if n_fast and n_att and n_fast >= n_att:
        notes.append(
            "Aviso: quase todos os que passaram na atenção estão marcados como ritmo demasiado rápido. "
            "Convém rever a amostra e o limiar desta exportação."
        )
    if filt == "estrito":
        notes.append("O filtro estrito exclui falha no item de atenção e ritmo demasiado rápido.")
    return notes


def interpret_pattern(deltas: list[DeltaStats]) -> str:
    """Associa a forma aproximada de Δ aos padrões A/B/C da dissertação (só descritivo)."""
    vals = {d.epoch: d.delta for d in deltas if d.delta is not None}
    if len(vals) < 4:
        return "cobertura insuficiente para rotular o padrão"
    e1, e2, e3, e4 = vals["E1"], vals["E2"], vals["E3"], vals["E4"]
    early = (e1 + e2) / 2
    late = (e3 + e4) / 2
    if early > 0.3 and late < 0.2 and early > late:
        return "inclina para o padrão A (Δ maior nas épocas mais antigas) — provisório"
    if abs(e3) < 0.2 and abs(e4) < 0.2 and (e3 + e4) / 2 < early:
        return "Δ próximo de zero em E3/E4 (componente do padrão B) — provisório"
    if e3 < -0.3 or e1 < 0 and e2 > 0.4:
        return "não monótono / misto (candidato a padrão C) — provisório"
    return "misto / inconclusivo com o n actual — provisório"


def print_report(summary: dict) -> None:
    cov = summary["coverage"]
    print("=" * 72)
    print("EXPORTAÇÃO DO QUESTIONÁRIO — ANÁLISE")
    print("=" * 72)
    print(f"Filtro: {FILTER_LABELS.get(summary['filter'], summary['filter'])}")
    print(
        f"Classificações no filtro: {summary['n_ratings']}  |  "
        f"participantes: {summary['n_participants_in_filter']}"
    )
    print()
    print("Cobertura (todas as linhas do ficheiro)")
    print(f"  participantes: {cov['n_participants']}")
    print(f"  estado:        {cov['status']}")
    print(f"  atenção:       {cov['attention']}")
    print(f"  exclusão:      {cov['excluded_reason']}")
    print(f"  idioma:        {cov['lang']}")
    print(f"  classificações:{cov['ratings_total']}")
    print()
    print(f"{'Época':<6} {'Condição':<14} {'n':>5} {'média':>7} {'mediana':>7} {'dp':>7}")
    print("-" * 54)
    for c in summary["cells"]:
        print(
            f"{c['epoch']:<6} {c['condition']:<14} {c['n']:>5} "
            f"{fmt(c['mean']):>7} {fmt(c['median']):>7} {fmt(c['sd']):>7}"
        )
    print()
    print(
        f"{'Época':<6} {'n_base':>6} {'n_pipe':>6} {'méd_base':>8} {'méd_pipe':>8} "
        f"{'Δ':>7} {'d':>7} {'p_MW':>8} {'p_W':>8}"
    )
    print("-" * 78)
    for d in summary["deltas"]:
        print(
            f"{d['epoch']:<6} {d['n_baseline']:>6} {d['n_pipeline']:>6} "
            f"{fmt(d['mean_baseline']):>8} {fmt(d['mean_pipeline']):>8} {fmt(d['delta']):>7} "
            f"{fmt(d.get('cohens_d')):>7} "
            f"{fmt(d['p_mannwhitney'], 3):>8} {fmt(d['p_welch'], 3):>8}"
        )
    print()
    print("Média de empatia por época (condições juntas):")
    for e, m in summary["epoch_means_pooled"].items():
        print(f"  {e}: {fmt(m)}")
    print()
    print("Sugestão de padrão:", summary["pattern_hint"])
    print()
    print("Notas:")
    for n in summary["notes"]:
        print(f"  - {n}")
    print("=" * 72)


def main() -> None:
    args = parse_args()
    filt = resolve_filter(args.filter)
    rows = load_rows(args.csv_path)
    if not rows:
        raise SystemExit("O CSV está vazio.")
    if COL_PARTICIPANT not in rows[0]:
        raise SystemExit(
            "Este ficheiro não tem os cabeçalhos em português da exportação actual "
            "(coluna «participante» em falta)."
        )
    summary = analyse(rows, filt)
    print_report(summary)
    if filt == "estrito":
        print("\n(Comparação rápida com --filter atencao e --filter todos)")
        for name in ("atencao", "todos"):
            s_alt = analyse(rows, name)
            for d in s_alt["deltas"]:
                print(
                    f"  {name.upper():8} {d['epoch']}: Δ={fmt(d['delta'])} "
                    f"(n_base={d['n_baseline']}, n_pipe={d['n_pipeline']})"
                )
    if args.json:
        args.json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nEscreveu {args.json}")


if __name__ == "__main__":
    main()
