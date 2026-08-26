# Project Summary

**Author:** Salvador Palma · Copenhagen University
**Project Outside Course Scope (15 ECTS)** · Supervisor: Bulat Ibragimov
**Last updated:** 2026-08-26

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

**Working conclusion for RQ1 (so far):** neighbour encodings add nothing beyond a fold
standard deviation, under two models, with and without co-located neighbours. Whether
that is because spatial context is genuinely uninformative here, or because it is
redundant with a sample's own co-measured chemistry, is not yet distinguished — see
Next Steps.

### K-sweep — how many neighbours?

Mean R² over the 10 elements, HGB, co-located neighbours excluded. Baseline (no
neighbours) is 0.8392; typical fold std is 0.0113.

| k | A (+1 col) | B (+k cols) | C (+68 cols) | D (+68k cols) |
|---|---|---|---|---|
| 1 | 0.8404 | 0.8404 | 0.8408 | 0.8408 |
| 3 | 0.8415 | 0.8415 | 0.8435 | 0.8395 |
| 5 | 0.8421 | 0.8421 | 0.8452 | 0.8386 |
| 10 | 0.8423 | 0.8421 | 0.8469 | 0.8375 |
| 20 | 0.8424 | 0.8415 | **0.8490** | 0.8352 |

Two clean trends, in opposite directions:

* **C improves monotonically with k** (0.8408 → 0.8490). Averaging every element over more
  neighbours smooths out sampling noise without adding columns — C stays at 68 features
  whatever k is. Best overall, +0.0098 over baseline at k=20, which is just under one fold
  standard deviation.
* **D degrades monotonically with k** (0.8408 → 0.8352). It is the same information, but
  spread over 68k columns — 1,360 at k=20. The decline tracks the column count, confirming
  the A–D pattern is feature dimensionality rather than geology.

A and B plateau by k≈5: both are target-only encodings, so extra neighbours add little.

Even the best cell is inside one fold standard deviation of baseline, so the headline
conclusion is unchanged: **neighbour features are not adding usable signal at any k.**
What the sweep does establish is that the shape of the A–D result is an aggregation-versus-
dimensionality effect, and that if a neighbourhood is used at all it should be pooled
(variant C), not enumerated (variant D).

---

## Geophysical features (`1. Data Fetching.ipynb`)

Geochemical neighbours only exist where somebody has already sampled. Geophysical grids are
measured everywhere, so they are what replaces the neighbourhood on unexplored ground — the
RQ2 substitute. Attached to `Data.csv` before the splits, since they are static per coordinate
and carry no train/test dependence.

**Inclusion rule: full Greenland coverage**, checked over the whole landmass rather than over
the samples at hand, so the same columns attach to any future sample set (stream sediment,
heavy minerals) unchanged.

| column | source | grid | licence |
|---|---|---|---|
| `geo_magnetic_anomaly nT` | GREENMAG `doi:10.22008/FK2/LQN5YJ` | 400 m, native UTM 24N | CC-BY 4.0 |
| `geo_heat_flow mW/m2` | Heat Flow `doi:10.22008/FK2/F9P03L` | ~0.4° (~25 km) | CC0 |
| `geo_depth_to_moho km` | Depth to Moho `doi:10.22008/FK2/TG7OQU` | ~0.5 km spacing | CC-BY 4.0 |

All three are 100% valid at the 6,957 samples. Magnetic anomaly spans −472…840 nT, heat flow
32.9…117.7 mW/m², Moho depth 27.7…46.6 km.

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
and four explicit encodings.

---

## Next steps

**Next session — feature-source ablation.** Run the same 10 elements and 5 folds under
HGB, varying only what goes into `X`, so each source can be scored on its own and in
combination:

| feature set | question it answers |
|---|---|
| own chemistry (current baseline) | the reference, 0.8392 |
| geophysics only | how much do the three grids carry alone? |
| coordinates only | how much is plain position worth? |
| neighbours only | how much is the neighbourhood worth without own chemistry? |
| own + geophysics | do the grids add anything on top of chemistry? |
| own + coordinates | does position add anything on top of chemistry? |
| geophysics vs coordinates | **the key test** — is geophysics real physics or a position proxy? |

The last row matters most. Moho depth is r=0.75 with northing, and only 42% of elements
correlate with a geophysical field more strongly than with a coordinate. If geophysics
scores no better than raw x/y, the honest reading is that these grids encode *where you
are*, not *what is underfoot* — which changes how RQ2 gets framed.

Report per element as well as pooled: the correlation table suggests U is where geophysics
should help most, and a pooled mean would hide that.

**After that — RQ1 to its endpoint:**
- Build the **GNN**: nodes = samples, edges = the existing k-NN graph, target masked.
  Reuse the same folds and `AggregateFolds` so results drop into the current table.
- Make edges **distance-aware**. The k-sweep showed pooling over more neighbours (variant C)
  beats enumerating them (variant D), which is exactly the argument for learned aggregation
  over hand-specified columns — and a GNN that ignores edge distance is just variant C.
- Consider **stream sediment** (~2× the samples, more spatially diffuse) as a replication
  check once RQ1 is closed on whole rock.

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
