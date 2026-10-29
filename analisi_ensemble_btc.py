#!/usr/bin/env python3
"""Analisi statistica NetLogo BehaviorSpace: Bitcoin, fase endogena.

Uso:
    python analisi_ensemble_btc.py
    python analisi_ensemble_btc.py --ensemble dati_bitcoin_ensemble.csv \
        --real dati_btc.csv --out risultati_analisi

L'analisi lavora su UNA configurazione di parametri (ensemble di ripetizioni).
Tutte le statistiche sono calcolate per ciascuna run, non sulla media dei prezzi.
"""
from __future__ import annotations

import argparse
import csv
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
except ImportError:
    acorr_ljungbox = None
    het_arch = None

METRICS = [
    ("sigma_r", "Deviazione standard dei log-rendimenti"),
    ("q99_abs_r", "Quantile 99% dei rendimenti assoluti"),
    ("acf_abs_r_1", "Autocorrelazione |r| a lag 1"),
    ("acf_abs_r_7", "Autocorrelazione |r| a lag 7"),
    ("mediana_log_v", "Mediana dei log-volumi"),
    ("sigma_log_v", "Deviazione standard dei log-volumi"),
    ("acf_log_v_1", "Autocorrelazione log-volumi a lag 1"),
    ("corr_log_v_abs_r", "Correlazione log-volumi e |r|"),
]
METRIC_NAMES = dict(METRICS)


def read_behaviorspace(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"CSV BehaviorSpace non trovato: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header_idx = next((i for i, line in enumerate(handle) if "[run number]" in line), None)
    if header_idx is None:
        raise ValueError("Non trovo '[run number]': usa Table output di BehaviorSpace.")
    df = pd.read_csv(path, skiprows=header_idx, low_memory=False)
    for required in ("[run number]", "model-price"):
        if required not in df.columns:
            raise ValueError(f"Manca la colonna obbligatoria {required!r}.")
    tick_col = "ticks" if "ticks" in df.columns else "[step]"
    if tick_col not in df.columns:
        raise ValueError("Mancano 'ticks' e '[step]' nel CSV.")
    df["run"] = pd.to_numeric(df["[run number]"], errors="coerce")
    df["tick"] = pd.to_numeric(df[tick_col], errors="coerce")
    cols_numeric = ["model-price", "model-trading-volume-usd", "model-trading-volume",
                    "real-trading-volume-usd", "btc-price", "trade-interval",
                    "tick-switch-fase", "model-return", "model-volatility",
                    "order-parameter", "current-hype", "total-bitcoin", "total-cash"]
    for col in cols_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["run", "tick", "model-price"]).copy()
    df["run"] = df["run"].astype(int)
    df["tick"] = df["tick"].astype(int)
    if df.duplicated(["run", "tick"]).any():
        raise ValueError("Presenti tick duplicati nella stessa run. Verifica l'esportazione.")
    if "current-disabled?" in df.columns:
        df["endogenous"] = (df["current-disabled?"].astype(str)
                            .str.strip().str.lower().eq("true"))
    elif "tick-switch-fase" in df.columns:
        df["endogenous"] = df["tick"] > df["tick-switch-fase"]
        print("AVVISO: 'current-disabled?' assente; fase endogena inferita da tick > tick-switch-fase.")
    else:
        raise ValueError("Esporta 'current-disabled?' oppure 'tick-switch-fase'.")
    return df.sort_values(["run", "tick"]).reset_index(drop=True)


