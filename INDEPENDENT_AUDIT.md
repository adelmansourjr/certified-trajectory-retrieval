# Independent methodological audit

Date: 23 November 2026. Reviewer: separate agent from the implementation agent.
Status before final evaluation: **cleared for the frozen final run**. This is a code/protocol review and a finite test audit, not independent confirmation of novelty or real-world generalization.

## Scope reviewed

Reviewed `PROTOCOL.md`, `protocol_lock.json`, `study.py`, `dtw.c` and `test_study.py` before final data were evaluated. Final query classes11–20 were excluded from development queries; all candidate catalogues and normalization statistics come from official TRAIN. Catalogue examples from all classes are allowed for retrieval and do not establish unseen-class learning. Symbolic summaries rank candidates, never act as admissible bounds.

The matched strong comparator is symmetric two-pass LB_Improved ordering with the same LB_Improved pruning and compiled DTW backend used by symbolic, Euclidean and LB_Keogh ordering. Exhaustive DTW provides the metric oracle. The shared pruning backend isolates ordering quality. This does not compare with optimized contemporary DTW libraries or constitute a state-of-the-art benchmark.

## Issues corrected before final evaluation

1. The original summary used mean per-query cell ratios while the protocol asked for reduction in mean DP cells. The implementation and frozen protocol now identify **ratio of aggregate DP cells**, equivalently ratio of mean cells, as the primary efficiency endpoint. Mean paired ratios remain descriptive. Success requires at least10% fewer cells in every condition, alongside complete exact-nearest-neighbour agreement.
2. Catalogue envelope construction and symbolic-feature construction now have separate setup timings. Query timings already include bound calculation, query features, sorting and actual search. Parsing/resampling, normalization and compiled-backend setup are also recorded separately. All preprocessing must be considered before making end-to-end efficiency claims.

## Independently executed checks

- Re-executed the four supplied unit tests: all passed, including exhaustive ternary-sequence bound tests and comparison with an independent dynamic program.
- Wrote and executed an additional independent full-matrix dynamic program, without calling the implementation's reference test function.
- Compared compiled distances on **864 additional trajectory pairs**, with random trajectories, constant trajectories, cumulative random walks, and duplicate/near-tied candidates. Repeated at amplitudes1e-6,1 and1e6.
- Checked all864 two-pass bounds against those independent exact distances. Largest relative numerical excess was1.31e-15, within the search's declared pruning slack.
- Checked **144 exact searches** over these adversarial catalogues against independent oracle identities/distances: all passed.
- These checks used short trajectories and small catalogues; no model was loaded and memory use remained modest.

## Limits and interpretation requirements

- An admissible bound plus complete exact search preserves the nearest neighbour for the specified resampled, standardized, band-constrained squared-Euclidean DTW metric. It does not guarantee semantic relevance, maritime transfer, learned movement composition, or human-like reasoning.
- Pen data come from one writer. Artificial timewarp/noise stress conditions are useful controlled perturbations, not cross-writer or deployment validation.
- The same query can recur across conditions/catalogue seeds. Raw query IDs and paired measurements must remain available; three-seed bootstrap intervals are descriptive and cannot establish broad population inference.
- DP-cell reduction and wall-clock reduction are separate claims. Bound computation, Python/ctypes overhead, catalogue setup and feature construction may outweigh cell savings.
- The selected symbolic weight was1.0 versus0.0 on development with only22 fewer cells in total. This tiny difference supplies no evidence of a substantial vocabulary contribution by itself.
- Do not alter hyperparameters or select conditions after seeing final results. Report every condition and the frozen success/failure gate. A negative result is still a useful, reproducible engineering audit.

Final-result audit will be appended after the implementation agent completes the locked run.

## Final-result verification

Completed after the locked final run. Reviewed all2400 rows and recomputed the summary/gate directly from `results/raw.jsonl`. Every returned identity **and distance** agrees with its stored exhaustive result:1920 certified-method answers over480 final queries, plus480 exhaustive-oracle rows. Source hashes in metadata match the evaluated source files. Split indices reproduce exactly and development/final query IDs are disjoint.

Independently reconstructed24 final queries, selecting the first and last sampled query for each of the three seeds and four conditions. Replayed perturbation RNG and verified **all4800 candidate distances with a separate full-matrix dynamic program**, confirming the recorded nearest identity and distance on every selected query. This subset check is additional to the implementation agent's full-oracle verification. Machine-readable findings are in `results/independent_audit.json`.

The frozen symbolic-efficiency hypothesis **failed** in every condition. Aggregate symbolic/strong-LB_Improved-order DP-cell ratios are:

| Condition | Cell ratio | Consequence |
|---|---:|---|
| Clean |1.1108|11.1% more cells|
| Timewarp |1.1845|18.4% more cells|
| Noise |1.0679|6.8% more cells|
| Composed |1.0966|9.7% more cells|

The admissible backend preserved exact answers; it did not establish a symbolic-ordering advantage. Large reductions in DP cells relative to exhaustive DTW must not be advertised as a new symbolic contribution or wall-clock speedup. In this small200-candidate setting, the recorded Python bound overhead makes pruning slower than exhaustive compiled DTW. Keep this negative result prominent in the README, email and CV rather than calling the pilot a breakthrough.

Final audit status: **methodologically usable bounded retrieval audit, with a failed primary efficiency hypothesis**. It is suitable as evidence of careful implementation, strong-baseline comparison and honest empirical reporting; it does not supply a positive new research result.
