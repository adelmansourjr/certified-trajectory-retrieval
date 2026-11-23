"""Validate stored results and reconstruct all held-out query variants."""
import collections,hashlib,json,math
import numpy as np
import study as s

def main():
    root=s.HERE/'results'
    records=[json.loads(line) for line in (root/'raw.jsonl').read_text().splitlines()]
    meta=json.loads((root/'metadata.json').read_text())
    for name,digest in meta['source_hashes'].items():
        assert hashlib.sha256((s.HERE/name).read_bytes()).hexdigest()==digest,name
    assert len(records)==3*4*40*len(s.METHODS)
    grouped=collections.defaultdict(dict)
    for r in records:
        key=(r['seed'],r['condition'],r['query_id'])
        assert r['method'] not in grouped[key]
        grouped[key][r['method']]=r
        assert r['correct'] and 0<=r['winner']<200
        assert r['cells']>0 and 0<r['dtw_calls']<=200
        assert math.isfinite(r['distance']) and r['ms']>=0
    train,tl=s.load_split('TRAIN');test,yl=s.load_split('TEST')
    mean=train.mean(axis=(0,1));sd=train.std(axis=(0,1));train=(train-mean)/sd;test=(test-mean)/sd
    distance=s.backend();rechecked=0
    for seed in s.SEEDS:
        cat,ids,dev,final=s.prepare(seed,train,tl,test,yl)
        assert not set(dev)&set(final)
        assert set(yl[dev])<=set(range(1,11)) and set(yl[final])<=set(range(11,21))
        rng=np.random.default_rng(seed+100)
        for condition in s.CONDITIONS:
            for qi in final:
                q=s.transform(test[qi],condition,rng)
                rng.permutation(s.METHODS) # mirrors timing-order RNG consumption
                rr=grouped[seed,condition,int(qi)]
                assert set(rr)==set(s.METHODS)
                # Independent exhaustive recomputation: no envelopes or summaries.
                values=[distance(q,c)[0] for c in cat]
                winner=min(range(len(values)),key=lambda i:(values[i],i))
                for method,r in rr.items():
                    assert r['winner']==winner
                    assert abs(r['distance']-values[winner])<1e-8
                    assert r['cells']<=rr['exhaustive']['cells']
                rechecked+=1
    summary=json.loads((root/'summary.json').read_text())
    for row in summary:
        selected=[r for r in records if r['condition']==row['condition'] and r['method']==row['method']]
        base=[r for r in records if r['condition']==row['condition'] and r['method']=='improved_bound_order']
        aggregate=sum(r['cells'] for r in selected)/sum(r['cells'] for r in base)
        assert abs(row['aggregate_cell_ratio_vs_improved']-aggregate)<1e-12
        assert row['n_queries']==len(selected)
        assert abs(row['mean_cells']-sum(r['cells'] for r in selected)/len(selected))<1e-10
    gate=json.loads((root/'hypothesis_gate.json').read_text())
    assert gate['exactness_pass']==all(r['correct'] for r in records)
    assert gate['symbolic_efficiency_pass']==all(r['aggregate_cell_ratio_vs_improved']<=.9 for r in summary if r['method']=='symbolic_order')
    print(f'PASS: {len(records)} rows; {rechecked} independently reconstructed exhaustive oracles; source/data hashes; splits; ties; cell counts.')

if __name__=='__main__':main()