def read_real(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"CSV reale non trovato: {path}")
    real = pd.read_csv(path)
    real.columns = [str(col).strip().lower() for col in real.columns]
    if not {"price", "volume"}.issubset(real.columns):
        raise ValueError("Il CSV dei dati reali deve avere colonne 'date,price,volume'.")
    for col in ("price", "volume"):
        real[col] = pd.to_numeric(real[col], errors="coerce")
    if real[["price", "volume"]].isna().any().any():
        raise ValueError("Dati reali con prezzo/volume mancante o non numerico.")
    if (real["price"] <= 0).any() or (real["volume"] < 0).any():
        raise ValueError("Sono presenti prezzi <= 0 o volumi < 0 nei dati reali.")
    if "date" in real.columns:
        dates = pd.to_datetime(real["date"], errors="coerce")
        if dates.isna().any() or not dates.is_monotonic_increasing or dates.duplicated().any():
            raise ValueError("La colonna delle date non è valida, crescente e univoca.")
        if not dates.diff().dropna().eq(pd.Timedelta(days=1)).all():
            warnings.warn("La serie reale non è strettamente giornaliera: controllare le lacune.")
    return real.reset_index(drop=True)


def acf(x: np.ndarray, lag: int) -> float:
    if len(x) <= lag + 2:
        return np.nan
    a, b = x[lag:], x[:-lag]
    if np.std(a) < 1e-14 or np.std(b) < 1e-14:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def metrics_from_pairs(r: np.ndarray, v_log: np.ndarray) -> dict:
    """Statistiche su rendimenti/log-volumi già allineati temporalmente."""
    r, v_log = np.asarray(r, dtype=float), np.asarray(v_log, dtype=float)
    if len(r) != len(v_log) or len(r) < 3:
        return {k: np.nan for k, _ in METRICS}
    if not np.isfinite(r).all() or not np.isfinite(v_log).all():
        return {k: np.nan for k, _ in METRICS}
    ar = np.abs(r)
    cor = float(np.corrcoef(v_log, ar)[0, 1]) if np.std(v_log) > 1e-14 and np.std(ar) > 1e-14 else np.nan
    return {
        "sigma_r": float(np.std(r, ddof=1)),
        "q99_abs_r": float(np.quantile(ar, 0.99)),
        "acf_abs_r_1": acf(ar, 1),
        "acf_abs_r_7": acf(ar, 7),
        "mediana_log_v": float(np.median(v_log)),
        "sigma_log_v": float(np.std(v_log, ddof=1)),
        "acf_log_v_1": acf(v_log, 1),
        "corr_log_v_abs_r": cor,
    }


def metrics_from_prices_volumes(prices: np.ndarray, volumes: np.ndarray | None,
                                volume_scale: float) -> tuple[dict, np.ndarray, np.ndarray | None]:
    prices = np.asarray(prices, dtype=float)
    if len(prices) < 4 or not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError("Prezzi insufficienti o non positivi nella fase analizzata.")
    r = np.diff(np.log(prices))
    if volumes is None:
        m = metrics_from_pairs(r, np.zeros_like(r))
        for k in ("mediana_log_v", "sigma_log_v", "acf_log_v_1", "corr_log_v_abs_r"):
            m[k] = np.nan
        return m, r, None
    volumes = np.asarray(volumes, dtype=float)
    if len(volumes) != len(prices) or not np.isfinite(volumes).all() or (volumes < 0).any():
        raise ValueError("Volumi simulati mancanti, negativi o non finiti.")
    v_log = np.log1p(volumes[1:] / volume_scale)
    return metrics_from_pairs(r, v_log), r, v_log


def paired_moving_block_bootstrap(r: np.ndarray, v: np.ndarray, n_boot: int,
                                  block_len: int, seed: int) -> pd.DataFrame:
    """Ricampiona congiuntamente coppie (r_t, logV_t) in blocchi sovrapposti."""
    n = len(r)
    if block_len > n or block_len < 2:
        raise ValueError("block_len deve essere compreso tra 2 e la lunghezza dei rendimenti.")
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block_len))
    offsets = np.arange(block_len, dtype=int)
    records = []
    for _ in range(n_boot):
        starts = rng.integers(0, n - block_len + 1, size=n_blocks)
        idx = (starts[:, None] + offsets[None, :]).ravel()[:n]
        records.append(metrics_from_pairs(r[idx], v[idx]))
    return pd.DataFrame.from_records(records)


