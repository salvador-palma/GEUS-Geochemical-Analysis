"""Builds every figure in the report from the cached results in Results/.

Two entry points, one implementation, so the report and the notebook cannot drift apart:

    python Report/make_figures.py          # from the repository root
    `4. Results.ipynb`, final section      # imports this module and displays them inline

Each Figure* function saves its PNG under ROOT/Report/figures and returns the Matplotlib
figure, so a caller that wants it on screen can display it before closing.
"""

import json
import sys
from pathlib import Path

#GreenlandUtils lives at the repository root, not beside this script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from GreenlandUtils import BASEMAP_BBOX, BASEMAP_PATH, lonlatToUTM24N

#Repository root. Defaults to the working directory, which is what running from the repo
#root or from a notebook beside it gives; a Colab session points it at the Drive mirror.
ROOT = Path(".")


def ResultsDir():
    return ROOT / "Results"


def DataDir(dataset):
    return ROOT / "Data" / dataset / "Mean Merge"


def FiguresDir():
    path = ROOT / "Report" / "figures"
    path.mkdir(parents=True, exist_ok=True)
    return path


DATASETS = ["Whole Rock", "Stream Sediment"]
LABELS = {"Whole Rock": "Whole rock", "Stream Sediment": "Stream sediment"}

#One palette for the whole report, so a colour means the same thing in every figure
CHEM, NEIGH, GEO, LOC = "#3a3a38", "#2f7d5c", "#b4553a", "#3f6ea8"
GRID, TEXT = "#d9d8d2", "#1a1a19"

mpl.rcParams.update({
    "figure.dpi": 200,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.edgecolor": "#8d8c85",
    "axes.linewidth": 0.7,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "legend.frameon": False,
    "text.color": TEXT,
    "axes.labelcolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
})


def LoadResults(dataset, name):
    path = ResultsDir() / dataset / "Mean Merge" / f"{name}.json"
    return json.loads(path.read_text()) if path.exists() else None


def MeanR2(result):
    return float(np.mean([v["r2"] for v in result.values()]))


def MeanFoldStd(result):
    return float(np.mean([v["r2_std"] for v in result.values()]))


# ------------------------------------------------------------ 1. sampling maps

def FigureSamples():
    """The sampling-geometry contrast that motivates using two datasets."""

    fig, axes = plt.subplots(1, 2, figsize=(5.4, 4.4))
    fig.subplots_adjust(wspace=0.02)
    basemap = plt.imread(BASEMAP_PATH)
    minx, miny, maxx, maxy = BASEMAP_BBOX

    for ax, dataset, colour in zip(axes, DATASETS, [GEO, NEIGH]):
        df = pd.read_csv(DataDir(dataset) / "Data.csv", sep=";",
                         usecols=["Longitude", "Latitude"]).dropna()
        x, y = lonlatToUTM24N(df["Longitude"].to_numpy(), df["Latitude"].to_numpy())

        ax.imshow(basemap, extent=(minx, maxx, miny, maxy), origin="upper",
                  interpolation="bilinear", zorder=0)
        ax.scatter(x, y, s=1.4, c=colour, alpha=0.5, linewidths=0, zorder=2)

        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        ax.set_aspect("equal")
        ax.set_title(f"{LABELS[dataset]}\n{len(df):,} samples", loc="center", fontsize=9)
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])

    fig.savefig(FiguresDir() / "samples.png")
    return fig


# ------------------------------------------------------------------ 2. k-sweep

KS = [1, 3, 5, 10, 20, 50, 100]


def FigureKSweep():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9), sharey=True)

    for ax, dataset, panel in zip(axes, DATASETS, ["(a)", "(b)"]):
        baseline = LoadResults(dataset, "HistGradientBoosting_KFold")
        base, noise = MeanR2(baseline), MeanFoldStd(baseline)

        ax.axhspan(-noise, noise, color=GRID, alpha=0.55, lw=0, zorder=0)
        ax.axhline(0, color="#8d8c85", lw=0.7, zorder=1)

        for variant, colour, style in [("A", LOC, "--"), ("C", NEIGH, "-"), ("D", GEO, "-")]:
            deltas = [MeanR2(LoadResults(dataset, f"K-Sweep_{k}_{variant}")) - base for k in KS]
            ax.plot(range(len(KS)), deltas, style, color=colour, marker="o", ms=3.4,
                    lw=1.4, label=f"Variant {variant}", zorder=3)

        ax.set_xticks(range(len(KS)), [str(k) for k in KS])
        ax.set_xlabel("$k$ (neighbours)")
        ax.set_title(f"{panel} {LABELS[dataset]}", loc="left")

    axes[0].set_ylabel(r"$\Delta$ mean $R^2$")
    axes[0].legend(loc="upper left", fontsize=8)
    fig.savefig(FiguresDir() / "ksweep.png")
    return fig


# --------------------------------------------------------------- 3. difficulty

