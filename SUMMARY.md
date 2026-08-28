# Project Summary

**Author:** Salvador Palma · Copenhagen University
**Project Outside Course Scope (15 ECTS)** · Supervisor: Bulat Ibragimov
**Last updated:** 2026-08-28

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
| unique coordinate pairs | 4,498 | 16,542 |
| samples sharing a coordinate | 3,458 (**50%**) | 1,759 (**10%**) |
| max samples at one coordinate | 67 | 11 |
| longitude span | −53.9 … −42.3 | **−72.8 … −13.3** |

The two differ in a way that turned out to matter: whole rock is clustered,
exploration-driven sampling in a narrow longitude band; stream sediment covers the whole
island with a fifth of the co-location. **Co-location is real and kept in both** — 67
samples at one outcrop is genuine sampling density, not duplication.

Stream sediment's 523 raw element columns are 93 elements measured by up to four
lab/method combinations each (`ACTLABS FUS ICP Ni ppm`, `ACTLABS INAA Ni ppm`, …). Whole
rock already has one column per element.

**Provenance note.** Bulat's `geochem_stream.csv` (69,720 rows, 15,398 samples) and
`clean_stream.csv` (14,831 samples) are the same data in long format and merged form.
All 15,398 of his samples are in the portal export used here, none are missing from it,
and shared-sample values agree (r=0.92 on Ni). The portal export is used because it has
2,065 more samples and a known origin.

### Column schema

Each source csv now carries a `<name>.json` beside it naming `sampleCol`, `metaCols`,
`physicalCols` and `locationCols`. Element columns are whatever is left over, so a new
dataset needs no code change — only the schema file and three constants.

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

**Working conclusion for RQ1, whole rock:** neighbour encodings add nothing beyond a fold
standard deviation, under two models, with and without co-located neighbours.

> **Since qualified by the stream sediment run below.** This holds for whole rock, whose
> sampling is clustered (50% co-located, narrow longitude band). It does *not* generalise:
> on stream sediment the same encodings give a gain of 2.5 standard deviations.

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

Even the best cell is inside one fold standard deviation of baseline, so on **whole rock**
neighbour features are not adding usable signal at any k. What the sweep establishes and
which does carry over to stream sediment: the A–D shape is an aggregation-versus-
dimensionality effect, and a neighbourhood should be pooled (variant C), not enumerated
(variant D).

### Stream sediment — the same pipeline on differently-sampled data

Whole rock's spatial ceiling could have been a property of Greenland geochemistry, or a
property of clustered exploration sampling. Stream sediment separates the two: 17,463
samples across the whole island, 10% co-located instead of 50%.

Targets are the 10 best-covered elements, which for stream are `Zn, U, Cu, Rb, Ba, Cr, Sr,
Fe %, V, Co` — a different set from whole rock's oxide-heavy list, so the two datasets
compare in aggregate rather than element-for-element. Fold std ≈ 0.012 on both.

**Neighbour features, k=5, co-located excluded:**

| variant | whole rock | Δ | stream | Δ |
|---|---|---|---|---|
| baseline | 0.8388 | — | 0.7988 | — |
| A | 0.8421 | +0.0033 | 0.8257 | **+0.0270** |
| B | 0.8421 | +0.0033 | 0.8212 | +0.0224 |
| C | 0.8452 | +0.0064 | **0.8285** | **+0.0297** |
| D | 0.8386 | −0.0002 | 0.8187 | +0.0199 |

On whole rock every gain sat inside one fold standard deviation. On stream, variant C's
+0.0297 is **2.5 standard deviations**, and even D — the worst encoding — clears one. This
is the first defensible neighbour gain in the project.

**K-sweep, variant C:**

| k | whole rock Δ | stream Δ |
|---|---|---|
| 1 | +0.0020 | +0.0221 |
| 5 | +0.0064 | +0.0297 |
| 20 | +0.0102 | **+0.0347** |

Monotone on both, and still climbing at k=20 on both — the plateau has not been found.

**Feature sets:**

| set | whole rock | stream |
|---|---|---|
| Chemistry | 0.8388 | 0.7988 |
| Physics | 0.3000 | 0.4712 |
| Location | 0.3145 | **0.5428** |
| Neighbours | 0.3150 | **0.5582** |
| Chemistry + Physics | 0.8442 | 0.8225 |
| Chemistry + Location | 0.8449 | 0.8271 |
| Physics + Location | 0.3288 | 0.5495 |

