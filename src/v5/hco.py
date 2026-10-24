"""Mã khoa học trích từ 06_human_conception_optimization_STEP6_V5.ipynb; chỉ đổi cách truyền evaluator."""
import time
from itertools import combinations, product
import numpy as np
import pandas as pd
from .config import DIMENSION, LEVELS, LOWER, UPPER, EPSILON, PARAMS, RANDOM_SEED

def to_levels(bounded_position):
    bounded_position = np.asarray(bounded_position,dtype=float)
    assert np.isfinite(bounded_position).all()
    assert ((bounded_position>=LOWER)&(bounded_position<=UPPER)).all()
    return np.floor(bounded_position+0.5).astype(int)

def run_hco(evaluate_solution, seed=RANDOM_SEED):
    params = dict(PARAMS)
    rng = np.random.default_rng(seed)
    start = time.perf_counter()
    gamma, eta = float(rng.random()), float(rng.random())
    cache = {}
    evaluations = evaluator_calls = infeasible_evaluations = 0
    best_feasible = None
    best_feasible_x = None
    denominator_guards = 0
    finite_scores = bounds_valid = levels_valid = direction_valid = True

    def score(vector):
        nonlocal evaluations, evaluator_calls, infeasible_evaluations
        nonlocal best_feasible, best_feasible_x, finite_scores, levels_valid
        key = tuple(int(p) for p in vector)
        evaluations += 1
        levels_valid = levels_valid and len(key)==DIMENSION and set(key)<=set(LEVELS)
        assert levels_valid
        if key not in cache:
            cache[key] = evaluate_solution(key)
            evaluator_calls += 1
        result = cache[key]
        finite_scores = finite_scores and bool(all(np.isfinite(result[k]) for k in
            ['fitness','profit','total_cost','budget','budget_violation','penalty','total_uplift']))
        assert finite_scores
        infeasible_evaluations += int(not result['is_feasible'])
        return result

    def keep_feasible(vector, result):
        nonlocal best_feasible, best_feasible_x
        if result['is_feasible'] and (best_feasible is None or result['fitness']>best_feasible['fitness']):
            best_feasible = result
            best_feasible_x = tuple(int(p) for p in vector)

    # Chuẩn bị: Eq.(2), Eq.(4), chọn hướng rồi Eq.(7)–(8).
    original = rng.uniform(LOWER,UPPER,size=(params['nPop'],DIMENSION))
    opposite = LOWER+UPPER-original
    original_x, opposite_x = to_levels(original), to_levels(opposite)
    original_results = [score(x) for x in original_x]
    opposite_results = [score(x) for x in opposite_x]
    for x,result in zip(np.concatenate([original_x,opposite_x]),original_results+opposite_results):
        keep_feasible(x,result)
    original_f = -np.array([r['fitness'] for r in original_results])
    opposite_f = -np.array([r['fitness'] for r in opposite_results])
    use_original = original_f<opposite_f
    chosen_s = np.where(use_original[:,None],original,opposite)
    chosen_f = np.where(use_original,original_f,opposite_f)
    pfit = (chosen_f.max()-chosen_f.min())*params['w']+chosen_f.min()
    healthy_mask = chosen_f<=pfit
    S, objective = chosen_s[healthy_mask].copy(), chosen_f[healthy_mask].copy()
    T = len(S)
    assert T>0
    velocity = np.zeros_like(S)
    pbest, pbest_objective = S.copy(), objective.copy()
    winner = int(np.argmin(objective))
    gbest, gbest_objective = S[winner].copy(), float(objective[winner])
    initial_search_fitness = -gbest_objective
    initial_feasible_fitness = None if best_feasible is None else best_feasible['fitness']
    history = []

    for iteration in range(1,params['MaxIt']+1):
        # BƯỚC 1 — SINH NGHIỆM MỚI: Eq.(12)–(14), không có tìm kiếm cục bộ.
        best_current, average = float(objective.min()), float(objective.mean())
        denominator = 4*eta*(best_current-average)
        if abs(denominator)<EPSILON:
            profile = np.zeros(T)
            denominator_guards += 1
        else:
            R, r = best_current-objective, average-objective
            profile = gamma*(R**2-r**2)/denominator
        A1, A2 = pbest-S, gbest-S
        sine = np.sin(2*np.pi*iteration/params['MaxIt'])
        new_velocity = (params['w1']*(velocity+profile[:,None])
            +params['c1']*A1*sine+params['c2']*A2*sine)
        S_new = S+new_velocity
        assert np.isfinite(S_new).all() and np.isfinite(new_velocity).all()

        # BƯỚC 2 — KIỂM TRA GIỚI HẠN BIẾN.
        S_new = np.clip(S_new,LOWER,UPPER)
        bounds_valid = bounds_valid and bool(((S_new>=LOWER)&(S_new<=UPPER)).all())
        assert bounds_valid

        # BƯỚC 3 — CHUYỂN VỀ MỨC KHUYẾN MÃI HỢP LỆ.
        X_new = to_levels(S_new)

        # BƯỚC 4 — KIỂM TRA RÀNG BUỘC NGÂN SÁCH: chỉ dùng kết quả V5.
        candidate_results = [score(x) for x in X_new]
        constraint_records = [(r['total_cost'],r['budget'],r['is_feasible'],r['budget_violation'])
                              for r in candidate_results]
        assert len(constraint_records)==T

        # BƯỚC 5 — TÍNH FITNESS: đọc điểm kinh tế, đổi dấu nội bộ.
        candidate_fitness = np.array([r['fitness'] for r in candidate_results])
        new_objective = -candidate_fitness
        assert np.isfinite(candidate_fitness).all()

        # BƯỚC 6 — CẬP NHẬT CÁ THỂ, PBEST, GBEST VÀ NGHIỆM KHẢ THI TỐT NHẤT.
        previous_gbest = gbest_objective
        previous_pbest = pbest_objective.copy()
        previous_objective = objective.copy()
        improved = new_objective<objective
        S[improved], objective[improved] = S_new[improved], new_objective[improved]
        velocity = new_velocity
        personal_improved = objective<pbest_objective
        pbest[personal_improved] = S[personal_improved]
        pbest_objective[personal_improved] = objective[personal_improved]
        winner = int(np.argmin(pbest_objective))
        if pbest_objective[winner]<gbest_objective:
            gbest, gbest_objective = pbest[winner].copy(), float(pbest_objective[winner])
        for x,result in zip(X_new,candidate_results):
            keep_feasible(x,result)
        direction_valid = direction_valid and bool((objective<=previous_objective).all()
            and (pbest_objective<=previous_pbest).all() and gbest_objective<=previous_gbest)
        assert direction_valid and np.array_equal(pbest,S)
        history.append({'iteration':iteration,
            'best_search_fitness':-gbest_objective,
            'best_feasible_fitness':None if best_feasible is None else best_feasible['fitness'],
            'evaluations':evaluations,'evaluator_calls':evaluator_calls,
            'infeasible_evaluations':infeasible_evaluations})

    if best_feasible is None:
        raise RuntimeError('HCO chưa gặp nghiệm khả thi; không tự sửa hoặc thêm nghiệm mồi.')
    assert evaluations==2*params['nPop']+params['MaxIt']*T
    assert best_feasible['is_feasible'] and best_feasible['total_cost']<=best_feasible['budget']+1e-12
    assert abs(best_feasible['budget_violation'])<=1e-12
    return {'X':best_feasible_x,'result':best_feasible,
        'history':pd.DataFrame(history),'seed':int(seed),'healthy_size':T,
        'evaluations':evaluations,'evaluator_calls':evaluator_calls,
        'infeasible_evaluations':infeasible_evaluations,'gamma':gamma,'eta':eta,
        'denominator_guards':denominator_guards,'elapsed_seconds':time.perf_counter()-start,
        'best_search_fitness':-gbest_objective,'initial_search_fitness':initial_search_fitness,
        'initial_feasible_fitness':initial_feasible_fitness,
        'initialization':{'shape':original.shape, 'opposite_bounds_valid':bool(((opposite>=LOWER)&(opposite<=UPPER)).all()),
            'healthy_size':T,'pfit':float(pfit),'cache_entries':len(cache)},
        'checks':{'finite_scores':finite_scores,'bounds_valid':bounds_valid,
                  'levels_valid':levels_valid,'direction_valid':direction_valid}}
