import os
import sys

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), "../../comsol_workflow"))
from run_manager import RunManager
from runtime_paths import ensure_directory, get_out_path, get_out_root, get_workspaces_path

def plot_heatmap(pivot_df, title, xlabel, ylabel, out_path, annot_series=None):
    pivot_df.index = pivot_df.index.astype(float)
    pivot_df.columns = pivot_df.columns.astype(float)
    pivot_df = pivot_df.sort_index(ascending=False)
    pivot_df = pivot_df.reindex(sorted(pivot_df.columns), axis=1)

    x = pivot_df.columns.to_numpy(dtype=float)
    y = pivot_df.index.to_numpy(dtype=float)
    data = pivot_df.to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(12, 8))
    im = ax.pcolormesh(x, y, data, cmap="viridis")
    fig.colorbar(im, ax=ax, label="log$_{10}$(Q)")

    if annot_series:
        for i, df_annot in enumerate(annot_series):
            if df_annot.empty:
                continue
            y_vals = df_annot[pivot_df.index.name].astype(float).to_numpy()
            x_vals = df_annot[pivot_df.columns.name].astype(float).to_numpy()
            order = np.argsort(y_vals)
            ax.plot(x_vals[order], y_vals[order], marker="o", markersize=4, linewidth=1.5, color="coral")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=500)
    plt.close(fig)
    print(f"Heatmap saved to {out_path}")

