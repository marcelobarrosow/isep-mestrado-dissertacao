#!/usr/bin/env python3
"""Modelo misto linear com RE cruzados (participante × item) — filtro estrito.

Usage:
  .venv/bin/python analyze_survey_mixed.py caminho/exportacao_questionario_....csv
  .venv/bin/python analyze_survey_mixed.py export.csv --json saida.json

Modelo principal (statsmodels crossed RE via grupo dummy + VC):
  score ~ C(condicao) * C(epoca) + (1|participante) + (1|item)
"""

from __future__ import annotations

import argparse
import csv
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.formula.api import mixedlm

COL_PARTICIPANT = "participante"
COL_ITEM = "código do item"
COL_SCORE = "classificação"
COL_ATT = "atenção"
COL_STATUS = "estado"
COL_EXCL = "motivo de exclusão"
COL_EPOCH = "época"
COL_COND = "condição"

ATT_YES = "Sim"
STATUS_DONE = "concluído"
EXCL_FAST = "ritmo demasiado rápido"
EXCL_ATT = "falha no item de atenção"

EPOCHS = ["E1", "E2", "E3", "E4"]


def load_strict(path: Path) -> pd.DataFrame:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    kept = []
    for r in rows:
        item = (r.get(COL_ITEM) or "").strip()
        score = (r.get(COL_SCORE) or "").strip()
        if not item or not score:
            continue
        if (r.get(COL_STATUS) or "").strip() != STATUS_DONE:
            continue
        if (r.get(COL_ATT) or "").strip() != ATT_YES:
            continue
        excl = (r.get(COL_EXCL) or "").strip()
        if excl in {EXCL_FAST, EXCL_ATT}:
            continue
        kept.append(
            {
                "participante": r[COL_PARTICIPANT],
                "item": item,
                "score": float(score),
                "epoca": r[COL_EPOCH],
                "condicao": "pipeline" if r[COL_COND] == "pipeline" else "baseline",
            }
        )
    df = pd.DataFrame(kept)
    df["epoca"] = pd.Categorical(df["epoca"], categories=EPOCHS, ordered=True)
    df["condicao"] = pd.Categorical(df["condicao"], categories=["baseline", "pipeline"])
    df["grp"] = 1
    return df


def _pack_result(res, formula: str) -> dict:
    return {
        "formula": formula,
        "converged": bool(res.converged),
        "params": {k: float(v) for k, v in res.params.items()},
        "pvalues": {k: float(v) for k, v in res.pvalues.items()},
        "conf_int": {
            k: [float(lo), float(hi)] for k, (lo, hi) in res.conf_int().iterrows()
        },
        "llf": float(res.llf),
    }


def _pipeline_effect_at_epoch(res, epoca: str) -> dict:
    """Marginal pipeline − baseline at a given epoch from interaction model.

    Design matrix treatment coding with baseline/E1 as reference:
      E1: β_pipe
      Ek: β_pipe + β_pipe:Ek
    """
    names = list(res.params.index)
    pipe = "C(condicao)[T.pipeline]"
    if pipe not in names:
        raise KeyError(pipe)

    coef = float(res.params[pipe])
    var = float(res.cov_params().loc[pipe, pipe])
    terms = [pipe]

    if epoca != "E1":
        inter = f"C(condicao)[T.pipeline]:C(epoca)[T.{epoca}]"
        if inter not in names:
            raise KeyError(inter)
        coef += float(res.params[inter])
        var += float(res.cov_params().loc[inter, inter])
        var += 2.0 * float(res.cov_params().loc[pipe, inter])
        terms.append(inter)

    se = float(np.sqrt(max(var, 0.0)))
    z = coef / se if se > 0 else float("nan")
    p = float(2 * stats.norm.sf(abs(z))) if se > 0 else float("nan")
    lo, hi = coef - 1.96 * se, coef + 1.96 * se
    return {
        "epoca": epoca,
        "delta": coef,
        "se": se,
        "z": float(z),
        "p": p,
        "ci95": [lo, hi],
        "terms": terms,
    }


def _interaction_omnibus(res) -> dict:
    """Wald test that all three condition×epoch interactions are zero."""
    names = [
        f"C(condicao)[T.pipeline]:C(epoca)[T.{e}]" for e in ("E2", "E3", "E4")
    ]
    R = np.zeros((3, len(res.params)))
    for i, n in enumerate(names):
        R[i, list(res.params.index).index(n)] = 1.0
    # statsmodels MixedLMResults.wald_test
    wt = res.wald_test(R, use_f=False, scalar=True)
    return {
        "statistic": float(np.asarray(wt.statistic).squeeze()),
        "df": 3,
        "p": float(np.asarray(wt.pvalue).squeeze()),
        "H0": "all condition×epoch interactions = 0",
    }


