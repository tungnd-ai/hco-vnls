"""Mã khoa học trích từ 07_HCO_VNLS_STEP7_V5.ipynb; chỉ đổi cách truyền evaluator."""
import time
from itertools import combinations, product
import numpy as np
import pandas as pd
from .config import DIMENSION, LEVELS, LOWER, UPPER, EPSILON, PARAMS, RANDOM_SEED

PASS_COLUMNS=['pass','neighborhood','X_before','fitness_before','generated_candidates','feasible_candidates',
 'infeasible_candidates','new_evaluator_calls','cache_hits','best_neighbor_fitness','accepted','X_after','fitness_after','next_k']

MOVE_COLUMNS=['move','pass','neighborhood','X_before','X_after','profit_before','profit_after',
 'fitness_before','fitness_after','cost_before','cost_after','uplift_before','uplift_after','feasible_after']

def validate_vector(X):
    if not isinstance(X,(list,tuple,np.ndarray)) or len(X)!=DIMENSION:
        raise ValueError('Véc-tơ phải có đúng 15 tọa độ.')
    if any(isinstance(p,(bool,np.bool_)) or not isinstance(p,(int,np.integer)) or p not in LEVELS for p in X):
        raise ValueError('Mỗi tọa độ phải là số nguyên 0–3, không nhận bool hoặc số thực.')
    return tuple(int(p) for p in X)

def generate_n1_neighbors(X):
    X=validate_vector(X)
    neighbors=set()
    for i in range(DIMENSION):
        for step in (-1,1):
            if X[i]+step in LEVELS:
                candidate=list(X);candidate[i]+=step
                neighbors.add(tuple(candidate))
    return sorted(neighbors)

def generate_n2_neighbors(X):
    X=validate_vector(X)
    neighbors=set()
    for i in range(DIMENSION):
        for j in range(DIMENSION):
            if i!=j and X[i]>0 and X[j]<3:
                candidate=list(X);candidate[i]-=1;candidate[j]+=1
                neighbors.add(tuple(candidate))
    return sorted(neighbors)

def generate_n3_neighbors(X):
    X=validate_vector(X)
    neighbors=set()
    for indices in combinations(range(DIMENSION),4):
        for steps in product((-1,1),repeat=4):
            candidate=list(X)
            for i,step in zip(indices,steps):
                candidate[i]+=step
            if all(candidate[i] in LEVELS for i in indices):
                neighbors.add(tuple(candidate))
    return sorted(neighbors)

def get_neighbors(X,k):
    generators={1:generate_n1_neighbors,2:generate_n2_neighbors,3:generate_n3_neighbors}
    if k not in generators:
        raise ValueError('Chỉ có N1, N2, N3.')
    return generators[k](X)

def evaluate_with_cache(X,evaluator,cache,counts):
    key=validate_vector(X)
    counts['candidate_requests']+=1
    if key in cache:
        counts['cache_hits']+=1
    else:
        cache[key]=evaluator(key)
        counts['unique_candidate_calls']+=1
    return cache[key]

def choose_best_feasible(scored):
    feasible=[(X,r) for X,r in scored if r['is_feasible']]
    return min(feasible,key=lambda item:(-item[1]['fitness'],item[0])) if feasible else None

def is_strict_improvement(best,current):
    return bool(best is not None and best[1]['fitness']>current['fitness']+EPSILON)

def run_vnls(X_start, evaluator, neighbors_fn=get_neighbors, verbose=False):
    start=time.perf_counter()
    current_X=validate_vector(X_start)
    current_result=evaluator(current_X)
    if not current_result['is_feasible']:
        raise ValueError('VNLS cần nghiệm xuất phát khả thi; không tự sửa ngân sách.')
    initial=current_result
    cache={current_X:current_result}
    counts={'candidate_requests':0,'unique_candidate_calls':0,'cache_hits':0,
        'feasible_candidates':0,'infeasible_candidates':0}
    passes,moves=[],[]
    k=1
    while k<=3:
        neighbors=neighbors_fn(current_X,k)
        before_calls,before_hits=counts['unique_candidate_calls'],counts['cache_hits']
        scored=[(X,evaluate_with_cache(X,evaluator,cache,counts)) for X in neighbors]
        assert all(np.isfinite(r['fitness']) for _,r in scored)
        best=choose_best_feasible(scored)
        accepted=is_strict_improvement(best,current_result)
        feasible_count=sum(bool(r['is_feasible']) for _,r in scored)
        counts['feasible_candidates']+=feasible_count
        counts['infeasible_candidates']+=len(neighbors)-feasible_count
        next_X,next_result=best if accepted else (current_X,current_result)
        next_k=1 if accepted else k+1
        passes.append({'pass':len(passes)+1,'neighborhood':f'N{k}','X_before':current_X,
            'fitness_before':current_result['fitness'],'generated_candidates':len(neighbors),
            'feasible_candidates':feasible_count,'infeasible_candidates':len(neighbors)-feasible_count,
            'new_evaluator_calls':counts['unique_candidate_calls']-before_calls,
            'cache_hits':counts['cache_hits']-before_hits,
            'best_neighbor_fitness':None if best is None else best[1]['fitness'],
            'accepted':accepted,'X_after':next_X,'fitness_after':next_result['fitness'],'next_k':next_k})
        if accepted:
            assert next_result['is_feasible']
            moves.append({'move':len(moves)+1,'pass':len(passes),'neighborhood':f'N{k}',
                'X_before':current_X,'X_after':next_X,
                **{name+'_before':current_result[field] for name,field in
                    [('profit','profit'),('fitness','fitness'),('cost','total_cost'),('uplift','total_uplift')]},
                **{name+'_after':next_result[field] for name,field in
                    [('profit','profit'),('fitness','fitness'),('cost','total_cost'),('uplift','total_uplift')]},
                'feasible_after':next_result['is_feasible']})
        if verbose:
            print(f'Lượt {len(passes)} — N{k}: {len(neighbors)} ứng viên; {feasible_count} khả thi; nhận={accepted}; Fitness={next_result["fitness"]:.12f}',flush=True)
        current_X,current_result=next_X,next_result
        k=next_k
    assert counts['candidate_requests']==counts['unique_candidate_calls']+counts['cache_hits']
    assert len(cache)==1+counts['unique_candidate_calls']
    assert counts['candidate_requests']==counts['feasible_candidates']+counts['infeasible_candidates']
    return {'X_start':validate_vector(X_start),'X':current_X,'initial':initial,'final':current_result,
        'passes':pd.DataFrame(passes,columns=PASS_COLUMNS),'accepted':pd.DataFrame(moves,columns=MOVE_COLUMNS),
        **counts,'initial_evaluator_calls':1,'total_evaluator_calls':len(cache),
        'elapsed_seconds':time.perf_counter()-start}
