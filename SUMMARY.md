# Project Summary

**Author:** Salvador Palma · Copenhagen University
**Project Outside Course Scope (15 ECTS)** · Supervisor: Bulat Ibragimov
**Last updated:** 2026-08-25

Running log of the hand-built work in `Project/`. Appended as the project advances.

---

## Research questions

| RQ | Question | Status |
|---|---|---|
| 0 | Parse GEUS exploration reports with public AI models | not started |
| **1** | **Predict missing geochemistry within reports (random sampling)** | **in progress** |
| 2 | Predict unexplored areas where no reports exist (spatial) | scoping |

Current focus is RQ1: predict a held-out element from a sample's other measured
elements, and test whether spatial context (nearest neighbours) adds anything.

---

## Dataset

**GEUS whole-rock geochemistry** (`Data/whole-rock.csv`), public.

| | |
|---|---|
| Raw rows | 26,068 |
| Unique sample numbers | 6,957 |
| Element columns (raw) | 76 |
| Element columns (after coverage filter) | 68 |
| Unique coordinate pairs | 4,498 |
| Samples sharing a coordinate | 3,458 (50%) |
| Max samples at one coordinate | 67 |

The 26,068 → 6,957 collapse is because one physical sample appears as several rows,
one per analytical method. **Co-location is real and kept**: 67 samples at one outcrop
is genuine sampling density, not duplication, so they stay as separate rows.

---

## Data treatment (`1. Data Fetching.ipynb`)

1. **Mask BDL** — values ≤ 0 are below detection limit → NaN.
2. **Merge by sample number** — median across the method-duplicate rows.
3. **Log10 transform** — concentrations span wt% to ppb.
4. **Coverage filter** — drop element columns measured in < 10 samples.
   Removes 8: `B ppm, Ru ppb, Rh ppb, Te ppm, I ppm, Re ppb, Os ppb, Ir ppb`
   (`I ppm` and `Os ppb` are *entirely* empty across all 6,957 samples).
   Needed because HistGradientBoosting cannot bin a constant column; Random Forest
   silently tolerated them by never splitting on them.
5. **Splits** — 80/10/10 holdout (`Holdout.split`) + 5-fold random CV (`5-Fold.kfold`).

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

| variant | content | added columns (k=5, m=68) |
|---|---|---|
| A | mean of the **target** element over k neighbours | 1 |
| B | the k individual **target** values | 5 |
| C | mean of **every** element over k neighbours | 68 |
| D | **every** element of **every** neighbour | 340 |

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

### Baseline comparison (10 elements × 5 folds, own-chemistry features)

| model | mean R² | total time |
|---|---|---|
| RandomForest (200 trees) | 0.8207 | 388 s |
| **HistGradientBoosting (200 iter)** | **0.8388** | **155 s** |
| XGBoost (200 est., `hist`) | 0.8215 | 199 s |

**HGB wins on all ten elements** and is the fastest. XGBoost at default settings is
indistinguishable from Random Forest — its reputation comes from heavily tuned
competition use; untuned defaults (`max_depth=6, learning_rate=0.3`) overfit this
small, dense, correlated dataset.

`MODEL_TYPE = "hgb"` is the working default. RF is kept as a comparison row so the
RQ1 conclusion can be shown to be model-independent.

---

## Results so far

### RQ1 — does spatial context help?

Mean R² over 10 elements, 5-fold random CV (fold std ≈ 0.012 throughout):

| variant | RF | RF (excl. co-located) | HGB (excl. co-located) |
|---|---|---|---|
| baseline (no neighbours) | 0.8206 | — | 0.8392 |
| A (+1 col) | 0.8235 | 0.8222 | 0.8421 |
| B (+5 cols) | 0.8190 | 0.8203 | 0.8421 |
| C (+68 cols) | 0.8192 | 0.8203 | **0.8452** |
| D (+340 cols) | 0.8036 | 0.8106 | 0.8386 |

**Neighbour features add essentially nothing.** The best gain (HGB variant C, +0.006)
is half a fold standard deviation. Variant D consistently *loses*, tracking its column
count — a feature-dimensionality effect, not a statement about geology.

The result holds under **two models** and **with and without co-located neighbours**,
which closes the obvious objection that the neighbours were just duplicates.

### Neighbour-only diagnostic *(exploratory — not yet reproduced in the notebooks)*

> These numbers come from a throwaway script run during a supervision session, **not**
> from `2. Random Forest.ipynb`. They are recorded here as a lead worth following, not
> as a project result. Re-implement as a notebook cell before citing in the report.