BINS = [(-9.0, 0.70, "$<0.70$"), (0.70, 0.85, "0.70-0.85"),
        (0.85, 0.95, "0.85-0.95"), (0.95, 9.0, "$>0.95$")]

ARMS = [("+ neighbours", NEIGH), ("+ coordinates", LOC), ("+ geophysics", GEO)]


def Stratify(dataset):
    baseline = LoadResults(dataset, "HistGradientBoosting_KFold_Cov1000")
    arms = {
        "+ neighbours": LoadResults(dataset, "HistGradientBoosting_KFold_KNN_C_ExcludingColocation_Cov1000"),
        "+ coordinates": LoadResults(dataset, "HistGradientBoosting_KFold_FeatureSet_Chemistry_Location_Cov1000"),
        "+ geophysics": LoadResults(dataset, "HistGradientBoosting_KFold_FeatureSet_Chemistry_Physics_Cov1000"),
    }

    rows = []
    for low, high, label in BINS:
        targets = [e for e in baseline if low <= baseline[e]["r2"] < high]
        rows.append({
            "label": label,
            "n": len(targets),
            "baseline": float(np.mean([baseline[e]["r2"] for e in targets])),
            **{name: float(np.mean([arm[e]["r2"] - baseline[e]["r2"] for e in targets]))
               for name, arm in arms.items()},
        })
    return rows


def FigureDifficulty():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0), sharey=True)

    for ax, dataset, panel in zip(axes, DATASETS, ["(a)", "(b)"]):
        rows = Stratify(dataset)
        positions = np.arange(len(rows))

        for offset, (name, colour) in enumerate(ARMS):
            ax.bar(positions + (offset - 1) * 0.27, [r[name] for r in rows], 0.25,
                   color=colour, label=name, zorder=3)

        ax.set_xticks(positions, [f"{r['label']}\n$n={r['n']}$" for r in rows], fontsize=7.5)
        ax.set_xlabel("Baseline $R^2$ of the target element")
        ax.set_title(f"{panel} {LABELS[dataset]}", loc="left")
        ax.set_axisbelow(True)
        ax.xaxis.grid(False)

    axes[0].set_ylabel(r"Mean $\Delta R^2$ over own chemistry")
    axes[0].legend(fontsize=8)
    fig.savefig(FiguresDir() / "difficulty.png")
    return fig


# ------------------------------------------------------------- 4. feature sets

FEATURESETS = [
    ("Chemistry", "Chemistry", CHEM),
    ("Neighbours", "Neighbours", NEIGH),
    ("Coordinates", "Location", LOC),
    ("Geophysics", "Physics", GEO),
    ("Chemistry + neighbours", None, NEIGH),
    ("Chemistry + coordinates", "Chemistry_Location", LOC),
    ("Chemistry + geophysics", "Chemistry_Physics", GEO),
]


def FeatureSetScores(dataset):
    scores = []
    for _, key, _ in FEATURESETS:
        if key is None:
            result = LoadResults(dataset, "HistGradientBoosting_KFold_KNN_C_ExcludingColocation_Cov1000")
        else:
            result = LoadResults(dataset, f"HistGradientBoosting_KFold_FeatureSet_{key}_Cov1000")
        scores.append(MeanR2(result))
    return scores


def FigureFeatureSets():
    fig, ax = plt.subplots(figsize=(7.0, 3.3))
    positions = np.arange(len(FEATURESETS))
    colours = [c for _, _, c in FEATURESETS]

    #Colour encodes the feature source; opacity encodes the dataset
    for dataset, offset, alpha in [(DATASETS[0], -0.20, 1.0), (DATASETS[1], 0.20, 0.42)]:
        scores = FeatureSetScores(dataset)
        ax.barh(positions + offset, scores, 0.36, color=colours, alpha=alpha, zorder=3)
        for position, score in zip(positions + offset, scores):
            ax.text(score + 0.008, position, f"{score:.3f}", va="center", fontsize=7.2)

    handles = [mpl.patches.Patch(facecolor="#6b6b68", alpha=alpha, label=LABELS[dataset])
               for dataset, alpha in [(DATASETS[0], 1.0), (DATASETS[1], 0.42)]]
    #Parked over the whitespace left by the three spatial-only rows
    ax.legend(handles=handles, loc="center right", bbox_to_anchor=(0.995, 0.63), fontsize=8)

    ax.set_yticks(positions, [name for name, _, _ in FEATURESETS])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Mean $R^2$ over target elements")
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)
    fig.savefig(FiguresDir() / "featuresets.png")
    return fig


# ---------------------------------------------------------------------- 5. GNN

