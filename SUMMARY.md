# Project Summary

**Author:** Salvador Palma · Copenhagen University
**Project Outside Course Scope (15 ECTS)** · Supervisor: Bulat Ibragimov
**Last updated:** 2026-09-06

Running log of the hand-built work in `Project/`. Appended as the project advances.

> **Starting a new session? Read this first.**
>
> * Everything in `Project/` is hand-built and is the work being assessed. The workspace
>   *root* holds two vibe-coded predecessors (Bulat's `gui.py` GUI and a `greenland_ml/`
>   package) — reference only, not part of this project, and their `report/report.pdf`
>   answers a different question (see *Comparison to prior code*).
> * Three notebooks, run in order: `1. Data Fetching` → `2. Random Forest` → `3. GNN`.
>   Switching dataset means changing three constants (`DATA_TYPE`, `MERGE_TYPE`,
>   `SOURCE_CSV`) and nothing else.
> * Results cache to `Results/<DATA_TYPE>/<MERGE_TYPE>/`. Every experiment checks the cache
>   first, so a rerun is near-instant unless the file is missing.
> * **Every number below is random 5-fold CV.** Spatial CV is RQ2 and is not built yet.
>   Do not present these as spatial-generalisation results.

---

## Research questions

| RQ | Question | Status |
|---|---|---|
| 0 | Parse GEUS exploration reports with public AI models | **dropped** — supervisor deprioritised |
| **1** | **Predict a held-out element from a sample's other elements (random CV)** | **~90% done** |
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

## Feature-source ablation (`2. Random Forest.ipynb`)

Same 10 elements, same 5 folds, same model — only the contents of `X` change. Stream
sediment, random CV.

| feature set | mean R² | vs chemistry |
|---|---|---|
| **Chemistry** (68 own elements) | **0.7988** | — |
| Physics (3 geophysical grids) | 0.4712 | −0.3276 |
| Location (UTM x, y) | 0.5428 | −0.2560 |
| Neighbours (variant C, k=20) | 0.5582 | −0.2406 |
| Chemistry + Physics | 0.8225 | +0.0237 |
| Chemistry + Location | 0.8271 | +0.0283 |
| Physics + Location | 0.5495 | −0.2493 |

Three readings:

1. **The three spatial sources are interchangeable.** Physics 0.471, Location 0.543,
   Neighbours 0.558 — three quite different encodings of "where am I" landing in the same
   band. That looks like a ceiling on how much spatial information exists, regardless of how
   it is expressed, and it explains why the A–D table and the k-sweep are both flat.
2. **Geophysics does not beat plain coordinates.** Location outscores Physics by 0.072, and
   Physics + Location (0.5495) barely exceeds Location alone. On this evidence the grids
   encode *where* a sample is rather than independently *what* is underfoot.
3. **Everything adds about the same on top of chemistry** — +0.024 for physics, +0.028 for
   coordinates, +0.030 for neighbours. Three routes to what appears to be the same
   information.

> **Reading 2 is conditional on random CV and is the single most likely conclusion to
> change.** Coordinates are unusually strong when train and test are interleaved in space.
> Under spatial CV they should collapse while the geophysical grids — real measurements
> available at every point — should not. Task 5 in the list below is this test.

---

## Graph neural network (`3. GNN.ipynb`)

Built on stream sediment, because that is where the headroom is: 0.558 of standalone spatial
signal against whole rock's 0.315.

**Design.** Nodes = samples. Edges = the same train-only k-NN mapping the KNN variants use,
so the network sees exactly the neighbourhood the hand-built columns saw. Node features are
the sample's own elements with the target removed, each element contributing two columns —
standardised value (zero when missing) and a present/absent flag, since a network cannot
consume NaN and needs to tell "average" from "not measured". Standardisation uses training
rows only. Full-batch transductive training, early stopping on a validation slice carved out
of *training* nodes.

**Two architectures, and the contrast was the experiment:**

* `GATConv(edge_dim=1)` — attention weights computed per edge **from the distance**, so the
  network learns how fast a neighbour stops mattering. This is the one thing variants A–D
  structurally cannot encode.
* `SAGEConv` — distance-blind control.

### Results (stream sediment, k=10, 5 folds, 10 elements)

| model | mean R² | vs baseline | vs KNN C |
|---|---|---|---|
| Baseline (chemistry only) | 0.7988 | — | −0.0297 |
| **KNN C (hand-built)** | **0.8285** | +0.0297 | — |
| GNN GAT | 0.8226 | +0.0238 | −0.0059 |
| GNN SAGE | 0.8225 | +0.0237 | −0.0060 |