Three readings:

1. **The R² ≈ 0.30 spatial ceiling was a sampling artefact, not geology.** Every spatial
   source roughly doubled: neighbours 0.315 → 0.558, location 0.315 → 0.543. The earlier
   whole-rock conclusion should be qualified to "spatial context is weak *in clustered
   sampling*", not weak in Greenland geochemistry generally.
2. **Chemistry is weaker on stream** (0.7988 vs 0.8388). Stream sediment averages an
   upstream catchment rather than sampling one rock, so co-measured elements predict each
   other less tightly. Both effects push the same way: neighbours help more, and the
   baseline they help is lower. Worth stating both rather than only the first.
3. **Geophysics remains a position proxy, more clearly than before.** Location beats
   Physics by 0.072 on stream against 0.014 on whole rock, and Physics + Location (0.5495)
   barely exceeds Location alone. The three grids encode *where* a sample is rather than
   independently *what* is underfoot. Chemistry + Physics and Chemistry + Location both add
   ~+0.024–0.028, the same magnitude as neighbours — three routes to the same information.

---

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

**Next — the GNN, on stream sediment.**

The dataset choice is now settled by evidence rather than convenience. Whole rock offered
~0.31 of standalone spatial signal and gains inside the noise floor; stream sediment offers
**0.558** and a demonstrated +0.035 from hand-built pooling that is still climbing at k=20.
That is real headroom for a learned aggregation to compete for, and it is where a GNN has
something to win.

- Nodes = samples, edges = the existing k-NN graph, target masked. Same folds, same
  `AggregateFolds`, so results drop into the current tables.
- Edges **must carry distance**. The k-sweep showed pooling beats enumerating, which is the
  argument for learned aggregation over hand-specified columns — but a GNN that ignores edge
  distance is just variant C with extra machinery.
- **Extend the k-sweep** past 20 first. Variant C has not plateaued on either dataset, so
  the hand-built ceiling the GNN has to beat is not yet known.
- Re-run the whole-rock GNN afterwards for the contrast: same architecture, two sampling
  geometries.

**Then — widen the target set.** Every result so far uses the 10 best-covered elements, which
is an arbitrary cutoff rather than a principled one: on stream sediment ranks 11–20 have
12,469–13,354 samples against rank 10's 13,979, a 4% difference, and 71 of 87 elements have
at least 1,000 measurements. Replace `top_n=10` with a coverage threshold
(`MIN_TARGET_COVERAGE = 1000` gives 48 elements on whole rock, 71 on stream).

This does **not** bias the neighbour-versus-baseline comparison, since both arms see the same
elements. It does bias any claim about *which feature source* helps: the correlation analysis
found geophysics tracks U most reliably, and U is not in whole rock's top 10 — so
"Physics 0.3000 vs Location 0.3145" was averaged over ten elements that largely exclude the
ones geophysics should help. Stream's top 10 does include U, which may be part of why Physics
rose to 0.4712 there.

Rerun the **feature-set ablation** on the wider set before the geophysics conclusion goes in
the report, and report the per-element distribution rather than only a pooled mean — "physics
helps U, Th, Zr, Nb and does nothing for the major oxides" is a stronger and more honest
finding than one averaged number. Keep the k-sweep at top-10; it is the expensive one.

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

- **Everything so far is random CV**, where train and test are interleaved in space and
  position is therefore unusually informative. Location scoring 0.543 on stream should be
  expected to collapse under spatial CV. Whether Physics holds up better than Location there
  is the test that would settle whether the grids carry real physics — under spatial CV the
  "position proxy" reading could invert.
- Does the flat A–D result survive **spatial** CV, or is it specific to random folds?
  (RQ2 territory — block-based splits, with block size in km as an interpretable
  parameter, are preferred over KMeans, whose clusters follow sampling density.)
- Does a GNN with learned, distance-weighted aggregation beat the hand-specified
  encodings, or does it confirm the ceiling?
- Do the geophysical grids add signal *beyond* raw position? To be tested once the
  neighbour-only diagnostic exists in the notebook.