How much of an element is predictable from the neighbourhood *alone* (HGB, k=5):

| feature set | co-located allowed | co-located excluded |
|---|---|---|
| own chemistry (68 cols) | **0.839** | 0.839 |
| all-element neighbour means | 0.250 | 0.298 |
| target-only neighbour mean | 0.285 | 0.239 |
| raw UTM coordinates (x, y) | 0.313 | 0.313 |

Three findings:

1. **Spatial signal exists but is weak** — ~0.25–0.30 standalone against 0.84.
   Not zero, so a GNN is not doomed; not large, which explains the flat A–D results.
2. **Raw coordinates beat both neighbour encodings.** Two numbers outperform the full
   chemistry of five neighbours. Most of what "neighbourhood" contributes is coarse
   geographic position.
3. **Excluding co-located samples helps the broad encoding and hurts the narrow one.**
   A target-only column is nearly the answer when a twin is present; a 68-column
   vector was being degraded by near-zero-variance duplicate neighbourhoods.

**Working hypothesis for RQ1** (resting on the exploratory numbers above, so it needs
confirming): spatial context in Greenland whole-rock geochemistry may be largely
redundant with a sample's own co-measured chemistry, with the remainder mostly
reducible to position. What *is* established from the notebook runs is the A–D table
above — neighbour encodings add nothing beyond a fold standard deviation, under two
models, with and without co-located neighbours.

---

## Comparison to prior code

Bulat's GUI (`gui.py`, workspace root) implemented an RF+NN experiment equivalent to
**variant D with k=1**, with two differences: the neighbour feature vector is not
target-masked, and neighbours are drawn from the **full dataset** before a random
`KFold` — so test samples appear in training samples' neighbour lists. With 25.6% of
neighbours at exactly 0 m, that number is not a clean estimate. The help text in that
code flags the risk without closing it.

The current pipeline uses train-only lookup, consistent masking, `k` as a parameter,
and four explicit encodings.

---

## Next steps

**Immediate — RQ1 to its endpoint:**
- **Re-implement the neighbour-only diagnostic** as a notebook cell (own / neighbour-only
  / target-only / coordinates), so the exploratory numbers above become project results.
- Add **own + coordinates** as a baseline row (isolates position from neighbourhood).
- Build the **GNN**: nodes = samples, edges = the existing k-NN graph, target masked.
  Reuse the same folds and `AggregateFolds` so results drop into the current table.
- Make edges **distance-aware** — since coordinates outrank neighbour chemistry, a
  model ignoring edge distance discards the stronger signal.
- Sweep `k ∈ {1,3,5,10,20}` (no new neighbour search needed — 20 are already stored).

**Scoping — RQ2 geophysics.** Neighbours will be absent in unexplored areas, so
complete-coverage physical fields replace them. Verified accessible on GEUS Dataverse
(the `geusmap/ows` WFS/WMS endpoint in the old notes now returns 404):

| feature | dataset | licence |
|---|---|---|
| Magnetic anomaly (400 m grid, UTM 24N) | GREENMAG `doi:10.22008/FK2/LQN5YJ` | CC-BY 4.0 |
| Bouguer / isostatic / tilt-derivative gravity | NAG-TEC `doi:10.22008/FK2/AQ38FS` | CC-BY 4.0 |
| Geothermal heat flow (10 km) | `doi:10.22008/FK2/F9P03L` | CC0 |
| Moho / basement / crustal thickness | `doi:10.22008/FK2/TG7OQU` | CC-BY 4.0 |
| Sediment thickness | `doi:10.22008/FK2/P9XHV9` | CC-BY 4.0 |
| Subglacial geologic provinces (categorical) | `doi:10.22008/FK2/BUQQ9C` | CC0 |
| Airborne radiometrics (K, U, Th) — West Greenland only | `doi:10.22008/FK2/0JIMQO` | — |

GREENMAG verified end-to-end: **100% of the 6,957 samples fall inside the grid**, it is
already in UTM 24N (no reprojection), and sampled values are physically sensible
(−210.9 … 768.9 nT). Sampling is integer arithmetic on the `.flt` via `np.memmap`.

---

## Open questions

- Does the flat A–D result survive **spatial** CV, or is it specific to random folds?
  (RQ2 territory — block-based splits, with block size in km as an interpretable
  parameter, are preferred over KMeans, whose clusters follow sampling density.)
- Does a GNN with learned, distance-weighted aggregation beat the hand-specified
  encodings, or does it confirm the ceiling?
- Do the geophysical grids add signal *beyond* raw position? To be tested once the
  neighbour-only diagnostic exists in the notebook.
