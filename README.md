# Certified trajectory retrieval

Can a coarse movement vocabulary make exact trajectory retrieval cheaper without
silently changing its answer? This CPU study separates **candidate suggestions**
from **numerical verification**, then tests both on real handwriting movements.

The reliability check passed. The proposed symbolic efficiency gain did not.
Four pruned retrieval strategies each matched exhaustive DTW on all 480 evaluated
query variants. Symbolic ordering used **6.8–18.4% more DP cells** than the stronger
published lower-bound ordering, and this implementation was slower in wall time
than exhaustive compiled DTW on its small 200-item catalogues. These failures are
retained, not replaced with a better-looking synthetic task.

## Why this experiment

[Amilcar Soares's symbolic movement PhD advert](https://www.findaphd.com/phds/project/from-trajectories-to-meaning-symbolic-learning-for-movement-data/?p202574)
asks about interpretable movement representations. His coauthored
[MoCo-AIS paper](https://arxiv.org/abs/2606.17978v2) studies vessel-trajectory
similarity. This study addresses a narrower question: when a simple movement
representation proposes a neighbor, can an exact verifier retain the correct
answer, and does the representation actually save work against strong baselines?

It does not reproduce MoCo-AIS, train a symbolic learner, show human-like reasoning,
or establish a research breakthrough. It gives a finite exactness argument and a
reproducible, real-data negative result relevant to reliable movement retrieval.

## Frozen test

- Real UEA CharacterTrajectoriesv3:1422 official TRAIN and 1436 TEST trajectories,
  three measured channels, all from one writer. Source archive hash is locked.
- Train-only normalization; 200-item catalogue balanced across 20 characters.
  Development queries use character labels 1–10; final queries use labels 11–20.
  Catalogue includes all classes, so this is not zero-shot character recognition.
- Three fixed sampling seeds, 40 final queries per seed, four conditions: clean,
  monotone timewarp, additive noise, and their composition. That produces 480
  variants of 113 distinct source queries, not 480 independent people or behaviors.
- Fixed 48-step representation; multivariate squared-Euclidean DTW, band radius 6.
  All methods share the same compiled C backend and the same catalogue/query.
- Strong exact comparators: exhaustive DTW, symmetric LB_Keogh ordering,
  symmetric two-pass LB_Improved ordering, and raw Euclidean ordering.
  Every pruned method uses the same stronger bound to isolate candidate ordering.
- Coarse vocabulary: eight normalized velocity-direction symbols and adjacent
  transitions, plus six block means. A clean development split selected the
  vocabulary weight 1.0; the tiny 22-cell development difference versus weight 0
  is not evidence that symbols help.

See [the pre-final protocol](PROTOCOL.md), [locked settings](protocol_lock.json),
[independent audit](INDEPENDENT_AUDIT.md) and [data attribution](data/README.md).

## Results

The primary efficiency target was at least 10% fewer aggregate DP cells than
LB_Improved ordering in **every** final condition. It failed in all four.

Mean DP cells per query; lower is better:

| Condition | Exhaustive | Keogh ordering | Improved ordering | Euclidean ordering | Symbolic ordering |
|---|---:|---:|---:|---:|---:|
| Clean |116400|3844|3831|4232|4255|
| Timewarp |116400|3988|3978|4748|4712|
| Noise |116400|5208|5179|5541|5531|
| Composed |116400|5191|5169|5844|5668|

| Condition | Symbolic / Improved aggregate cells | Approximate symbolic top1 recall |
|---|---:|---:|
| Clean |1.111|41.7%|
| Timewarp |1.184|27.5%|
| Noise |1.068|45.0%|
| Composed |1.097|30.0%|

Approximate recall compares the vocabulary proposal with the exact DTW neighbor,
not a character label. Verification restored exact agreement in all 1,920 pruned
retrievals. That supports the known finite-search guarantee, not semantic quality.
Symbolic ordering slightly improved on Euclidean ordering in three conditions,
but lost to both published-bound orderings throughout; those comparisons are
all included rather than selecting the weaker comparator.

**DP work is not elapsed time.** Improved ordering cut DP cells by 95.6–96.7%,
yet its median query time was 5.46–5.60ms, versus 0.71–0.72ms for exhaustive compiled
DTW. Symbolic ordering took 5.65–5.79ms. Python/NumPy bound construction dominates
these short searches. No wall-time speedup is claimed. Shared backend loading
took 0.0006s, data parsing/resampling 0.238s, normalization 0.0025s; per catalogue,
envelope preparation took 0.0025–0.0027s and symbolic features 0.0009s. These are
separate from per-query timings, which include bounds, ordering and verification.

The full experiment took 11.86s and peaked at 110.3MiB resident memory on this
machine. No neural model was downloaded or loaded. Three seed clusters support
descriptive summaries only; the stored bootstrap intervals do not justify broad
statistical or deployment claims. Raw measurements and failures are preserved:

- [2400 method/query records](results/raw.jsonl)
- [All comparison summaries](results/summary.json)
- [Primary hypothesis gate](results/hypothesis_gate.json)
- [Exact sampled row indices](results/splits.json)
- [Hardware, setup costs, hashes and memory](results/metadata.json)

## Finite guarantee

Maintain incumbent exact distance U. Only skip a candidate if an admissible lower
bound exceeds U. Every skipped candidate then has true distance greater than U, so
it cannot change the exhaustive result. A symbolic score can therefore order the
search arbitrarily without compromising exactness; it cannot itself justify
pruning. Strict comparisons, numerical slack and stable index tie breaks are
explicit. The lower bounds are established methods, credited to Keogh and
[Lemire 2009](https://arxiv.org/abs/0811.3301), not invented here.

The certificate is conditional on this fixed finite catalogue, normalization,
distance and warping band. It does not certify human-interpretable meaning.
Stronger modern bounds such as LB_Webb are not reproduced, so this is not a
state-of-the-art speed comparison.

## Reproduce

Requires Python 3, NumPy 2 and a C compiler. Runs sequentially on CPU.

```sh
python -m pip install -r requirements.txt
python study.py download
python -m unittest -v test_study.py
python verify.py
python study.py run
```

`verify.py` independently reconstructs all 480 query variants and exhaustively
recomputes every oracle, checks all 2,400 records, data/source hashes, query splits,
cell counts, summary aggregates and the hypothesis gate. It passed. Unit tests
also exhaust small ternary-series bounds and compare the C backend against an
independent full-matrix DP. Independent adversarial review added 864 bound checks
and 144 searches, including different scales and near ties; see its audit.

The committed protocol and results are the original final run. A later `run`
writes a timestamped subfolder rather than overwriting them. `develop` refuses
to retune after final results exist. Timing values naturally vary; exact answers
and operation counts are the reproducible outcomes. The archive is downloaded
separately and checked against SHA256; it is not committed.

## What would need to improve

A future study should first remove bound-construction overhead and compare
against an optimized modern exact-DTW library, then use independent writers and
actual movement-domain data with meaningful task labels. Stronger semantics or
compositional learning requires its own task and evaluation, rather than treating
nuisance robustness or exact metric retrieval as proof of reasoning ability.