**The GNN beats the baseline but loses to the hand-built columns**, recovering about 80% of
the available neighbour gain.

**GAT and SAGE are identical** — 0.8226 vs 0.8225, against a fold std of ~0.010, with GAT
winning on 5/10 elements. Distance-aware attention adds nothing. A single CPU test earlier
had suggested otherwise (GAT 0.790 vs SAGE 0.768 on one element, one fold); across 5 folds
and 10 elements that gap evaporates, and the single measurement should not have been leaned
on.

**The uranium exception, again.** U ppm: baseline 0.594 → KNN C 0.800 → **GNN GAT 0.816**.
A +0.22 jump from neighbours and the only element where the GNN clearly beats the hand-built
version. This is the third independent appearance of the same finding — U also has the only
reliable geophysical correlations (+0.28 magnetics, −0.34 Moho, n=3227), and the predecessor
report found U to be the one element where neighbours help under *spatial* CV
(0.472 → 0.578). Two pipelines, two CV schemes, same exception, same geological explanation:
South Greenland uranium districts are coherent at a scale that survives spatial separation.

**Working conclusion.** Three independent lines now agree: four hand-built encodings plateau
at +0.03, a learned aggregation reaches +0.024, and distance-awareness contributes nothing.
The spatial information in this data appears to be exhausted by averaging nearby samples'
chemistry. Caveats: the GNN is untuned (one hidden size, one learning rate), and this is
random CV.

**Ran on Colab (T4)** — ~5 min per architecture against ~5.3 h on CPU. The Drive mirror at
`MyDrive/UCPH/POOCS/` holds `GreenlandUtils.py`, the schema json, `Data.csv`, `5-Fold.kfold`
and slimmed reference results (prediction arrays stripped, 9.5 MB → 1.4 KB each).

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

## Task list

Ordered. Steps 1–2 finish RQ1 and are compute-bound rather than design-bound; steps 3–8 are
RQ2 and are the real remaining work.

### RQ1 — finish (about half a day, mostly waiting)

**1. Widen the target set to a coverage threshold.**
Every result so far uses the 10 best-covered elements, which is an arbitrary cutoff: on
stream sediment ranks 11–20 have 12,469–13,354 samples against rank 10's 13,979, a 4%
difference, and 71 of 87 elements have at least 1,000 measurements. Replace `top_n=10` with
`MIN_TARGET_COVERAGE = 1000` (48 elements on whole rock, 71 on stream) in cell 5 of
`2. Random Forest.ipynb`.

Rerun **baseline + feature-set ablation only**. Keep the k-sweep at top-10 — it is the
expensive one and nothing about it depends on the target set.

This does *not* bias the neighbour-versus-baseline comparison, since both arms see the same
elements. It **does** bias any claim about which feature source helps: geophysics tracks U
most reliably, and U is absent from whole rock's top 10. Report the per-element distribution,
not only a pooled mean — "physics helps U, Th, Zr, Nb and does nothing for the major oxides"
is a stronger finding than one averaged number.

**2. Add `physicalCols` to the GNN node features.**
Two lines in `BuildNodeFeatures` in `3. GNN.ipynb`; one Colab run (~10 min). Currently the
GNN is chemistry-only, which made GNN-vs-KNN-C a clean comparison but leaves one cell of the
2×2 empty:

| | chemistry only | + physics |
|---|---|---|
| tabular | 0.7988 | 0.8225 |
| + neighbours | 0.8285 (KNN C) | — |
| GNN | 0.8226 | **?** |

Do this **after** step 1 so both use the same element list.

### RQ2 — build

**3. Implement spatial block folds.**
Hash UTM coordinates into squares of side `blockKm`, assign whole blocks to folds. About ten
lines; the logic already exists at `greenland_ml/data/spatial.py:99` in the root package.
Write as `Spatial-{km}km.kfold` in the same format as `5-Fold.kfold` so `ReadKFold` picks it
up unchanged and every downstream notebook works without modification.

Blocks are preferred over KMeans: block size in kilometres is an interpretable parameter,
whereas KMeans clusters follow sampling density — carving small clusters out of dense regions
and large ones out of sparse regions, confounding fold difficulty with geography.

**4. Sanity-check the fold geometry before trusting any result.**
Print fold sizes and the minimum distance from each test sample to its nearest training
sample. If one fold holds 60% of the data the mean-across-folds is misleading and pooled R²
is the right statistic. This step is cheap and catches a silent failure mode.

