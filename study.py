"""A bounded, exact trajectory-retrieval audit; not a new DTW lower bound."""
from __future__ import annotations
import argparse, ctypes, hashlib, json, math, os, pathlib, platform
import resource, subprocess, time, urllib.request, zipfile
from datetime import datetime, timezone
import numpy as np

HERE=pathlib.Path(__file__).resolve().parent
URL='https://www.timeseriesclassification.com/aeon-toolkit/CharacterTrajectories.zip'
SHA='336f345d6a5280d7e3642978bb8ed85b7e4c6813024d29be157d757cf3c54358'
N=48; RADIUS=6
SEEDS=[2026112301,2026112302,2026112303]
CONDITIONS=['clean','timewarp','noise','composed']

def backend():
    cache=HERE/'.cache';cache.mkdir(exist_ok=True)
    binary=cache/'dtw.so'
    if not binary.exists() or binary.stat().st_mtime<(HERE/'dtw.c').stat().st_mtime:
        subprocess.run(['cc','-O3','-shared','-fPIC',str(HERE/'dtw.c'),'-lm','-o',str(binary)],check=True)
    lib=ctypes.CDLL(str(binary)); f=lib.dtw
    p=ctypes.POINTER(ctypes.c_double)
    f.argtypes=[p,p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_double,ctypes.POINTER(ctypes.c_uint64)]
    f.restype=ctypes.c_double
    def distance(x,y,cutoff=math.inf,radius=RADIUS):
        x=np.ascontiguousarray(x,dtype=np.float64);y=np.ascontiguousarray(y,dtype=np.float64)
        cells=ctypes.c_uint64()
        out=f(x.ctypes.data_as(p),y.ctypes.data_as(p),len(x),x.shape[1],radius,cutoff,ctypes.byref(cells))
        return out,cells.value
    return distance

def download():
    folder=HERE/'data';folder.mkdir(exist_ok=True)
    dest=folder/'CharacterTrajectories.zip'
    if not dest.exists():
        with urllib.request.urlopen(URL,timeout=45) as r: dest.write_bytes(r.read())
    actual=hashlib.sha256(dest.read_bytes()).hexdigest()
    if actual!=SHA: raise ValueError(f'Dataset archive changed: {actual}; review before using')
    return dest

def load_split(split):
    out=[];labels=[]
    with zipfile.ZipFile(download()) as z:
        text=z.read(f'CharacterTrajectories_{split}.ts').decode()
    data=False
    for line in text.splitlines():
        if line.lower().startswith('@data'):data=True;continue
        if not data or not line or line.startswith('#'):continue
        fields=line.split(':'); channels=[np.fromstring(s,sep=',') for s in fields[:-1]]
        if len(channels)!=3 or len({len(v) for v in channels})!=1:raise ValueError('Unexpected channels')
        t=np.linspace(0,1,len(channels[0]));grid=np.linspace(0,1,N)
        out.append(np.stack([np.interp(grid,t,v) for v in channels],axis=1))
        labels.append(int(fields[-1]))
    return np.array(out),np.array(labels)

def envelope(x,r=RADIUS):
    # x shape(..., time, channels)
    lo=np.empty_like(x);hi=np.empty_like(x)
    for i in range(x.shape[-2]):
        sl=x[...,max(0,i-r):min(x.shape[-2],i+r+1),:]
        lo[...,i,:]=sl.min(axis=-2);hi[...,i,:]=sl.max(axis=-2)
    return lo,hi

def directional(query,candidates,cenv):
    lo,hi=cenv
    projected=np.clip(query,lo,hi)
    first=((query-projected)**2).sum(axis=(-2,-1))
    # Lemire's LB_Improved: a second projection pass, NOT sum of two
    # arbitrary directional Keogh bounds. Each coordinate is separable.
    plo,phi=envelope(projected)
    second=((candidates-np.clip(candidates,plo,phi))**2).sum(axis=(-2,-1))
    return first+second,first

def bounds(query,candidates,cenv):
    forward,k1=directional(query,candidates,cenv)
    qlo,qhi=envelope(query)
    reverse,k2=directional(candidates,np.broadcast_to(query,candidates.shape),(qlo,qhi))
    endpoints=((candidates[:,0]-query[0])**2).sum(axis=-1)+((candidates[:,-1]-query[-1])**2).sum(axis=-1)
    return np.maximum(np.maximum(forward,reverse),endpoints),np.maximum(k1,k2)

