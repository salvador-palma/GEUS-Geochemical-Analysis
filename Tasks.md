# Tasks

Estimated times; 1 day = 8 h.

## RQ1 (done)

- [x] Data pipeline: preprocessing both datasets + geophysics attachment (~2 days)
- [x] Model comparison: RF / HGB / XGB (~2 h)
- [x] KNN encodings A–D + vectorised rewrite (~1 day)
- [x] K-sweep, top-10, both datasets (~3 h)
- [x] Cov1000 target set + feature-set ablation (~4 h)
- [x] GNN: SAGE/GAT sweep, target-channel fix, settled config (~2 days)
- [x] Results notebook: difficulty bands, correlations, companion strength (~1 day)
- [x] E1 Specific Rock (~4 h)
- [x] Masked autoencoder (~4 h)
- [x] E2 Zonation Maps: kriging, IDW, HGB, GNN (~1 day)
- [x] Report draft, RQ1 sections (~3 days)

## RQ1 (to do)

- [ ] K-sweep on the full Cov1000 target set, both datasets (~4 h, mostly compute)
- [ ] Report fixes: §3.2 top-10 caveat, §3.7 target-set claim, broken "??" ref in §3.5 (~30 min)

## RQ2 (to do)

- [ ] Spatial folds at several block sizes (~2 h)
- [ ] Sanity check: fold sizes, distances, map plot (~1 h)
- [ ] Core comparison at one block size (~3 h, mostly compute)
- [ ] Block-size sweep (~4 h, mostly compute)
- [ ] GNN under spatial CV (~3 h, mostly Colab)
- [ ] Province hold-out, optional (~4 h)
- [ ] E2 into the report (~3 h)
- [ ] Write RQ2, Abstract, Discussion (~2 days)

## Totals

- Done: ~13 days (~103 h)
- To do: ~5 days (~40 h), ~36 h without the province hold-out
- Progress: ~72%
