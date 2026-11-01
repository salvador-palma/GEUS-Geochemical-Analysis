# Tasks

## Part 1 — Whole Rock, random 5-fold CV

- [ ] Rewrite RQ1 sections for Whole Rock emphasis keeping Stream Sediment for robustness
- [ ] Rewrite RQ1 sections to emphasize Pierpaolo's elements and ratios both on tables and text
- [ (Experimental Done) ] Pierpaolo 80/20: train on Pierpaolo vs Pierpaolo + Whole Rock vs Whole Rock, test on same 20%
- [ ] E1 rock type as a short section (Optional)

## Part 2 — Pierpaolo, spatial block CV

- [ ] Create Block size and buffering functions
- [ ] Block-size S-sweep
- [ ] Performance vs distance to nearest training sample on specific Block-size
- [ ] Map of per-block accuracy
- [ ] Final zonation maps

## Part 2 — Notebook 6 steps

**0. Setup**
- [x] Load Pierpaolo `Data.csv` (8 elements + 7 ratios), `x_km`/`y_km`
- [x] Fix model to Part 1's best: HGB on Chemistry + KNN C

**1. Block size and buffer functions**
- [x] `SpatialFolds(df, blockKm)` (from E2)
- [x] `Buffer(train, test, bufferKm)`: drop training samples within `bufferKm` of any test sample
- [x] KNN features from the training fold only, excluding the test sample's own block (no leakage across the boundary)
- [x] Sanity plot: one fold's train/test map (`DisplayFold` from E2)

**2. Block-size S-sweep**
- [ ] Sizes e.g. `[1, 2, 5, 10, 20, 50]` km, with random CV as reference
- [ ] Loop size × fold × target and save to `Results/Pierpaolo/Spatial/S-Sweep_{s}.json`
- [ ] Plot mean R² vs block size, random CV dashed (the leakage gap)

**3. Performance vs distance**
- [ ] Pick one block size (e.g. 10 km)
- [ ] Per test sample, nearest training distance (`NearestTrainingKm`)
- [ ] Bin distances, R² per bin (pooled or a few key targets)
- [ ] Plot R² vs distance

**4. Per-block accuracy map**
- [ ] MAE per block at the chosen size (R² is meaningless for small blocks)
- [ ] Blocks as coloured squares on the map for one or two targets (Cu, Mo?)

**5. Zonation maps**
- [ ] Fit on all samples, predict on the grid (`BuildGrid` from E2), mask beyond `MAX_DISTANCE_KM`
- [ ] Map the 8 elements and 7 ratios (`DisplayMaps`), save to `Report/figures/`
- [ ] Optionally compare with kriging (E2: kriging wins at map distances)

## Report

- [ ] Geological explanations

## Polish

- [ ] Run GNN on Cov1000 set for Whole Rock focus
