# Project Summary

**Author:** Salvador Palma · Copenhagen University
**Project Outside Course Scope (15 ECTS)** · Supervisor: Bulat Ibragimov
**Last updated:** 2026-09-09

Running log of the hand-built work in `Project/`. Appended as the project advances.

> **Starting a new session? Read this first.**
>
> * **RQ1 is done — experiments and report both** — see *Report write-up* below.
>   Do not add RQ1 experiments without a reason; the next work is RQ2.
> * Everything in `Project/` is hand-built and is the work being assessed. The workspace
>   *root* holds two vibe-coded predecessors (Bulat's `gui.py` GUI and a `greenland_ml/`
>   package) — reference only, not part of this project, and their `report/report.pdf`
>   answers a different question (see *Comparison to prior code*).
> * Four notebooks, run in order: `1. Data Fetching` → `2. Random Forest` → `3. GNN` →
>   `4. Results`. Switching dataset means changing three constants (`DATA_TYPE`,
>   `MERGE_TYPE`, `SOURCE_CSV`) and nothing else — except in `4. Results`, which loads
>   **both** datasets at once, trains nothing, and only reads the JSON cache.
> * Results cache to `Results/<DATA_TYPE>/<MERGE_TYPE>/`. Every experiment checks the cache
>   first, so a rerun is near-instant unless the file is missing.
> * **Every number below is random 5-fold CV.** Spatial CV is RQ2 and is not built yet.
>   Do not present these as spatial-generalisation results.
> * **Two target sets exist.** Files with no suffix use the 10 best-covered elements; files
>   suffixed `_Cov1000` use every element with ≥1000 measurements (48 whole rock, 71 stream).
>   **The `_Cov1000` set is the reportable one** — see *The correction* below for why.

---

## Research questions

| RQ | Question | Status |
|---|---|---|
| 0 | Parse GEUS exploration reports with public AI models | **dropped** — supervisor deprioritised |
| **1** | **Predict a held-out element from a sample's other elements (random CV)** | **experiments done, writing** |
| **2** | **Predict a geographically held-out region (spatial CV)** | **not started** |

**RQ0 is out.** Bulat, by email: *"Parsing is more of a long-term project for this work.
I think we should not worry about this for now."* This also matched the observation that
the scanned reports rarely contain parseable assay tables.

**RQ2 was ambiguous and is now settled.** *"Predict areas where no reports are available"*
could mean predicting concentrations in unsampled regions, or predicting which regions are
prospective. Bulat's clarification picks the first: *"select a geological area outside the
one we used for training and predict the numbers there."* **Regression, spatially held out
— not occurrence classification.** The predecessor report built the second interpretation;
that is not what this project is doing.

Bulat also set the direction: *"It is very naive from a geological point of view… What we
should do is add a geologically relevant angle — additional data parameters, maybe maps, or
geophysical measurements."* The geophysical features below are that work, already done.

---

## Report write-up

**Drafted 2026-09-09.** RQ1's experimental work is finished and the report is written.
`Report/Report.tex` is a `scrartcl` document (biblatex/biber, booktabs, siunitx, cleveref),
**16 pages**: title page, abstract + contents, 13 of body, ~1.5 of references. It compiles with
`pdflatex → biber → pdflatex ×2` (MiKTeX here has no perl, so `latexmk` does not run).