def FigureGNN():
    fig, ax = plt.subplots(figsize=(5.2, 3.1))
    dataset = "Stream Sediment"
    base = MeanR2(LoadResults(dataset, "HistGradientBoosting_KFold"))

    series = [
        ("Variant C (pooled columns)", [MeanR2(LoadResults(dataset, f"K-Sweep_{k}_C")) for k in KS], NEIGH),
        ("GNN, SAGE (distance-blind)", [MeanR2(LoadResults(dataset, f"GNN_SAGE_KFold_k{k}")) for k in KS], LOC),
        ("GNN, GAT (distance-aware)", [MeanR2(LoadResults(dataset, f"GNN_GAT_KFold_k{k}")) for k in KS], GEO),
    ]
    for label, values, colour in series:
        ax.plot(range(len(KS)), values, color=colour, marker="o", ms=3.4, lw=1.4,
                label=label, zorder=3)

    ax.axhline(base, color=CHEM, lw=1.0, ls=":", zorder=2)
    ax.text(0.05, base + 0.0007, "own chemistry only", fontsize=7.5, color=CHEM)

    ax.set_xticks(range(len(KS)), [str(k) for k in KS])
    #Headroom below the baseline line so the legend sits on empty canvas
    ax.set_ylim(0.7845, None)
    ax.set_xlabel("$k$ (neighbours)")
    ax.set_ylabel("Mean $R^2$")
    ax.legend(loc="lower right", fontsize=8)
    fig.savefig(FiguresDir() / "gnn.png")
    return fig


# --------------------------------------------------------------- 6. isolation

#Elements to name on the scatter, chosen to span both extremes without crowding the panel.
#The offsets keep the crowded low-companion corner legible.
ANNOTATE = {
    "Whole Rock": {
        "As ppm": (-15, -3), "Au ppb": (0, -16), "Sb ppm": (14, 2), "Pb ppm": (0, 10),
        "Cs ppm": (13, -2), "Ce ppm": (-14, 4), "Nd ppm": (-15, -9),
    },
    "Stream Sediment": {
        "U ppm": (0, -28), "As ppm": (-16, -3), "Au ppb": (0, 11), "Sb ppm": (13, 3),
        "Pb ppm": (-22, 7), "Br ppm": (0, 11), "Ho ppm": (-13, -2),
    },
}


def PerElement(dataset):
    """The per-element export written by `4. Results.ipynb`."""
    name = dataset.replace(" ", "-").lower()
    frame = pd.read_csv(ResultsDir() / f"per-element-{name}.csv", sep=";")
    frame["companion"] = frame["companion_spearman"].abs()
    return frame


def FigureIsolation():
    """Chemical isolation explains both the baseline and the neighbour gain."""

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2), sharey=True)
    frames = {dataset: PerElement(dataset) for dataset in DATASETS}
    largest = max(frame["+neighbours"].max() for frame in frames.values())

    for ax, dataset, panel in zip(axes, DATASETS, ["(a)", "(b)"]):
        frame = frames[dataset]

        #Size carries the neighbour gain, so all three quantities sit in one panel
        sizes = 12 + 260 * (frame["+neighbours"].clip(lower=0) / largest)
        ax.scatter(frame["companion"], frame["baseline"], s=sizes, color=NEIGH,
                   alpha=0.45, linewidths=0.5, edgecolors="white", zorder=3)

        offsets = ANNOTATE[dataset]
        for _, row in frame[frame["element"].isin(offsets)].iterrows():
            ax.annotate(row["element"].split()[0], (row["companion"], row["baseline"]),
                        textcoords="offset points", xytext=offsets[row["element"]],
                        ha="center", fontsize=7, color=TEXT, zorder=4)

        ax.set_xlim(0.25, 1.06)
        ax.set_ylim(0.05, 1.06)
        ax.set_xlabel("$|\\rho|$ with closest companion element")
        ax.set_title(f"{panel} {LABELS[dataset]}", loc="left")
        ax.set_axisbelow(True)

    axes[0].set_ylabel("Baseline $R^2$ (own chemistry)")

    #Legend keyed to the size encoding rather than to colour
    handles = [plt.scatter([], [], s=12 + 260 * gain / largest, color=NEIGH, alpha=0.45,
                           linewidths=0.5, edgecolors="white", label=f"$+{gain:.2f}$")
               for gain in [0.0, 0.05, 0.20]]
    axes[1].legend(handles=handles, title=r"gain from neighbours", title_fontsize=7.5,
                   fontsize=7.5, loc="lower right", labelspacing=1.1, borderpad=0.8)

    fig.savefig(FiguresDir() / "isolation.png")
    return fig


#Name -> builder, in the order the report uses them. Both entry points iterate this, so a
#figure added here appears in the report and in `4. Results.ipynb` without further wiring.
FIGURES = {
    "samples": FigureSamples,
    "ksweep": FigureKSweep,
    "difficulty": FigureDifficulty,
    "isolation": FigureIsolation,
    "featuresets": FigureFeatureSets,
    "gnn": FigureGNN,
}


if __name__ == "__main__":
    for name, Build in FIGURES.items():
        plt.close(Build())
        print(f"  wrote {name}.png")
    print("figures written to", FiguresDir())