**5. Rerun the core table under spatial CV.**
Baseline, KNN C, and the full feature-set ablation. **This is the step that can change a
conclusion, so do it early.**

Under random CV, Physics (0.4712) scored *below* Location (0.5428), which reads as "the
geophysical grids are a position proxy". That reading is conditional on the CV scheme:
coordinates are unusually strong under random CV because train and test are interleaved in
space. Under spatial CV a model that learned "northing 7.2M → high U" is useless when that
whole band is held out, while magnetic anomaly remains a real measurement at every point.
**If the ordering inverts, that is the headline RQ2 result** — and it is exactly the
"geologically relevant angle" Bulat asked for. Do not drop geophysics on the random-CV
evidence.

**6. Block-size sweep, `blockKm ∈ {10, 25, 50, 100, 200}`.**
Plot R² against block size. A degradation curve is a better deliverable than any single
number: it shows the distance over which the model generalises, which is the quantity a
geologist actually wants.

**7. GNN under spatial CV**, best configuration only. Do not sweep architectures again — GAT
and SAGE agree to four decimal places, and that is a property of the data rather than a
tuning problem.

**8. Geological province hold-out.**
The stricter test Bulat actually described: *"select a geological area outside the one we used
for training"* — a coherent terrane, not an arbitrary square. Subglacial geologic provinces
are published as a GeoPackage (`doi:10.22008/FK2/BUQQ9C`, CC0) and would need `geopandas`.
If time runs short this is the one to cut, but say so explicitly in the report rather than
omitting it silently.

### Framing RQ2: two scenarios, not one

Worth designing for deliberately. "Predict a held-out region" splits into two questions the
same table can answer, because the feature sets already exist:

| feature set | scenario |
|---|---|
| Chemistry | new region, sample collected, partial analytical suite |
| Chemistry + Physics | same, geologically enriched — **the primary RQ2** |
| Neighbours | region has some prior sampling nearby |
| Physics | **genuinely blank terrain, nobody has been there** |
| Physics + Location | same, with position |

Bulat's phrasing implies the first: the samples exist and the region is withheld. The
Physics-only row is the honest lower bound on what can be said about ground with no samples
at all, and is worth reporting precisely because it will be low.

### Write-up

**9. The random-vs-spatial figure.** Mean R² per model under both CV schemes, side by side.
This is the single most communicative figure the project will have, and it is the one the
predecessor report leads with (its Figure 3).

**10. Keep this file current** as results land.

---

## Open questions

* **Everything so far is random CV.** Train and test are interleaved in space, so position is
  unusually informative. The Location = 0.543 result in particular should be expected to
  collapse under spatial CV, and the "geophysics is a position proxy" reading could invert.
  This is task 5.
* Does the flat A–D result survive spatial CV, or is it specific to random folds? The
  predecessor report suggests it does not survive in the same form: its neighbour gain goes
  from +0.047 under random CV to +0.003 under 50 km blocks.
* Is uranium exceptional, or the visible tip of a pattern across the trace elements? The
  widened target set (task 1) answers this — U is currently the one element where spatial
  context clearly pays, and it appears in three independent analyses.
* Would per-commodity occurrence labels be viable? `mineral_occurrences_v3_external` carries
  commodity attributes, but 1,167 positives fragment across classes. Relevant only if the
  project later extends toward prospectivity — **not part of RQ2 as Bulat defined it.**

---

## Environment notes

* Python 3.14, Windows. `sklearn` 1.9, `torch` 2.12 (CPU), `torch_geometric` 2.8,
  `xgboost` 3.4.1. No `geopandas`, `rasterio` or `tifffile` — task 8 needs the first.
* Geophysical rasters live in `Project/Data/Geophysics/` (~250 MB, gitignore-worthy):
  `GREENMAG_magnetic_anomaly.flt/.hdr`, `GeothermalHeatFlow.xyz`, `DepthToMoho.xyz`.
  Download URLs are in the markdown of `1. Data Fetching.ipynb` cell 8.
* GPU work runs on Colab against `MyDrive/UCPH/POOCS/`. `3. GNN.ipynb` ships with
  `COLAB_SESSION = True`; set it to `False` to run locally.
* The `!pip install` cell at the top of notebooks 2 and 3 is a notebook magic, so a plain
  `ast.parse` of that cell fails. Expected, not a bug.