Layout choices made to hit that length, all reversible in the preamble: `geometry` at 2.5 cm
margins (KOMA's default typearea was leaving ~6 cm of horizontal margin), classic indented
paragraphs rather than `parskip=half`, and `maxnames=3` in biblatex so 14-author entries do not
run three lines each. Together these were worth ~5 pages with no words cut.

Dropping the standalone title page for a title block would take it to 15; left in place as a
submission-format call.

Four tables were folded into prose during the same pass (model comparison, difficulty bands,
the isolation split, and the two-model check) — all four were small or duplicated a figure. The
numbers survive inline; nothing was dropped.

| section | content |
|---|---|
| 1 Introduction | the archive, RQ0/RQ1/RQ2, four contributions |
| 2 Data and method | two datasets, pipeline, targets, A–D encodings, geophysics, models, GNN |
| 3 Results | baseline, pooling vs enumeration, difficulty stratification, pathfinders, feature sources, GNN, robustness |
| 4 Discussion | redundancy thesis, why pooling wins, why the GNN does not, limitations |
| 5 Conclusion | answer to RQ1, hand-off to RQ2 |

Background was folded into the method section rather than kept as its own chapter — every
citation now sits next to the choice it justifies. `references.bib` has 16 entries.

**Six figures carry the argument**, all regenerated from `Results/` by
`Report/make_figures.py` (run from the repo root):

1. `samples.png` — sample locations on both datasets (the sampling-geometry contrast)
2. `ksweep.png` — A–D k-sweep, both datasets (aggregation vs dimensionality)
3. `difficulty.png` — gain stratified by baseline difficulty (**the central figure**)
4. `isolation.png` — companion strength vs baseline vs neighbour gain (**the mechanism**)
5. `featuresets.png` — feature-source ablation (spatial alone vs on top of chemistry)
6. `gnn.png` — GNN vs hand-built across k (learned aggregation does not win)

Figure 4 reads `Results/per-element-*.csv`, which `4. Results.ipynb` exports; the other five
read the experiment JSONs directly.

**Two entry points, one implementation.** `make_figures.py` exposes a `FIGURES` dict mapping
name → builder; each builder saves its PNG and returns the figure. `python
Report/make_figures.py` from the repo root iterates it, and so does the final *Report Figures*
section of `4. Results.ipynb`, which imports the module and displays each figure inline. Adding
a figure to that dict is the only wiring needed for it to appear in both.

The module addresses paths through `make_figures.ROOT` (default: the working directory), which
the notebook sets to `DRIVE_PATH` on Colab. Importing it applies the report's Matplotlib style
globally, so plot anything of your own *before* that cell.

Two things deliberately *not* in the report, having been judged process rather than result:
the KNN vectorisation speedup, and the narrative of how the target-set correction was found.
The correction itself survives as a *Target selection* paragraph inside §3.8 *Robustness*,
stated as a sensitivity result.

---

## Datasets

Two GEUS geochemistry datasets, both public, both run through the same pipeline.

| | whole rock | stream sediment |
|---|---|---|
| source | `Data/whole-rock.csv` | `Data/stream-sediment.csv` |
| raw rows | 26,068 | 20,158 |
| raw element columns | 76 | **523** |
| merged samples | 6,957 | **17,463** |
| element columns after merge | 76 | 93 |
| after coverage filter (<10) | 68 | 87 |
| targets at coverage ≥1000 | 48 | 71 |
| unique coordinate pairs | 4,498 | 16,542 |
| samples sharing a coordinate | 3,458 (**50%**) | 1,759 (**10%**) |
| max samples at one coordinate | 67 | 11 |
| longitude span | −53.9 … −42.3 (11.7°) | **−72.8 … −13.3 (59.5°)** |
| latitude span | 59.9 … 70.2 | 59.8 … 83.6 |

The two differ in a way that turned out to matter, though not in the way first assumed:
whole rock is clustered, exploration-driven sampling in a narrow longitude band; stream
sediment covers the whole island with a fifth of the co-location. **Co-location is real and
kept in both** — 67 samples at one outcrop is genuine sampling density, not duplication.

Stream sediment's 523 raw element columns are 93 elements measured by up to four
lab/method combinations each (`ACTLABS FUS ICP Ni ppm`, `ACTLABS INAA Ni ppm`, …). Whole
rock already has one column per element.

**Provenance note.** Bulat's `geochem_stream.csv` (69,720 rows, 15,398 samples) and
`clean_stream.csv` (14,831 samples) are the same data in long format and merged form.
All 15,398 of his samples are in the portal export used here, none are missing from it,
and shared-sample values agree (r=0.92 on Ni). The portal export is used because it has
2,065 more samples and a known origin.

### Column schema

Each source csv carries a `<name>.json` beside it naming `sampleCol`, `metaCols`,
`physicalCols` and `locationCols`. Element columns are whatever is left over, so a new
dataset needs no code change — only the schema file and three constants. `Longitude` and
`Latitude` sit in `metaCols`, so coordinates never leak into the chemistry feature set.

---

## Data treatment (`1. Data Fetching.ipynb`)

1. **Mask BDL** — values ≤ 0 are below detection limit → NaN. Done first so a negative
   reading can never drag a later median down.
2. **Merge analytical columns** — collapse per-lab, per-method columns of the same element
   into one, median across whichever methods measured that sample. Stream sediment goes
   523 → 93; whole rock is untouched, since the function returns early when every element
   already has exactly one column. Methods differ in detection limit and bias, so the
   median here is a deliberate choice of the neutral option rather than a given.
3. **Merge by sample number** — median across the duplicate rows of one physical sample.
4. **Log10 transform** — concentrations span wt% to ppb. After both merges, so it is a
   log of medians rather than a median of logs.
5. **Coverage filter** — drop element columns measured in < 10 samples. Whole rock loses 8
   (`I ppm` and `Os ppb` are *entirely* empty); stream loses 6. This stays last on purpose:
   filtering earlier would discard measurements the merges would have rescued.
   Needed because HistGradientBoosting cannot bin a constant column; Random Forest
   silently tolerated them by never splitting on them.
6. **Splits** — 80/10/10 holdout (`Holdout.split`) + 5-fold random CV (`5-Fold.kfold`).

Outputs: one `Data.csv`, one split file, one k-fold file. Nothing else.

---

## Neighbour features (`2. Random Forest.ipynb`)

Built **at training time**, per fold, never cached to disk.

- KD-tree fitted on **training coordinates only**, queried with all rows, so a test
  sample never sees another test sample.
- Self-matches pushed to infinity.
- `excludeSameLocation=True` additionally drops distance-0 neighbours, separating
  "another sample from the same outcrop" from "a genuinely different place".
- Returns positions **and distances**; gathered into one `(samples, k, elements)`
  array per fold that every variant slices.

### The four KNN encodings

| variant | content | added columns (k=20, m=87) |
|---|---|---|
| A | mean of the **target** element over k neighbours | 1 |
| B | the k individual **target** values | 20 |
| C | mean of **every** element over k neighbours | 87 |
| D | **every** element of **every** neighbour | 1,740 |

C is the settled encoding — its column count is independent of k, which is the whole
reason it wins (see the k-sweep).

### Performance rewrite

The original per-row `progress_apply` construction was replaced with vectorised
NumPy gathers. Measured on fold 1, identical output (`np.allclose(..., equal_nan=True)`):

| | per fold | 5 folds |
|---|---|---|
| Row-wise `progress_apply` | 65.8 min | 5.5 h |
| Vectorised | 0.077 s | 0.38 s |

**~51,600× faster.** Caching the KNN CSVs to disk is now slower than recomputing
them, so the cached files were removed — which also eliminates the risk of a stored
mapping falling out of sync with its split.

---

## Models

`MakeModel(modelType)` selects between three, so any experiment can be re-run under
each without editing the pipeline.

### Baseline comparison (whole rock, 10 elements × 5 folds, own-chemistry features)

| model | mean R² | total time |
|---|---|---|
| RandomForest (200 trees) | 0.8207 | 388 s |
| **HistGradientBoosting (200 iter)** | **0.8388** | **155 s** |
| XGBoost (200 est., `hist`) | 0.8215 | 199 s |

**HGB wins on all ten elements** and is the fastest. XGBoost at default settings is
indistinguishable from Random Forest — its reputation comes from heavily tuned
competition use; untuned defaults (`max_depth=6, learning_rate=0.3`) overfit this
small, dense, correlated dataset.

`MODEL_TYPE = "hgb"` is the working default.

**Model independence** was checked on whole rock, where all four encodings ran under both
RF and HGB and agreed — every gain inside one fold std, D worst under both:

| variant | RF Δ | HGB Δ |
|---|---|---|
| A | +0.0016 | +0.0033 |
| B | −0.0004 | +0.0033 |
| C | −0.0003 | +0.0064 |
| D | −0.0101 | −0.0002 |

Stream sediment results use HGB only. Re-running the A–D table under RF there was
considered and rejected: variant D at k=20 is 1,740 columns and `RandomForestRegressor`
searches all features per split, making it far more expensive than HGB's binning for a
confirmation the whole-rock table already provides. **This is a stated limitation.**

---

## Results — RQ1

### The correction

The first version of this project reported a sharp contrast: neighbour features added
nothing on whole rock (+0.006, inside noise) but 2.5σ on stream sediment, read as evidence
that **sampling geometry** decides whether spatial context helps.

**That result did not survive widening the target set, and the widening is the honest
comparison.** Both datasets had been scored on their 10 best-covered elements — an
arbitrary cutoff that happened to differ systematically between them. Whole rock's top 10
is oxide-heavy and easy; stream's is trace-heavy and hard, and it contained uranium.

Matched at coverage ≥1000, variant C, k=20, co-located neighbours excluded:

| | targets | baseline | KNN C | Δ | in σ |
|---|---|---|---|---|---|
| Whole rock | 48 | 0.7983 | 0.8132 | +0.0149 | **0.82σ** |
| Stream sediment | 71 | 0.8676 | 0.8801 | +0.0125 | **0.91σ** |

The two datasets are now **statistically indistinguishable, and both sit below one fold
standard deviation.**

Note which side moved. Whole rock is unchanged (0.81σ → 0.82σ). **Stream collapsed**, from
2.93σ to 0.91σ, and the cause is one element:

* U's gain is +0.2205, an order of magnitude above any other element.
* In a 10-element mean it contributes +0.0220 of +0.0342 — **65% of the old headline was
  uranium alone.**
* In the 71-element mean it contributes +0.0031 of +0.0125 (25%). Excluding U, stream's
  gain is +0.0096.

This is exactly the failure mode the widening was meant to catch, and it caught it.

### The A–D table (Cov1000, k=20, co-located excluded)

Fold std 0.0180 whole rock, 0.0137 stream.

| variant | whole rock | Δ | stream | Δ |
|---|---|---|---|---|
| baseline | 0.7983 | — | 0.8676 | — |
| A (+1 col) | 0.8043 | +0.0059 | 0.8757 | +0.0081 |
| B (+20 cols) | 0.8050 | +0.0066 | 0.8724 | +0.0048 |
| **C (+87 cols)** | **0.8132** | **+0.0149** | **0.8801** | **+0.0125** |
| D (+1,740 cols) | 0.7982 | −0.0001 | 0.8659 | −0.0017 |

Same shape on both: C best, D at or below baseline, every gain under 1σ.

### K-sweep — how many neighbours?

Δ over baseline, top-10 targets, HGB, co-located excluded. Both datasets now run to k=100.

| k | WR A | WR C | WR D | SS A | SS C | SS D |
|---|---|---|---|---|---|---|
| 1 | +0.0016 | +0.0020 | +0.0020 | +0.0186 | +0.0221 | +0.0221 |
| 3 | +0.0027 | +0.0048 | +0.0007 | +0.0248 | +0.0279 | +0.0216 |
| 5 | +0.0033 | +0.0064 | −0.0002 | +0.0270 | +0.0297 | +0.0199 |
| 10 | +0.0035 | +0.0082 | −0.0013 | +0.0276 | +0.0327 | +0.0174 |
| 20 | +0.0037 | +0.0102 | −0.0035 | +0.0279 | **+0.0347** | +0.0158 |
| 50 | +0.0041 | +0.0112 | −0.0054 | +0.0282 | **+0.0355** | +0.0112 |
| 100 | +0.0043 | **+0.0116** | −0.0079 | +0.0230 | +0.0353 | +0.0087 |

Two clean trends, in opposite directions, **now confirmed on both datasets**:

* **C improves with k and plateaus at k≈20–50.** It stays at 87 columns whatever k is, so
  more neighbours only smooth sampling noise. Stream: +0.0347 / +0.0355 / +0.0353 at
  k=20/50/100 — converged. Whole rock is still creeping at k=100 but has flattened.
* **D degrades monotonically with k**, tracking its column count (1,740 at k=20; 8,700 at
  k=100). Same information, spread over more columns.

**A neighbourhood should be pooled, not enumerated.** This is the most robust result in the
project — two datasets, two models, seven values of k.

`k = 20` is the settled value: the plateau onset, and free for variant C, whose column
count does not depend on k (measured: 0.46 s to build at k=20 vs 0.48 s at k=10).

### Where the gain lands — the central result

Binning targets by their **own baseline score** separates elements chemistry already
predicts from elements it cannot. Mean gain within each bin, Cov1000, k=20:

**Whole rock (48 targets)**

| baseline R² | n | mean baseline | + neighbours | + geophysics |
|---|---|---|---|---|
| < 0.70 | 8 | 0.5920 | **+0.0517** | +0.0238 |
| 0.70 – 0.85 | 23 | 0.7927 | +0.0102 | +0.0058 |
| 0.85 – 0.95 | 14 | 0.8909 | +0.0044 | +0.0026 |
| > 0.95 | 3 | 0.9597 | +0.0008 | +0.0007 |

**Stream sediment (71 targets)**

| baseline R² | n | mean baseline | + neighbours | + geophysics |
|---|---|---|---|---|
| < 0.70 | 8 | 0.5846 | **+0.0484** | +0.0291 |
| 0.70 – 0.85 | 13 | 0.7896 | +0.0211 | +0.0084 |
| 0.85 – 0.95 | 30 | 0.9076 | +0.0075 | +0.0032 |
| > 0.95 | 20 | 0.9714 | +0.0001 | +0.0004 |

**Two datasets, different sampling geometries, different target sets, and the curve is the
same.** Neighbours are worth ~+0.05 where own chemistry fails and nothing at all where it
already scores above 0.95. The pooled mean is a weighted average of these, which is why it
moved so much when the target set changed — and why the stratified table, not the pooled
mean, is the result to report.

### The pathfinder exception

The elements that gain most are not a random assortment, and they reproduce across datasets:

| whole rock | Δ | stream | Δ |
|---|---|---|---|
| As ppm | +0.096 | U ppm | +0.220 |
| Au ppb | +0.092 | As ppm | +0.060 |
| Sb ppm | +0.070 | Br ppm | +0.043 |
| Cs ppm | +0.048 | Sb ppm | +0.041 |
| S ppm | +0.040 | Pb ppm | +0.034 |
| Pb ppm | +0.027 | Cs ppm | +0.031 |

**As, Sb, Cs and Pb appear in both lists.** These are the classic hydrothermal *pathfinder*
suite plus mobile alkalis — elements whose distribution is set by regional-scale processes
(mineralisation, alteration, and for Br marine influence) rather than by bulk rock
composition. Uranium is the extreme case, and appears in three independent analyses: the
largest neighbour gain, the only reliable geophysical correlations (+0.28 magnetics, −0.34
Moho depth, n=3227), and the one element the predecessor report found neighbours help under
*spatial* CV (0.472 → 0.578).

Five of stream's top six were invisible under the old top-10 cutoff.

### Chemical isolation — the mechanism (`4. Results.ipynb`)

**Added 2026-09-10.** Measured directly from the chemistry, with no model involved: for each
element, the strongest pairwise-complete Spearman it has with any *other* element in the same
sample — its **companion strength**, i.e. how good a proxy the sample already carries.

| | whole rock | stream |
|---|---|---|
| companion strength vs baseline R² | **+0.765** (ρ +0.756) | **+0.760** (ρ +0.628) |
| companion strength vs neighbour gain | −0.633 (ρ −0.696) | −0.440 (ρ −0.629) |

Split on whether any partner exceeds ρ=0.8:

| | n | baseline | + neighbours |
|---|---|---|---|
| whole rock, has a partner >0.8 | 23 | 0.864 | +0.0047 |
| whole rock, isolated | 25 | 0.738 | **+0.0242** |
| stream, has a partner >0.8 | 44 | 0.920 | +0.0047 |
| stream, isolated | 27 | 0.782 | **+0.0253** |

The connected rows agree to four decimals across two datasets, which is luck, but the split
itself reproduces cleanly. The identities do the explaining: the top of the baseline
distribution is REEs tracking each other at ρ>0.98 (Ce–Pr 0.995, Ho–Er 0.993), the bottom is
elements with no proxy at all — Au 0.31 (stream), As 0.47, U 0.60, none with a partner over 0.8.

**This is the mechanism behind the difficulty stratification.** Spatial context substitutes for
a missing chemical proxy; where the sample already contains one, the neighbourhood is redundant.
It also collapses the pathfinder ambiguity: "mobile element" and "hard target" are one property
seen from two sides, since an element set by mineralisation rather than bulk composition is for
that reason one nothing else in the sample tracks. **Does not resolve the confound** — isolation
explains both — but names the common cause. Report §3.5, `isolation.png`.

### Geophysics as a position proxy (`4. Results.ipynb`)

Independent of the model ablation: for each element, its strongest geophysical correlation
against its strongest correlation with raw easting/northing.

* Whole rock: geophysics wins for **27/64 (42%)**; median |ρ| for northing alone 0.106.
* Stream: geophysics wins for **26/81 (32%)**; median |ρ| for northing alone 0.248.

Moho depth is r=+0.75 with northing on **whole rock**, but only −0.23 on stream — so the
proxy relation is a property of the sampling footprint, not of the grid. Worth remembering
before reading too much into it under spatial CV.

### Feature sources (Cov1000)

| set | whole rock | stream |
|---|---|---|
| Chemistry | 0.7983 | 0.8676 |
| Physics | 0.3228 | **0.5253** |
| Location | 0.3484 | **0.5994** |
| Neighbours | 0.3246 | **0.6086** |
| Chemistry + Physics | 0.8059 | 0.8739 |
| Chemistry + Location | 0.8063 | 0.8775 |
| Physics + Location | 0.3546 | 0.6017 |

1. **Sampling geometry does decide how much spatial information exists.** Every standalone
   spatial source roughly doubles from whole rock to stream (neighbours 0.325 → 0.609,
   location 0.348 → 0.599). This contrast is large and survives the target-set widening
   intact — it is the part of the original claim that holds.
2. **But it does not decide how much that information *adds*.** Five times the spatial
   signal buys the same sub-1σ gain on top of chemistry, because chemistry already carries
   nearly all of it. **This is the thesis of RQ1.**
3. **The three spatial sources are interchangeable** — physics, location and neighbours land
   in one band on each dataset, and everything adds about the same on top of chemistry
   (+0.006 to +0.012). Three encodings of "where am I", one ceiling.
4. **Geophysics does not beat plain coordinates.** Location outscores Physics on both, and
   Physics + Location barely exceeds Location alone (stream: 0.6017 vs 0.5994).

> **Reading 4 is conditional on random CV and is the single most likely conclusion to
> change.** Coordinates are unusually strong when train and test are interleaved in space.
> Under spatial CV they should collapse while the geophysical grids — real measurements
> available at every point — should not. That test is RQ2.

---

## Graph neural network (`3. GNN.ipynb`)

Built on stream sediment only, where the standalone spatial signal is 0.609 against whole
rock's 0.325 — the dataset with headroom for a learned aggregation to compete over.

**Design.** Nodes = samples. Edges = the same train-only k-NN mapping the KNN variants use,
so the network sees exactly the neighbourhood the hand-built columns saw. Node features are
the sample's own elements with the target removed, each contributing two columns —
standardised value (zero when missing) and a present/absent flag, since a network cannot
consume NaN and needs to tell "average" from "not measured". Standardisation uses training
rows only. Full-batch transductive training, early stopping on a validation slice carved out
of *training* nodes.

**Two architectures, and the contrast was the experiment:** `GATConv(edge_dim=1)`, whose
attention weights are computed per edge **from the distance** — the one thing variants A–D
structurally cannot encode — against `SAGEConv` as the distance-blind control.

### The GNN k-sweep (top-10 targets)

| k | GAT | SAGE | KNN C | SAGE − GAT |
|---|---|---|---|---|
| 1 | 0.8043 | 0.7918 | 0.8209 | −0.0125 |
| 3 | 0.8125 | 0.8090 | 0.8267 | −0.0035 |
| 5 | 0.8188 | 0.8182 | 0.8285 | −0.0006 |
| 10 | 0.8208 | 0.8216 | 0.8315 | +0.0008 |
| 20 | 0.8205 | **0.8260** | 0.8335 | +0.0055 |
| 50 | 0.8138 | 0.8255 | **0.8342** | +0.0117 |
| 100 | 0.8091 | 0.8231 | 0.8340 | +0.0140 |

Three findings:

1. **KNN C beats both architectures at every single k.** No crossover anywhere. Best GNN is
   SAGE at k=20 (0.8260); best hand-built is C at k=50 (0.8342).
2. **Distance-aware attention actively hurts at large neighbourhoods.** There is a crossover
   at k≈5: below it GAT wins, above it SAGE wins by a margin widening to +0.0140 at k=100.
   GNN run-to-run noise is ~0.002, so the k≥20 gaps are well outside it. An earlier
   single-point comparison at k=10 suggested the two were identical; the sweep shows that
   was the one k where they happen to cross.
3. **GAT degrades past k=20** (0.8205 → 0.8091), tracking edge count exactly as variant D
   tracks column count. The same aggregation-versus-dimensionality effect appears in the
   learned model.

### Settled configuration (SAGE, k=20, Cov1000)

| | mean R² | vs chemistry |
|---|---|---|
| tabular Chemistry | 0.8676 | — |
| **tabular KNN C** | **0.8801** | **+0.0125** |
| GNN Chemistry | 0.8676 | −0.0000 |
| GNN Chemistry + Physics | 0.8679 | +0.0004 |
| GNN Chemistry + Location | 0.8684 | +0.0008 |

The GNN's graph is always on, so **GNN `Chemistry` is the counterpart of tabular `KNN C`,
not of tabular `Chemistry`** — 0.8801 is the number it has to beat.

**It lands exactly on the no-neighbour baseline.** One target distorts this: `Sum wt%` is a
−0.253 outlier for the GNN (0.987 → 0.725) where nothing else is worse than −0.061.
Excluding it, GNN = +0.0037 against KNN C's +0.0128 — so the GNN recovers about **29% of the
available neighbour gain**, not zero. It beats KNN C on only 15 of 71 elements, and its wins
are small and concentrated in REEs while its losses are on the hard elements that matter.

On uranium it exactly ties the hand-built columns (0.814 vs 0.814, from a 0.594 baseline):
it captures the one large spatial signal and misses the many small ones.

Adding physics or location to the node features moves the pooled mean by +0.0004 and +0.0008
— inside noise. **Geophysics adds nothing to a model that already has the graph.**

**Ran on Colab (T4)**, ~9.1 s per fit at k=20; the full sweep was ~5 h, the settled
configuration ~54 min per feature set. The Drive mirror at `MyDrive/UCPH/POOCS/` holds
`GreenlandUtils.py`, the schema json, `Data.csv`, `5-Fold.kfold` and reference results.

---

## Known caveats

Deliberately accepted, to be stated in the report rather than fixed.

**`Sum wt%` is an exact arithmetic identity.** It equals the sum of the major oxides plus
L.o.i. — median absolute difference **0.0000 wt%**, 98.9% of 8,482 samples within 0.5 wt%.
The relation runs both ways, so `SiO2` and the other major oxides are also inflated by
subtraction, not only `Sum wt%` itself. Stream sediment only; whole rock has no such column.

**~10 elements appear twice under different unit conventions** — `Fe %`/`Fe2O3 wt%` (r=0.93),
`Mn %`/`MnO wt%` (r=0.97), plus Ca, Mg, K, Ti, P, Na. Redundancy rather than leakage, since
the pairs come from different digestions and methods.

Both raise absolute baselines and dilute measured gains. **Neither affects any conclusion
here, because every claim is a difference between two arms that see identical features.**
The one number to treat carefully is the `> 0.95` bin of the stratified table, which these
columns partly populate; the `< 0.70` row carries the finding and is unaffected.

**`Au ppb` is effectively unpredictable** (baseline 0.128, fold std 0.061) and `Ta`, `Pr`,
`Cl` have fold std > 0.03. Five unstable targets out of 71.

---

## Geophysical features (`1. Data Fetching.ipynb`)

Geochemical neighbours only exist where somebody has already sampled. Geophysical grids are
measured everywhere, so they are what replaces the neighbourhood on unexplored ground — the
RQ2 substitute. Attached to `Data.csv` before the splits, since they are static per coordinate
and carry no train/test dependence.

**Inclusion rule: full Greenland coverage**, checked over the whole landmass rather than over
the samples at hand, so the same columns attach to any future sample set unchanged.

| column | source | grid | licence |
|---|---|---|---|
| `geo_magnetic_anomaly nT` | GREENMAG `doi:10.22008/FK2/LQN5YJ` | 400 m, native UTM 24N | CC-BY 4.0 |
| `geo_heat_flow mW/m2` | Heat Flow `doi:10.22008/FK2/F9P03L` | ~0.4° (~25 km) | CC0 |
| `geo_depth_to_moho km` | Depth to Moho `doi:10.22008/FK2/TG7OQU` | ~0.5 km spacing | CC-BY 4.0 |

All three are 100% valid at the 6,957 whole-rock samples. Magnetic anomaly spans −472…840 nT,
heat flow 32.9…117.7 mW/m², Moho depth 27.7…46.6 km.

**What they mean.** Magnetic anomaly tracks how magnetite-rich the rock is (mafic high, felsic
low). Heat flow tracks tectonic setting plus decay of U/Th/K. Moho depth is crustal thickness —
thin under rifted margins, thick under old craton.

### Rejected, and why

| candidate | reason |
|---|---|
| NAG-TEC gravity (Bouguer / isostatic / tilt) | North Atlantic compilation; point density collapses west of 50°W. **Median 157 km** from a sample to the nearest grid point |
| crustal thickness, sediment thickness, depth to basement | same family, 43% NaN; 131 km and 287 km median distance |
| DTU gravity (ArcGIS service) | *does* cover Greenland in EPSG:32624, but publishes only rendered RGB imagery — no ImageServer, no pixel values. **Asking GEUS for the underlying grid** |
| Airborne radiometrics (K/U/Th), AEROMAG 1992–2013 | partial coverage |
| Darbyshire S-wave speed, subglacial provinces (both CC0) | need `rasterio` / `geopandas`; deferred until geophysics is shown to help |

Zero NaN in a file is not evidence of coverage — the gravity products have no missing values
because they have no *points* over western Greenland.

Also noted: the `geusmap/ows` WFS/WMS endpoint recorded in the older workspace notes now
returns **404** for both services.

### Correlation with geochemistry

Pearson and Spearman, pairwise-complete, on the log10 concentrations, with easting and
northing included as controls. Only pairs with ≥100 samples are kept.

The trustworthy signals are the ones with large n: **U ppm** correlates +0.28 with magnetics
and −0.34 with Moho depth (n=3227 both), which is coherent — uranium concentrates in evolved
felsic crust, which is thick and weakly magnetic. The largest coefficients in the table sit on
`C wt%` at n=101 and should not be relied on; that column also correlates −0.58 with northing.

**Only 42% of elements (27/64) have a geophysical field correlating more strongly than plain
easting or northing.** Median |Spearman| for northing alone is 0.106. Moho depth in particular
is r=0.75 with northing, so it may be closer to a latitude proxy than to independent physics.

---

## Comparison to prior code

Bulat's GUI (`gui.py`, workspace root) implemented an RF+NN experiment equivalent to
**variant D with k=1**, with two differences: the neighbour feature vector is not
target-masked, and neighbours are drawn from the **full dataset** before a random
`KFold` — so test samples appear in training samples' neighbour lists. With 25.6% of
neighbours at exactly 0 m, that number is not a clean estimate. The help text in that
code flags the risk without closing it.

The current pipeline uses train-only lookup, consistent masking, `k` as a parameter,
four explicit encodings, and a coverage-threshold target set rather than an arbitrary top-n.

---

## Task list

### RQ1 — experiments complete

Nothing outstanding. Both datasets have the Cov1000 ablation, k-sweeps to k=100, the
feature-source ablation and the difficulty stratification; stream additionally has the full
GNN sweep and settled configuration.

Deliberately not done, each for a stated reason: RF on stream Cov1000 (whole rock already
provides the two-model check; variant D under RF is prohibitive), a whole-rock GNN (no
headroom), and dropping the caveat columns (conclusions are differences, so unaffected).

### RQ1 — write-up complete

Figures, citations and all five sections are done; `Report/Report.pdf` builds clean. What is
left is a proof-read pass, not new writing.

### RQ2 — build

4. **Implement spatial block folds.** Hash UTM coordinates into squares of side `blockKm`,
   assign whole blocks to folds. Write as `Spatial-{km}km.kfold` in the same format as
   `5-Fold.kfold` so `ReadKFold` picks it up unchanged. Blocks beat KMeans: block size in
   kilometres is interpretable, whereas KMeans clusters follow sampling density.
   Reference implementation at `greenland_ml/data/spatial.py:99` in the root package.
5. **Sanity-check fold geometry** — fold sizes, and minimum distance from each test sample to
   its nearest training sample. Cheap, and catches a silent failure mode.
6. **Rerun the core table under spatial CV** — baseline, KNN C, full feature-source ablation.
   **The step that can change a conclusion**: if Physics overtakes Location, that is the
   headline RQ2 result and exactly the geological angle Bulat asked for.
7. **Block-size sweep**, `blockKm ∈ {10, 25, 50, 100, 200}`. The degradation curve is a better
   deliverable than any single number — it shows the distance over which the model generalises.
8. **GNN under spatial CV**, SAGE at k=20 only. Do not sweep architectures again.
9. **Geological province hold-out** — the stricter test Bulat described. Subglacial provinces
   are a GeoPackage (`doi:10.22008/FK2/BUQQ9C`, CC0), needs `geopandas`. First to cut if time
   runs short, but say so explicitly rather than omitting it.

**Stream sediment only.** Whole rock spans 11.7° of longitude in one region of West Greenland
— there is no meaningful "outside" to hold out, and block CV would either make blocks too
small to be independent or shatter the dataset. Whole rock retires at the RQ1/RQ2 boundary,
as a stated decision rather than a silent omission.

### Framing RQ2: two scenarios, not one

| feature set | scenario |
|---|---|
| Chemistry | new region, sample collected, partial analytical suite |
| Chemistry + Physics | same, geologically enriched — **the primary RQ2** |
| Neighbours | region has some prior sampling nearby |
| Physics | **genuinely blank terrain, nobody has been there** |

Bulat's phrasing implies the first: the samples exist and the region is withheld. The
Physics-only row is the honest lower bound on ground with no samples at all, and is worth
reporting precisely because it will be low.

---

## Open questions

* **Everything so far is random CV.** Position is unusually informative when train and test
  interleave in space. `Location = 0.599` on stream should be expected to collapse under
  spatial CV, and the "geophysics is a position proxy" reading could invert. This is task 6.
* **Does the redundancy thesis survive spatial CV?** Under random folds, chemistry already
  carries nearly all the spatial information. Under block folds it may not, which would make
  neighbours and geophysics matter far more than they do here. The predecessor report points
  the other way — its neighbour gain falls from +0.047 (random) to +0.003 (50 km blocks) — so
  both outcomes are live.
* **Is the pathfinder pattern geological or statistical?** As, Sb, Cs, Pb gain on both
  datasets, which argues geological. But they are also among the harder targets, and the
  stratified table shows gain tracks difficulty. Disentangling "mobile element" from "low
  baseline" would need a matched comparison at equal baseline.
* Would per-commodity occurrence labels be viable? `mineral_occurrences_v3_external` carries
  commodity attributes, but 1,167 positives fragment across classes. Relevant only if the
  project later extends toward prospectivity — **not part of RQ2 as Bulat defined it.**

---

## Environment notes

* **This PC** (transferred 2026-09-04): Python 3.13.3, Windows, 16 cores. `sklearn` 1.9,
  `pandas` 3.0.5, `numpy` 2.5.3. No `torch`/`torch_geometric` — GNN work runs on Colab.
  No `geopandas`/`rasterio` — task 9 needs the first.
* Pipeline reproduces across the machine transfer: stream top-10 baseline 0.7990 here vs
  0.7988 recorded, Physics 0.4719 vs 0.4712 — differences ~10× smaller than the fold std.
* Geophysical rasters live in `Project/Data/Geophysics/` (~250 MB, gitignored, **not
  transferred to this PC**): `GREENMAG_magnetic_anomaly.flt/.hdr`, `GeothermalHeatFlow.xyz`,
  `DepthToMoho.xyz`. Download URLs are in the markdown of `1. Data Fetching.ipynb` cell 8.
  Not needed downstream — `Data.csv` already carries the three `geo_` columns.
* GPU work runs on Colab against `MyDrive/UCPH/POOCS/`. `3. GNN.ipynb` ships with
  `COLAB_SESSION = True`; set it to `False` to run locally.
* Reference results uploaded to Drive should have `y_pred`/`y_test` stripped first — the
  `_Cov1000` files are 38.8 MB each and 6 KB without them.
* The `!pip install` cell at the top of notebooks 2 and 3 is a notebook magic, so a plain
  `ast.parse` of that cell fails. Expected, not a bug.