def summaries(x):
    # Deterministic motion vocabulary: 8 velocity-direction symbols and
    # their adjacent transitions. No character labels or test-set fitting.
    b=x.reshape(*x.shape[:-2],6,N//6,3).mean(axis=-2).reshape(*x.shape[:-2],18)
    angle=np.arctan2(x[...,1],x[...,0]); symbols=(np.floor((angle+np.pi)*8/(2*np.pi)).astype(int)%8)
    h=np.stack([(symbols==i).mean(axis=-1) for i in range(8)],axis=-1)
    tr=symbols[...,:-1]*8+symbols[...,1:]
    transitions=np.stack([(tr==i).mean(axis=-1) for i in range(64)],axis=-1)
    return b,np.concatenate([h,transitions],axis=-1)

def search(query,candidates,cenv,features,distance,method,weight=1.):
    begin=time.perf_counter_ns(); count=0;calls=0;pruned=0
    if method=='exhaustive':
        lb=np.zeros(len(candidates));order=np.arange(len(candidates));cut=False
    else:
        lb,keogh=bounds(query,candidates,cenv);cut=True
        if method=='improved_bound_order':scores=lb
        elif method=='keogh_bound_order':scores=keogh
        elif method=='euclidean_order':scores=((candidates-query)**2).sum(axis=(-2,-1))
        elif method=='symbolic_order':
            a,b=summaries(query);aa,bb=features
            scores=((aa-a)**2).sum(axis=-1)+weight*((bb-b)**2).sum(axis=-1)
        else:raise ValueError(method)
        order=np.lexsort((np.arange(len(candidates)),scores))
    best=math.inf; winner=-1
    for ix in order:
        # Strict comparison preserves equal-distance ties. Slack prevents
        # finite-precision bound noise from excluding a near tie.
        if cut and lb[ix]>best+1e-10*max(1.,best):pruned+=1;continue
        value,ncells=distance(query,candidates[ix],best if cut else math.inf)
        count+=ncells;calls+=1
        if value<best or (value==best and (winner<0 or ix<winner)):
            best=value;winner=int(ix)
    elapsed=(time.perf_counter_ns()-begin)/1e6
    return {'winner':winner,'distance':best,'cells':count,'dtw_calls':calls,'bound_pruned':pruned,'ms':elapsed}

def transform(x,condition,rng):
    out=x.copy()
    if condition in ('timewarp','composed'):
        # Strength0.65 is fixed before final testing; development is clean only.
        increments=np.exp(rng.normal(0,.65,N-1)); knots=np.r_[0,np.cumsum(increments)]
        knots/=knots[-1]; grid=np.linspace(0,1,N)
        out=np.stack([np.interp(grid,knots,out[:,d]) for d in range(3)],axis=-1)
    if condition in ('noise','composed'):out+=rng.normal(0,.12,out.shape)
    return out

def prepare(seed,train,trainlabels,test,testlabels):
    rng=np.random.default_rng(seed)
    # A common catalogue across all methods. Class labels ONLY balance its
    # selection, and separate development/final queries; never rank neighbors.
    ids=np.concatenate([rng.choice(np.flatnonzero(trainlabels==c),10,replace=False) for c in sorted(set(trainlabels))])
    catalogue=train[ids]
    dev_ids=np.concatenate([rng.choice(np.flatnonzero(testlabels==c),2,replace=False) for c in range(1,11)])
    final_ids=np.concatenate([rng.choice(np.flatnonzero(testlabels==c),4,replace=False) for c in range(11,21)])
    return catalogue,ids,dev_ids,final_ids

def develop(train,tl,test,yl,distance):
    catalogue,_,dev,_=prepare(SEEDS[0],train,tl,test,yl);env=envelope(catalogue);features=summaries(catalogue)
    trials=[]
    for weight in (0.,1.,10.,100.):
        cells=0
        for ix in dev:
            cells+=search(test[ix],catalogue,env,features,distance,'symbolic_order',weight)['cells']
        trials.append({'weight':weight,'cells':cells})
    winner=min(trials,key=lambda r:(r['cells'],r['weight']))['weight']
    return {'weight':winner,'development_trials':trials,'development_query_classes':list(range(1,11)),
            'locked_final_query_classes':list(range(11,21))}

METHODS=['exhaustive','keogh_bound_order','improved_bound_order','euclidean_order','symbolic_order']

def run():
    t0=time.perf_counter();distance=backend();backend_seconds=time.perf_counter()-t0
    parse_start=time.perf_counter()
    train,tl=load_split('TRAIN');test,yl=load_split('TEST')
    parse_seconds=time.perf_counter()-parse_start;normalization_start=time.perf_counter()
    # Per-channel scale learned only from official TRAIN, not per-trajectory
    # normalization that might erase real amplitude/force differences.
    mean=train.mean(axis=(0,1));scale=train.std(axis=(0,1));train=(train-mean)/scale;test=(test-mean)/scale
    normalization_seconds=time.perf_counter()-normalization_start
    frozen=HERE/'protocol_lock.json'
    if not frozen.exists():raise RuntimeError('Run `python study.py develop` and review protocol before final tests')
    lock=json.loads(frozen.read_text());weight=lock['weight']
    records=[];splits=[];catalogue_preprocess=[]
    for seed in SEEDS:
        catalogue,ids,dev,final=prepare(seed,train,tl,test,yl)
        begin=time.perf_counter();env=envelope(catalogue);envelope_seconds=time.perf_counter()-begin
        begin=time.perf_counter();features=summaries(catalogue);feature_seconds=time.perf_counter()-begin
        catalogue_preprocess.append({'seed':seed,'envelope_seconds':envelope_seconds,
          'symbolic_feature_seconds':feature_seconds,'total_seconds':envelope_seconds+feature_seconds})
        splits.append({'seed':seed,'catalogue_train_ids':ids.tolist(),'dev_test_ids':dev.tolist(),'final_test_ids':final.tolist()})
        rng=np.random.default_rng(seed+100)
        for condition in CONDITIONS:
            for qi in final:
                query=transform(test[qi],condition,rng)
                # Randomize method timing order; preserve the same query.
                outputs={}
                for method in rng.permutation(METHODS):
                    outputs[method]=search(query,catalogue,env,features,distance,method,weight)
                oracle=outputs['exhaustive']
                a,b=summaries(query);aa,bb=features
                score=((aa-a)**2).sum(axis=-1)+weight*((bb-b)**2).sum(axis=-1)
                approximate=int(np.argmin(score))
                for method in METHODS:
                    result=outputs[method]
                    records.append({'seed':seed,'condition':condition,'query_id':int(qi),'method':method,
                      **result,'oracle_winner':oracle['winner'],'oracle_distance':oracle['distance'],
                      'correct':result['winner']==oracle['winner'],
                      'approximate_symbolic_correct':approximate==oracle['winner']})
    results=HERE/'results'
    if (results/'raw.jsonl').exists():
        results=results/('rerun-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    results.mkdir(parents=True,exist_ok=True)
    with (results/'raw.jsonl').open('w') as f:
        for record in records:f.write(json.dumps(record)+'\n')
    (results/'splits.json').write_text(json.dumps(splits,indent=2)+'\n')
    meta={'dataset_sha256':SHA,'train_count':len(train),'test_count':len(test),'n':N,'radius':RADIUS,
          'seeds':SEEDS,'lock':lock,'normalization_mean':mean.tolist(),'normalization_std':scale.tolist(),
          'catalogue_preprocessing':catalogue_preprocess,'platform':platform.platform(),'python':platform.python_version(),
          'numpy':np.__version__,'elapsed_seconds':time.perf_counter()-t0,
          'setup_seconds':{'backend_load_or_compile':backend_seconds,'data_parse_and_resample':parse_seconds,
                           'train_fit_normalization':normalization_seconds},
          'source_hashes':{p:hashlib.sha256((HERE/p).read_bytes()).hexdigest() for p in
            ['study.py','dtw.c','PROTOCOL.md','protocol_lock.json']},
          'maxrss_native_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'maxrss_unit':'bytes' if platform.system()=='Darwin' else 'KiB'}
    (results/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    report(records,meta,results)

def report(records,meta,results):
    rows=[];rng=np.random.default_rng(20261123)
    for condition in CONDITIONS:
        rr=[r for r in records if r['condition']==condition]
        base={ (r['seed'],r['query_id']):r for r in rr if r['method']=='improved_bound_order'}
        oracle={ (r['seed'],r['query_id']):r for r in rr if r['method']=='exhaustive'}
        for method in METHODS:
            group=[r for r in rr if r['method']==method]
            ratios=np.array([r['cells']/base[r['seed'],r['query_id']]['cells'] for r in group])
            # Seed-level means avoid treating repeated query IDs across seeds
            # as independent observations. 3 seed clusters => descriptive CI.
            seed_ratios=np.array([np.mean([r['cells']/base[r['seed'],r['query_id']]['cells'] for r in group if r['seed']==s]) for s in SEEDS])
            boot=np.mean(rng.choice(seed_ratios,size=(4000,len(SEEDS)),replace=True),axis=1)
            seed_num=np.array([sum(r['cells'] for r in group if r['seed']==s) for s in SEEDS])
            seed_den=np.array([sum(base[r['seed'],r['query_id']]['cells'] for r in group if r['seed']==s) for s in SEEDS])
            draws=rng.integers(0,len(SEEDS),size=(4000,len(SEEDS)))
            aggregate_boot=seed_num[draws].sum(axis=1)/seed_den[draws].sum(axis=1)
            rows.append({'condition':condition,'method':method,'n_queries':len(group),
              'oracle_agreement':sum(r['correct'] for r in group)/len(group),
              'mean_cells':float(np.mean([r['cells'] for r in group])),
              'mean_calls':float(np.mean([r['dtw_calls'] for r in group])),
              'mean_cell_ratio_vs_improved':float(ratios.mean()),
              'descriptive_seed_bootstrap_95':np.quantile(boot,[.025,.975]).tolist(),
              'aggregate_cell_ratio_vs_improved':float(seed_num.sum()/seed_den.sum()),
              'descriptive_seed_bootstrap_95_aggregate_ratio':np.quantile(aggregate_boot,[.025,.975]).tolist(),
              'median_ms':float(np.median([r['ms'] for r in group])),
              'mean_cell_ratio_vs_exhaustive':float(np.mean([r['cells']/oracle[r['seed'],r['query_id']]['cells'] for r in group])),
              'approximate_symbolic_recall':sum(r['approximate_symbolic_correct'] for r in group)/len(group)})
    gate={'exactness_pass':all(r['correct'] for r in records),
          'symbolic_efficiency_pass':all(r['aggregate_cell_ratio_vs_improved']<=.90 for r in rows if r['method']=='symbolic_order'),
          'definition':'primary efficiency is ratio of aggregate DP cells (equivalently ratio of mean cells), not mean per-query ratios'}
    (results/'hypothesis_gate.json').write_text(json.dumps(gate,indent=2)+'\n')
    (results/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps({'output_directory':str(results),'metadata':meta,'summary':rows},indent=2))

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['download','develop','run']);args=p.parse_args()
    if args.action=='download':print(download());return
    if args.action=='develop':
        if (HERE/'results'/'raw.jsonl').exists():
            raise RuntimeError('Final results already exist: preserve the locked protocol and use a new project/version for retuning')
        tr,tl=load_split('TRAIN');te,yl=load_split('TEST');mean=tr.mean(axis=(0,1));sd=tr.std(axis=(0,1))
        result=develop((tr-mean)/sd,tl,(te-mean)/sd,yl,backend())
        result.update({'dataset_sha256':SHA,'n':N,'radius':RADIUS,'seeds':SEEDS,'conditions':CONDITIONS,
          'primary_endpoint':'exact oracle agreement; ratio of aggregate DP cells (ratio of means) symbolic ordering vs improved-bound ordering',
          'success_threshold':'100% exact agreement; >=10% cell reduction vs improved-bound ordering in every final condition',
          'scope':'real pen movement; not AIS, learned world models or new DTW lower bounds'})
        (HERE/'protocol_lock.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return
    run()
if __name__=='__main__':main()