if __name__ == "__main__":
    out_dir = ensure_directory(get_out_root())

    sweep_save_path = get_workspaces_path("param_sweep_runs")
    sweep_file_name = "sweep_info"

    '''
    Step 1: Process sweep results to find best modes
    '''
    df = RunManager.get_records_df(sweep_save_path, sweep_file_name)
    df = df[df["___status"] == "done"].reset_index()
    
    best_modes = []
    for (r_f0, modulation), df_group in df.groupby(["r_f0", "modulation"]):
        label = f"r_f0={r_f0}, modulation={modulation}"
        print(f"[{label}]: {len(df_group)} runs")

        df_pos = df_group[~df_group["option"].str.startswith("-")]
        df_neg = df_group[df_group["option"].str.startswith("-")]

        best_pos = df_pos.loc[df_pos.groupby("b_square_f0")["q_p"].idxmax()].drop(columns="index")
        best_neg = df_neg.loc[df_neg.groupby("b_square_f0")["q_p"].idxmax()].drop(columns="index")

        best_pos = best_pos[best_pos["q_p"] > 1e6]
        best_neg = best_neg[best_neg["q_p"] > 1e6]

        best_modes.extend([best_pos, best_neg])

        # heatmap log_q_p vs (b_square_f0, option)
        pivot = df_group.pivot_table(
            index="b_square_f0",
            columns="option",
            values="log_q_p",
            dropna=False,
        )

        plot_heatmap(
            pivot,
            title=f"log10(Q) heatmap - {label}",
            xlabel="modulation value",
            ylabel="b_square_f0",
            out_path=os.path.join(out_dir, f"heatmap_logq_{modulation}_{r_f0}.png"),
        )

        plot_heatmap(
            pivot,
            title=f"log10(Q) heatmap - {label}",
            xlabel="modulation value",
            ylabel="b_square_f0",
            out_path=os.path.join(out_dir, f"heatmap_logq_{modulation}_{r_f0}_annotated.png"),
            annot_series=[best_pos, best_neg],
        )

        # xxx vs b_square_f0
        plot_specs = [
            ("log_q_p", "log10(Q)", f"logq_{modulation}_{r_f0}.png"),
            ("freq_p", "freq [THz]", f"freq_{modulation}_{r_f0}.png"),
        ]

        for col, ylabel, fname in plot_specs:
            fig, ax = plt.subplots(figsize=(8, 5))
            for sign_df, sign_label, color in [
                (best_pos, "modulation > 0", "tab:blue"),
                (best_neg, "modulation < 0", "tab:orange"),
            ]:
                if sign_df.empty:
                    continue
                x_vals = sign_df["b_square_f0"].to_numpy(dtype=float)
                y_vals = sign_df[col].astype(float).to_numpy()
                order = np.argsort(x_vals)
                ax.plot(x_vals[order], y_vals[order], marker="o", markersize=4, linewidth=1, label=sign_label, color=color)
            ax.set_xlabel("b_square_f0")
            ax.set_ylabel(ylabel)
            ax.set_title(f"{ylabel} - {label}")
            ax.legend()
            ax.grid(True, linestyle="--", alpha=0.5)
            fig.tight_layout()
            out_path = os.path.join(out_dir, fname)
            fig.savefig(out_path, dpi=500)
            plt.close(fig)
            print(f"{col} vs. b_square_f0 saved to {out_path}")

    # process best modes
    df_best = pd.concat(best_modes, ignore_index=True)
    df_best.to_csv(os.path.join(out_dir, "best_modes_summary.csv"), index=False)
    df_best.to_parquet(os.path.join(out_dir, "best_modes_summary.parquet"), index=False)

    # For each (r_f0, modulation) group, and each target frequency, find one
    # record from +modulation and one from -modulation whose freq_p is closest
    # to the target and within freq_tolerance THz.

    '''
    Step 2: From the best modes, find pairs of modes with similar frequencies but opposite modulation signs
    '''
    freq_tolerance = 0.5  # THz
    freq_lists = {
        "r-3":      list(range(180, 221, 5)) + [194],   # 180, 185, 190, 195, 200, 205, 210, 215, 220
        "theta-4":  list(range(180, 211, 2)),   # 180, 182, 184, ..., 210
    }
    df_best = pd.read_parquet(os.path.join(out_dir, "best_modes_summary.parquet"))
    df_best = df_best[df_best["q_p"] > 1e7].reset_index(drop=True)

    pair_records = []
    for (r_f0, modulation), df_group in df_best.groupby(["r_f0", "modulation"]):
        freq_list = freq_lists[modulation]

        df_pos = df_group[~df_group["option"].str.startswith("-")]
        df_neg = df_group[df_group["option"].str.startswith("-")]

        if df_pos.empty or df_neg.empty:
            continue
        current_pairs = []
        for target_freq in freq_list:
            diff_pos = (df_pos["freq_p"] - target_freq).abs()
            idx_pos = diff_pos.idxmin()
            if diff_pos[idx_pos] > freq_tolerance:
                continue

            diff_neg = (df_neg["freq_p"] - target_freq).abs()
            idx_neg = diff_neg.idxmin()
            if diff_neg[idx_neg] > freq_tolerance:
                continue

            row_pos = df_pos.loc[idx_pos].copy()
            row_neg = df_neg.loc[idx_neg].copy()

            row_pos["target_freq"] = target_freq
            row_neg["target_freq"] = target_freq

            current_pairs.append(row_pos)
            current_pairs.append(row_neg)
            pair_records.append(row_pos)
            pair_records.append(row_neg)

        label = f"modulation={modulation}, r_f0={r_f0}"
        col, ylabel, fname = ("freq_p", "freq [THz]", f"freq_{modulation}_{r_f0}_annotated.png")
        fig, ax = plt.subplots(figsize=(8, 5))
        for sign_df, sign_label, color in [
            (df_pos, "modulation > 0", "tab:blue"),
            (df_neg, "modulation < 0", "tab:orange"),
        ]:
            if sign_df.empty:
                continue
            x_vals = sign_df["b_square_f0"].to_numpy(dtype=float)
            y_vals = sign_df[col].astype(float).to_numpy()
            order = np.argsort(x_vals)
            ax.plot(x_vals[order], y_vals[order], marker="o", markersize=4, linewidth=1, label=sign_label, color=color, alpha=0.5)

        # Annotate target frequencies as horizontal dashed lines
        # for target_freq in freq_list:
        #     ax.axhline(y=target_freq, color="red", linestyle=":", linewidth=0.7, alpha=0.5)

        # Annotate matched pairs with star markers
        df_cp = pd.DataFrame(current_pairs)
        df_cp_pos = df_cp[~df_cp["option"].str.startswith("-")]
        df_cp_neg = df_cp[df_cp["option"].str.startswith("-")]
        for cp_df, color, mlabel in [
            (df_cp_pos, "tab:blue",   "matched (+)"),
            (df_cp_neg, "tab:orange", "matched (-)"),
        ]:
            if cp_df.empty:
                continue
            xs = cp_df["b_square_f0"].to_numpy(dtype=float)
            ys = cp_df[col].astype(float).to_numpy()
            ax.scatter(xs, ys, marker="*", s=100, color=color, label=mlabel)
            for x_pt, y_pt in zip(xs, ys):
                ax.annotate(
                    f"  ({x_pt:.4f}, {y_pt:.3f})",
                    xy=(x_pt, y_pt),
                    fontsize=6,
                    color="red",
                    va="bottom",
                    ha="left",
                )

        ax.set_xlabel("b_square_f0")
        ax.set_ylabel(ylabel)
        ax.set_title(f"{ylabel} - {label}")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)
        fig.tight_layout()
        out_path = os.path.join(out_dir, fname)
        fig.savefig(out_path, dpi=500)
        plt.close(fig)
        print(f"{col} vs. b_square_f0 saved to {out_path}")


    df_pairs = pd.DataFrame(pair_records)
    df_pairs.to_csv(get_out_path("matched_freq_pairs.csv"), index=False)
    df_pairs.to_parquet(get_out_path("matched_freq_pairs.parquet"), index=False)