def diagnostic_tests(r: np.ndarray, series_name: str, run_id: str,
                     max_lag: int = 10) -> dict:
    item = {"serie": series_name, "run": run_id, "n_rendimenti": len(r),
            "LB_r_p": np.nan, "LB_abs_r_p": np.nan, "ARCH_LM_p": np.nan}
    if acorr_ljungbox is None or het_arch is None or len(r) < max_lag * 3:
        return item
    try:
        item["LB_r_p"] = float(acorr_ljungbox(r, lags=[max_lag], return_df=True)["lb_pvalue"].iloc[0])
        item["LB_abs_r_p"] = float(acorr_ljungbox(np.abs(r), lags=[max_lag], return_df=True)["lb_pvalue"].iloc[0])
        item["ARCH_LM_p"] = float(het_arch(r - np.mean(r), nlags=max_lag)[1])
    except (ValueError, FloatingPointError, ZeroDivisionError):
        pass
    return item


def relative_drift(values: pd.Series) -> float:
    vals = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if len(vals) < 2 or abs(vals[0]) < 1e-12:
        return np.nan
    return float(np.max(np.abs(vals - vals[0])) / abs(vals[0]))


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Analisi statistica di ensemble BehaviorSpace Bitcoin")
    ap.add_argument("--ensemble", type=Path, default=here / "model/dati_bitcoin_ensemble.csv")
    ap.add_argument("--real", type=Path, default=here / "model/dati_btc.csv")
    ap.add_argument("--out", type=Path, default=here / "risultati_analisi")
    ap.add_argument("--bootstrap-reps", type=int, default=1000)
    ap.add_argument("--block-length", type=int, default=20)
    ap.add_argument("--volume-scale", type=float, default=1e9,
                    help="V_* in USD, identico per dati veri e simulati (default: 1 miliardo USD)")
    ap.add_argument("--burn-in-events", type=int, default=0,
                    help="Eventi endogeni iniziali da scartare, per ogni run")
    ap.add_argument("--seed", type=int, default=20261017)
    args = ap.parse_args()
    if args.volume_scale <= 0 or args.bootstrap_reps < 0 or args.burn_in_events < 0:
        ap.error("volume-scale deve essere > 0; bootstrap-reps e burn-in-events >= 0")
    args.out.mkdir(parents=True, exist_ok=True)
    df = read_behaviorspace(args.ensemble)
    real = read_real(args.real)
    ti = 1
    if "trade-interval" in df.columns:
        intervals = df["trade-interval"].dropna().unique()
        if len(intervals) != 1:
            raise ValueError("Il file contiene trade-interval differenti. Analizzare configurazioni separate.")
        ti = int(intervals[0])
    if ti < 1:
        raise ValueError("trade-interval deve essere >= 1")
    if "tick-switch-fase" in df.columns:
        sw = df["tick-switch-fase"].dropna().unique()
        if len(sw) > 1:
            raise ValueError("Il file contiene tick-switch-fase differenti: separare gli esperimenti.")
    if "scenario" in df.columns and not df["scenario"].astype(str).eq("csv").all():
        warnings.warn("'scenario' non è sempre 'csv': il confronto con dati_btc.csv potrebbe essere non valido.")
    if ti != 1:
        print(f"ATTENZIONE: trade-interval={ti}. Prezzi campionati ogni {ti} tick; "
              f"volumi reali sommati sugli ultimi {ti} giorni come convenzione di confronto.")
        print("Per confronti finanziari giornalieri rigorosi, usare trade-interval=1.")
    has_volume = "model-trading-volume-usd" in df.columns
    if not has_volume:
        print("AVVISO: esportazione precedente SENZA 'model-trading-volume-usd'. "
              "Si calcolano solo statistiche del prezzo. Rieseguire BehaviorSpace per tutti gli 8 indicatori.")

    # 'go' esegue il trading al valore ticks=0,1,... e chiama tick alla fine.
    # Nel CSV, un evento a ticks=k appare quindi nella misura finale tick=k+1.
    events = df[(df["tick"] > 0) & ((df["tick"] - 1) % ti == 0) & df["endogenous"]].copy()
    selected = {}
    for run_id, sub in events.groupby("run"):
        sub = sub.sort_values("tick").iloc[args.burn_in_events:].copy()
        if not sub.empty:
            selected[run_id] = sub
    if not selected:
        raise ValueError("Nessun evento endogeno. Controlla tick-switch-fase, time limit e le metriche.")
    # Allineamento su tick comuni: non mescoliamo serie di lunghezza o intervalli diversi.
    common = sorted(set.intersection(*(set(sub["tick"]) for sub in selected.values())))
    if len(common) < 4:
        raise ValueError("Meno di quattro osservazioni endogene comuni tra le run.")
    if any(len(sub) != len(common) for sub in selected.values()):
        print("AVVISO: durate disuguali tra le run; si analizza solo l'intersezione dei tick.")
    sample_tick = np.array(common, dtype=int)
    for rid in selected:
        selected[rid] = selected[rid].set_index("tick").loc[common].reset_index()
    # Allineamento dati reali: snapshot alla fine di 'go' con tick=t -> day index t-1,
    # per la versione del codice caricata (setup legge giorno 0; go salta update al tick 0).
    real_idx = sample_tick - 1
    if real_idx.max() >= len(real):
        raise ValueError(f"Dati reali insufficienti: richiesto indice {real_idx.max()}, disponibili {len(real)} giorni.")
    real_price = real["price"].to_numpy(dtype=float)[real_idx]
    vol_days = real["volume"].rolling(ti, min_periods=ti).sum().to_numpy(dtype=float)
    real_volume = vol_days[real_idx]
    if np.isnan(real_volume).any():
        raise ValueError("Serie reale troppo corta per sommare i volumi sugli intervalli.")
    real_stats, real_r, real_v = metrics_from_prices_volumes(real_price, real_volume, args.volume_scale)
    print(f"Run={len(selected)}; trade-interval={ti}; osservazioni endogene/run={len(common)}; "
          f"rendimenti/run={len(common)-1}; tick: {common[0]}..{common[-1]}")
    if len(real_r) < 200:
        print("AVVISO: meno di 200 rendimenti per run. Le stime di code e autocorrelazioni possono essere instabili.")

    run_records = []
    diags = [diagnostic_tests(real_r, "BTC reale", "reale")]
    all_model_prices = []
    all_model_volumes = []
    conservation = []
    for run_id, sub in selected.items():
        price = sub["model-price"].to_numpy(dtype=float)
        vol = sub["model-trading-volume-usd"].to_numpy(dtype=float) if has_volume else None
        stat, r, vlog = metrics_from_prices_volumes(price, vol, args.volume_scale)
        run_records.append({"run": run_id, "n_osservazioni": len(price), "n_rendimenti": len(r), **stat})
        diags.append(diagnostic_tests(r, "ABM", str(run_id)))
        all_model_prices.append(price)
        if has_volume:
            all_model_volumes.append(vol)
        full = df[df["run"] == run_id]
        conservation.append({"run": run_id,
                             "massima_variazione_relativa_btc": relative_drift(full["total-bitcoin"]) if "total-bitcoin" in df else np.nan,
                             "massima_variazione_relativa_cash": relative_drift(full["total-cash"]) if "total-cash" in df else np.nan})
    results = pd.DataFrame(run_records).sort_values("run")
    results.to_csv(args.out / "statistiche_per_run.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(diags).to_csv(args.out / "test_diagnostici.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(conservation).to_csv(args.out / "controlli_conservazione.csv", index=False, encoding="utf-8-sig")

    boot = None
    if args.bootstrap_reps > 0:
        bl = min(args.block_length, len(real_r))
        if bl < 2:
            raise ValueError("Troppo pochi dati per il bootstrap a blocchi.")
        boot = paired_moving_block_bootstrap(real_r, real_v, args.bootstrap_reps, bl, args.seed)
        boot.to_csv(args.out / "repliche_bootstrap_reali.csv", index=False, encoding="utf-8-sig")
    comparisons = []
    for k, descr in METRICS:
        vals = results[k].dropna().to_numpy(dtype=float)
        if len(vals):
            m = float(np.mean(vals))
            between_sd = float(np.std(vals, ddof=1)) if len(vals) >= 2 else np.nan
            lo, hi = np.quantile(vals, [0.025, 0.975])
        else:
            m = between_sd = lo = hi = np.nan
        bs = boot[k].dropna().to_numpy() if boot is not None else np.array([])
        se = float(np.std(bs, ddof=1)) if len(bs) > 1 else np.nan
        if len(bs):
            ci_lo, ci_hi = np.quantile(bs, [0.025, 0.975])
        else:
            ci_lo = ci_hi = np.nan
        comparisons.append({"statistica": k, "descrizione": descr,
                            "reale": real_stats[k], "se_reale_bootstrap": se,
                            "ic95_reale_inf": ci_lo, "ic95_reale_sup": ci_hi,
                            "abm_media": m, "abm_sd_tra_run": between_sd,
                            "abm_q025_run": lo, "abm_q975_run": hi,
                            "run_utilizzate": len(vals)})
    pd.DataFrame(comparisons).to_csv(args.out / "confronto_statistiche.csv", index=False, encoding="utf-8-sig")

    plt.figure(figsize=(10, 6))
    for p in all_model_prices:
        plt.plot(sample_tick, p, alpha=0.25, linewidth=0.8)
    plt.plot(sample_tick, np.mean(all_model_prices, axis=0), linewidth=2,
             label="Media dei prezzi simulati")
    plt.plot(sample_tick, real_price, linewidth=2, label="Prezzo reale (solo confronto)")
    plt.yscale("log")
    plt.ylabel("Prezzo BTC (USD) - scala logaritmica")
    plt.xlabel("Tick NetLogo (fine del passo)")
    plt.ylabel("Prezzo (USD)")
    plt.title("Ensemble: fase endogena, traiettorie e media")
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.out / "traiettorie_prezzi.png", dpi=160)
    plt.close()

    if has_volume:
        plt.figure(figsize=(10, 6))
        for v in all_model_volumes:
            plt.plot(sample_tick, np.log1p(v / args.volume_scale), alpha=0.20, linewidth=0.8)
        plt.plot(sample_tick, np.mean([np.log1p(v / args.volume_scale) for v in all_model_volumes], axis=0),
                 linewidth=2, label="Media dei log-volumi simulati")
        plt.plot(sample_tick, np.log1p(real_volume / args.volume_scale),
                 linewidth=2, label="Log-volume reale")
        plt.xlabel("Tick NetLogo (fine del passo)")
        plt.ylabel(f"log(1 + V/{args.volume_scale:g} USD)")
        plt.title("Volumi: simulazioni e dati reali (stessa aggregazione temporale)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(args.out / "traiettorie_log_volumi.png", dpi=160)
        plt.close()

    print("\nConfronto statistiche (NaN = colonna non esportata o statistica non definita):")
    show = pd.DataFrame(comparisons)[["statistica", "reale", "abm_media", "abm_sd_tra_run"]]
    print(show.to_string(index=False, float_format=lambda x: f"{x:.5g}"))
    print(f"\nFile salvati in: {args.out.resolve()}")
    if acorr_ljungbox is None:
        print("Per i test diagnostici Ljung-Box/ARCH-LM: pip install statsmodels")
    print("NOTA: il modello caricato conserva possibili dipendenze esogene (ATH e isteresi). "
          "I risultati sono esplorativi finché non vengono eliminate.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERRORE: {exc}", file=sys.stderr)
        sys.exit(1)