def fit_models(df: pd.DataFrame) -> dict:
    out: dict = {
        "n": len(df),
        "n_participants": int(df["participante"].nunique()),
        "n_items": int(df["item"].nunique()),
        "re_structure": "crossed: dummy group + VC(participante) + VC(item)",
    }

    formula_inter = "score ~ C(condicao) * C(epoca)"
    formula_add = "score ~ C(condicao) + C(epoca)"
    vc = {"participante": "0 + C(participante)", "item": "0 + C(item)"}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m_cross = mixedlm(formula_inter, df, groups=df["grp"], vc_formula=vc)
        r_cross = m_cross.fit(method="lbfgs", reml=True)

    packed = _pack_result(
        r_cross,
        "score ~ C(condicao)*C(epoca) + (1|participante) + (1|item)  [crossed]",
    )
    packed["epoch_pipeline_contrasts"] = [
        _pipeline_effect_at_epoch(r_cross, e) for e in EPOCHS
    ]
    packed["interaction_omnibus"] = _interaction_omnibus(r_cross)
    out["model_crossed"] = packed

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m_add = mixedlm(formula_add, df, groups=df["grp"], vc_formula=vc)
        r_add = m_add.fit(method="lbfgs", reml=True)
    out["model_additive_crossed"] = _pack_result(
        r_add,
        "score ~ C(condicao)+C(epoca) + (1|participante) + (1|item)  [crossed]",
    )

    # Participant-mean contrasts (descriptive companion)
    part_means = (
        df.groupby(["participante", "epoca", "condicao"], observed=True)["score"]
        .mean()
        .reset_index()
    )
    epoch_deltas = []
    for epoca in EPOCHS:
        wide = part_means[part_means["epoca"] == epoca].pivot(
            index="participante", columns="condicao", values="score"
        )
        if "baseline" not in wide.columns or "pipeline" not in wide.columns:
            continue
        both = wide.dropna()
        if len(both) < 3:
            b = wide["baseline"].dropna()
            p = wide["pipeline"].dropna()
            delta = float(p.mean() - b.mean()) if len(b) and len(p) else None
            if len(b) >= 2 and len(p) >= 2:
                t, pval = stats.ttest_ind(p, b, equal_var=False)
            else:
                t, pval = None, None
            epoch_deltas.append(
                {
                    "epoca": epoca,
                    "design": "unpaired_participant_means",
                    "n_baseline": int(len(b)),
                    "n_pipeline": int(len(p)),
                    "delta": delta,
                    "t": float(t) if t is not None else None,
                    "p": float(pval) if pval is not None else None,
                }
            )
        else:
            d = both["pipeline"] - both["baseline"]
            t, pval = stats.ttest_1samp(d, 0.0)
            epoch_deltas.append(
                {
                    "epoca": epoca,
                    "design": "paired_participant_means",
                    "n_pairs": int(len(both)),
                    "delta": float(d.mean()),
                    "sd_delta": float(d.std(ddof=1)),
                    "t": float(t),
                    "p": float(pval),
                }
            )
    out["participant_mean_contrasts"] = epoch_deltas
    return out


def print_report(summary: dict) -> None:
    print("=" * 72)
    print("MODELO MISTO CRUZADO — filtro estrito")
    print("=" * 72)
    print(
        f"n={summary['n']}  participantes={summary['n_participants']}  "
        f"itens={summary['n_items']}"
    )
    print(f"RE: {summary['re_structure']}")
    print()

    add = summary["model_additive_crossed"]
    print("Aditivo cruzado: score ~ condição + época + (1|p) + (1|item)")
    print(f"  converged={add['converged']}  llf={add['llf']:.1f}")
    for k, v in add["params"].items():
        if "Var" in k:
            continue
        p = add["pvalues"].get(k)
        ci = add["conf_int"].get(k, [None, None])
        print(f"  {k:55} coef={v:+.3f}  p={p:.4f}  IC95=[{ci[0]:+.3f}, {ci[1]:+.3f}]")
    print()

    cross = summary["model_crossed"]
    print("Interacção cruzada: score ~ condição * época + (1|p) + (1|item)")
    print(f"  converged={cross['converged']}  llf={cross['llf']:.1f}")
    omn = cross["interaction_omnibus"]
    print(
        f"  omnibus interacção: χ²({omn['df']})={omn['statistic']:.2f}  "
        f"p={omn['p']:.4f}"
    )
    print("  Contrastes pipeline−baseline por época (do misto):")
    for c in cross["epoch_pipeline_contrasts"]:
        lo, hi = c["ci95"]
        print(
            f"    {c['epoca']}  Δ={c['delta']:+.3f}  SE={c['se']:.3f}  "
            f"p={c['p']:.4f}  IC95=[{lo:+.3f}, {hi:+.3f}]"
        )
    print()
    print("Contrastes descritivos (médias por participante):")
    for d in summary["participant_mean_contrasts"]:
        print(
            f"  {d['epoca']}  design={d['design']}  Δ={d.get('delta'):+.3f}  "
            f"p={d.get('p')}"
        )
    print("=" * 72)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", type=Path)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()
    df = load_strict(args.csv_path)
    summary = fit_models(df)
    print_report(summary)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Escreveu {args.json}")


if __name__ == "__main__":
    main()
