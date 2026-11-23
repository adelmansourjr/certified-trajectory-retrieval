# Protocol, frozen before the final runs

Question: can a coarse movement vocabulary order candidates more efficiently than
strong numerical lower bounds without silently changing the answer to an exact
trajectory-similarity query?

The goal is a trustworthy retrieval component, not a new foundation model or a
claim of human-like reasoning. This tests a concrete part of Amilcar Soares's
advertised *From Trajectories to Meaning: Symbolic Learning for Movement Data*
project. MoCo-AIS (Song et al., 2026, arXiv:2606.17978v2) studies vessel embeddings;
this experiment uses **real pen movements**, so cannot establish maritime transfer
or reproduce MoCo-AIS.

## Data and split

UEA CharacterTrajectories version3 (November2023), a repackaging of the UCI real
handwriting trajectory data. Archive SHA256 is recorded in study.py. Use the
official TRAIN only to fit channel means/standard deviations and form catalogues.
All trajectories are interpolated to48 steps, then standardized using TRAIN
statistics. Ten examples from each of20 characters form each200-item catalogue.

Development uses20 official TEST trajectories belonging to character labels1–10.
Final evaluation uses40 queries belonging to labels11–20 per seed. Thus final
query morphologies are excluded from tuning. Catalogue membership still includes
all characters: **this is not a claim of zero-shot class recognition**. Labels
balance the sampling and split development/final queries; no ranking function
receives labels. There are three preselected catalogue/query sampling seeds,
2026112301–2026112303. Individual row indices are saved.
UCI states that all recordings are from a **single writer**; there is no
cross-writer, sensor, region or real-world deployment validation. The original
dataset is CC BY4.0, attributed to Ben Williams, DOI10.24432/C58G7V. Downloaded
archive is excluded from the project repository.

## Matched methods

All exact methods use the same compiled squared-Euclidean multivariate DTW backend,
Sakoe-Chiba radius6, lexicographic tie handling, early abandoning, and identical
candidate catalogue. Exactness is measured against exhaustive DTW on that same
query, not a class label or a model-generated answer.

1. Exhaustive exact DTW, no pruning, numerical oracle.
2. Symmetric LB_Keogh candidate ordering.
3. Symmetric two-pass LB_Improved candidate ordering, a stronger published bound.
4. Raw Euclidean candidate ordering.
5. Movement-vocabulary ordering: six block means plus eight velocity-direction
   symbol frequencies and64 adjacent-symbol frequencies. The vocabulary weighting
   is chosen from0,1,10,100 using development DP-cell cost only.

Methods2–5 share **the same stronger LB_Improved pruning**, isolating candidate
ordering rather than conflating the bound and representation. Symbol scores are
never used as admissible bounds. Also report approximate vocabulary-only top1
agreement to show what certificates correct. No model weights are downloaded.
Dataset labels are used only for sampling/stratification, never candidate ranking.
LB_Improved is due to Lemire2009; this project does not claim
to invent it, or to beat optimized contemporary DTW libraries.

## Final conditions and endpoints

Preselected clean, monotone timewarp (lognormal increment sigma0.65), additive
noise (standardized channel sigma0.12), and their composition. These are measured
perturbations of real trajectories. The composition is of observation nuisances;
it does not demonstrate learned composition of movement primitives. Query variants
are paired across all methods; method execution order is randomized.

Primary:100% exact top1 agreement for every certified method, and whether symbolic
ordering reduces mean DP cells by at least10% against LB_Improved ordering **in
every condition**. The efficiency ratio is the aggregate symbolic DP-cell count
divided by the aggregate LB_Improved-order count within each condition (equivalently,
the ratio of means). The mean of paired per-query ratios is a separate descriptive
quantity and is **not** the primary gate. If it fails, report failure, including all conditions/seeds.
Secondary: DTW call count, wall time including bounds/feature computation/sorting,
catalogue preprocessing time, and approximate top1 recall. Timings share one
compiled backend and exclude compilation/data parsing for every method; report
those setup costs separately in run metadata. No claims of CPU-clock speedup
based solely on DP cells. First compiled-call warmup occurs in development, and
all final timing orders are randomized.

Three seeds are not sufficient for strong population inference. Any cluster
bootstrap interval over seed means is descriptive, explicitly labelled. Report
paired per-query raw measurements; avoid a tiny p-value from treating perturbed
copies or reused query IDs as independent observations. No hyperparameter changes
after reading final results; further experiments need a fresh labelled protocol.

## Exactness argument

For band widthr, every query point must pair with a candidate point inside its
r-envelope. Its squared distance to the envelope is no greater than its
contribution along any legal DTW path; summing yields LB_Keogh. The published
two-pass projection construction yields LB_Improved; coordinate-wise lower
bounds sum safely because every coordinate shares the same multivariate path.
Take the maximum of both directions and the mandatory endpoint cost, not their
sum. Maintain incumbent exact distanceU. Discard a candidate only when its lower
bound exceedsU with numerical slack. No discarded candidate can improveU, so
the exhaustive answer is unchanged regardless of symbolic ordering. Strict
pruning and stable index tie breaks retain deterministic ties. This is a known
finite-search guarantee, not a guarantee of semantic relevance or generalization.

Tests exhaust all81 length4 ternary sequences across all radii for the projection
bound, test randomized3D cases against an independent DP implementation, verify
early abandonment and duplicate/zero/adversarial query ties.

## Sources

- Advert: https://www.findaphd.com/phds/project/from-trajectories-to-meaning-symbolic-learning-for-movement-data/?p202574
- Current Bristol profile: https://www.bristol.ac.uk/people/person/Amilcar-Soares-2550d802-e82a-4ea6-93ef-65f89b205e5e/
- MoCo-AIS original: https://arxiv.org/abs/2606.17978v2
- UCI data source: https://archive.ics.uci.edu/dataset/175/character+trajectories
- UEA dataset archive: https://www.timeseriesclassification.com/aeon-toolkit/CharacterTrajectories.zip
- Two-pass bound, Lemire2009: https://arxiv.org/abs/0811.3301
- Stronger modern bound context (not reproduced): https://arxiv.org/abs/2102.07076
