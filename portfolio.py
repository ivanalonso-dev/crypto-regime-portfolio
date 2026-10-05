#!/usr/bin/env python3
"""
crypto-regime-portfolio · cartera combinada de los proyectos 006, 007 y 008

No añade reglas de trading nuevas: combina los sistemas ya validados para usar el
capital que cada uno deja parado.

CARTERA (pre-registrada)
------------------------
Núcleo  60%  BTC según el régimen del 006:
             ALCISTA (fuerte o débil) -> BTC
             NO ALCISTA               -> S2 del 008 (BTC si entró con MVRV < 1 y sigue
                                         en NO ALCISTA); si no, liquidez
Satélite 40% sistema 007 v2 (solo tendencia), riesgo 1% por operación, 19 monedas.
Liquidez     la parte parada de ambos bloques rinde 4% anual (stablecoin / letras);
             también se muestra con 0%.
Rebalanceo   mensual al 60/40, coste 0,10% sobre el importe movido. BTC: 0,10% por cambio.
Periodo      2017-08-17 -> hoy. IS < 2023-01-01 <= OOS.
Criterio     se adopta si su Calmar supera al del 006 solo (BTC en alcista, liquidez al
             0% en el resto) en TOTAL y en OOS, con drawdown máximo mejor que -35%.
Sensibilidad 80/20 y 40/60 (solo informativas, no se elige entre ellas).

Uso:
    python portfolio.py
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def find(prefix: str) -> str:
    for name in os.listdir(ROOT):
        if name.upper().startswith(prefix):
            return os.path.join(ROOT, name)
    raise SystemExit(f"No encuentro la carpeta del proyecto {prefix} junto a esta.")


P006, P007, P008 = find("006"), find("007"), find("008")
sys.path.insert(0, P007)
sys.path.insert(0, P008)
import bull_system as bs  # noqa: E402  (proyecto 007)
import bear_system as br  # noqa: E402  (proyecto 008)

YEAR = 365
START, SPLIT = "2017-08-17", "2023-01-01"
FEE = 0.10 / 100


def daily_yield(pct: float) -> float:
    return (1 + pct / 100) ** (1 / YEAR) - 1


def core_returns(btc006: pd.DataFrame, states: pd.Series, dates: pd.DatetimeIndex,
                 yield_pct: float, use_s2: bool = True) -> tuple[pd.Series, pd.Series]:
    """Rentabilidad diaria del núcleo y su posición en BTC (0/1)."""
    px = btc006["price"].reindex(dates).ffill()
    st = states.reindex(dates).ffill(limit=3)
    bull = (st >= 1).astype(float)
    hold = bull.copy()
    if use_s2:
        s2 = br.s2_hold(btc006, states).reindex(dates).fillna(0)
        hold = ((bull == 1) | (s2 == 1)).astype(float)
    pos = hold.shift(1).fillna(0)
    r = px.pct_change().fillna(0)
    ret = pos * r + (1 - pos) * daily_yield(yield_pct) - pos.diff().abs().fillna(pos) * FEE
    return ret, hold


def satellite_returns(coins, states, risk: float, yield_pct: float) -> tuple[pd.Series, pd.Series, dict]:
    out: dict = {}
    eq, tr, expo, dates, st = bs.backtest(coins, states, replace(bs.VERSIONS["v2"], risk_pct=risk),
                                          state_out=out)
    r = eq.pct_change().fillna(0)
    r = r + (1 - expo.shift(1).fillna(0)).clip(0, 1) * daily_yield(yield_pct)
    return r, expo, out


def combine(r_core: pd.Series, r_sat: pd.Series, w_core: float) -> pd.Series:
    """Rebalanceo mensual a los pesos objetivo, coste sobre el importe movido."""
    a, b = w_core, 1 - w_core
    vals = []
    month = None
    for d, rc, rs in zip(r_core.index, r_core.values, r_sat.values):
        if month is not None and d.month != month:
            tot = a + b
            turnover = abs(a - w_core * tot)
            a, b = w_core * tot, (1 - w_core) * tot
            a -= turnover * FEE / 2
            b -= turnover * FEE / 2
        month = d.month
        a *= 1 + rc
        b *= 1 + rs
        vals.append(a + b)
    return pd.Series(vals, index=r_core.index)


def perf(eq: pd.Series) -> dict:
    eq = eq.dropna()
    r = eq.pct_change().fillna(0)
    yrs = len(eq) / YEAR
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    vol = r.std() * np.sqrt(YEAR)
    return {"CAGR_%": 100 * cagr, "maxDD_%": 100 * dd,
            "Sharpe": r.mean() * YEAR / vol if vol > 0 else np.nan,
            "Calmar": cagr / abs(dd) if dd < 0 else np.nan}


def segments(eq: pd.Series) -> dict:
    out = {}
    for tag, lo, hi in [("TOTAL", START, None), ("IS", START, SPLIT), ("OOS", SPLIT, None)]:
        e = eq[(eq.index >= lo) & ((eq.index < hi) if hi else True)]
        for k, v in perf(e).items():
            out[f"{tag} {k}"] = round(v, 2)
    return out


def main():
    ap = argparse.ArgumentParser(description="Cartera combinada 006 + 007 + 008")
    ap.add_argument("--yield-pct", type=float, default=4.0)
    ap.add_argument("--risk", type=float, default=1.0)
    ap.add_argument("--out", default="resultados")
    a = ap.parse_args()

    states = bs.load_states(os.path.join(P006, "resultados", "estados_oficiales.csv"))
    btc006 = br.load_btc006(os.path.join(P006, "data", "btc_daily.csv"))
    coins = {}
    for sub in ["data", "data_val"]:
        coins.update(bs.load_coins(os.path.join(P007, sub)))
    print(f"Núcleo: BTC 006 ({btc006.index[0].date()} -> {btc006.index[-1].date()}) · "
          f"Satélite: {len(coins)} monedas del 007")

    curves = {}
    for y in [a.yield_pct, 0.0]:
        r_sat, expo, state = satellite_returns(coins, states, a.risk, y)
        dates = r_sat.index[r_sat.index >= START]
        r_sat = r_sat.reindex(dates)
        r_core, hold = core_returns(btc006, states, dates, y)
        tag = f"liquidez {y:g}%"
        curves[f"CARTERA 60/40 · {tag}"] = combine(r_core, r_sat, 0.60)
        if y == a.yield_pct:
            curves[f"Sensibilidad 80/20 · {tag}"] = combine(r_core, r_sat, 0.80)
            curves[f"Sensibilidad 40/60 · {tag}"] = combine(r_core, r_sat, 0.40)
            curves[f"Solo núcleo (006 + S2) · {tag}"] = (1 + r_core).cumprod()
            curves[f"Solo satélite (007 v2 {a.risk}%) · {tag}"] = (1 + r_sat).cumprod()
            today = {"fecha": dates[-1].date(), "hold_btc": int(hold.iloc[-1]),
                     "estado": states.reindex(dates).ffill().iloc[-1], "sat": state}
    r_006, _ = core_returns(btc006, states, dates, 0.0, use_s2=False)
    curves["REF · 006 solo (BTC en alcista, liquidez 0%)"] = (1 + r_006).cumprod()
    px = btc006["price"].reindex(dates).ffill()
    curves["REF · Comprar y mantener BTC"] = px / px.iloc[0]

    table = pd.DataFrame({k: segments(v) for k, v in curves.items()}).T
    yearly = pd.DataFrame({k: (v.resample("YE").last().pct_change()
                               .fillna(v.resample("YE").last().iloc[0] / v.iloc[0] - 1) * 100).round(1)
                           for k, v in curves.items()})
    yearly.index = yearly.index.year

    main_key = f"CARTERA 60/40 · liquidez {a.yield_pct:g}%"
    ref = table.loc["REF · 006 solo (BTC en alcista, liquidez 0%)"]
    m = table.loc[main_key]
    crit = [
        ("Calmar TOTAL > 006 solo", m["TOTAL Calmar"] > ref["TOTAL Calmar"], f"{m['TOTAL Calmar']} vs {ref['TOTAL Calmar']}"),
        ("Calmar OOS > 006 solo", m["OOS Calmar"] > ref["OOS Calmar"], f"{m['OOS Calmar']} vs {ref['OOS Calmar']}"),
        ("Drawdown máximo mejor que -35%", m["TOTAL maxDD_%"] > -35, f"{m['TOTAL maxDD_%']}%"),
    ]
    adopt = all(c[1] for c in crit)

    os.makedirs(a.out, exist_ok=True)
    table.to_csv(os.path.join(a.out, "metricas.csv"))
    yearly.to_csv(os.path.join(a.out, "por_año.csv"))
    pd.DataFrame({k: v for k, v in curves.items()}).to_csv(os.path.join(a.out, "curvas.csv"))
    _plot(curves, main_key, os.path.join(a.out, "equity.png"))

    with pd.option_context("display.width", 260, "display.max_columns", 30, "display.max_colwidth", 50):
        print(f"\n=== CARTERAS (IS < {SPLIT} <= OOS) ===")
        print(table[["TOTAL CAGR_%", "TOTAL maxDD_%", "TOTAL Sharpe", "TOTAL Calmar",
                     "IS Calmar", "OOS CAGR_%", "OOS maxDD_%", "OOS Calmar"]].to_string())
        print("\n=== RENTABILIDAD POR AÑO (%) ===")
        cols = [main_key, "REF · 006 solo (BTC en alcista, liquidez 0%)", "REF · Comprar y mantener BTC"]
        print(yearly[cols].to_string())
    print("\n=== CRITERIO PRE-REGISTRADO ===")
    for name, ok, det in crit:
        print(f"  [{'CUMPLE' if ok else 'NO    '}] {name}: {det}")
    fails = [c[0] for c in crit if not c[1]]
    print(f"  -> Cartera 60/40: {'SE ADOPTA' if adopt else 'NO se adopta. Falla: ' + '; '.join(fails)}")

    names = {2: "ALCISTA FUERTE", 1: "ALCISTA DÉBIL / LATERAL", 0: "NO ALCISTA"}
    sat = today["sat"]
    n_pos = len(sat["pos"])
    expo_now = sum(q["qty"] * sat["close"][j] for j, q in sat["pos"].items()) / sat["equity"]
    print(f"\n=== ASIGNACIÓN DE HOY ({today['fecha']}) · régimen {names.get(int(today['estado']), 'n/d')} ===")
    print(f"  Núcleo 60%:   {'BTC' if today['hold_btc'] else 'liquidez'}")
    print(f"  Satélite 40%: {n_pos} posiciones del 007 ({100 * expo_now:.0f}% del satélite invertido, "
          f"resto en liquidez); detalle en ../007/registro/posiciones_v2.csv")
    print(f"\nFicheros en ./{a.out}/")


def _plot(curves: dict, main_key: str, path: str):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    keep = [main_key, "REF · 006 solo (BTC en alcista, liquidez 0%)", "REF · Comprar y mantener BTC"]
    colors = ["#2a78d6", "#eb6834", "#1baf7a"]
    fig, ax = plt.subplots(figsize=(11, 5))
    for k, c in zip(keep, colors):
        ax.plot(curves[k].index, curves[k].values, label=k, color=c, lw=1.8)
    ax.axvline(pd.Timestamp(SPLIT), color="#52514e", ls="--", lw=1)
    ax.set_yscale("log")
    ax.set_title("Capital multiplicado (escala log, neto de costes) · línea discontinua = inicio OOS")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


if __name__ == "__main__":
    main()
