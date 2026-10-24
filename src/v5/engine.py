"""Chạy thật HCO rồi VNLS theo quy trình Bước 7, không áp giới hạn FE Bước 8."""
import time
import numpy as np
from .economics import ROOT, load_context
from .hco import run_hco
from .vnls import run_vnls
from .errors import InvalidBudgetError, NoFeasibleSolutionError, OptimizationExecutionError


def _run_algorithms(context, seed):
    """Chỉ phân loại lỗi ở biên điều phối; không sửa mã khoa học HCO/VNLS."""
    stage = 'HCO'
    try:
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            try:
                hco = run_hco(context.evaluate_candidate, seed=int(seed))
            except RuntimeError as exc:
                if str(exc) == 'HCO chưa gặp nghiệm khả thi; không tự sửa hoặc thêm nghiệm mồi.':
                    raise NoFeasibleSolutionError(
                        'HCO chưa tìm thấy nghiệm khả thi trong lần chạy này. '
                        'Điều này không có nghĩa bài toán không có nghiệm khả thi; '
                        'bộ máy không tự thêm nghiệm toàn 0 hoặc sửa nghiệm.',
                        budget=context.budget, seed=int(seed), stage=stage,
                        reason='ORIGINAL_HCO_NO_FEASIBLE_ARCHIVE') from exc
                raise
            stage = 'VNLS'
            vnls = run_vnls(hco['X'], context.evaluate_candidate)
        for result in (hco['result'], vnls['initial'], vnls['final']):
            if 'breakdown' not in result:
                result['breakdown'] = context.breakdown(result['solution'])
        return hco, vnls
    except NoFeasibleSolutionError:
        raise
    except Exception as exc:
        raise OptimizationExecutionError(
            f'Lỗi thực thi tại {stage}; không có phương án mới được chấp nhận.',
            budget=context.budget, seed=int(seed), stage=stage,
            reason='NUMERICAL_ERROR' if isinstance(exc, FloatingPointError) else type(exc).__name__) from exc


def run_hco_vnls(budget=768.0, seed=42, *, store=44, planning_horizon=7, root=ROOT):
    if isinstance(store, (bool, np.bool_)) or store != 44:
        raise ValueError('Bộ máy hiện chỉ hỗ trợ Store 44.')
    if isinstance(planning_horizon, (bool, np.bool_)) or planning_horizon != 7:
        raise ValueError('Bộ máy hiện chỉ hỗ trợ thời hạn 7 ngày.')
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError('Seed phải là số nguyên không âm, không nhận bool.')
    start = time.perf_counter()
    try:
        context = load_context(root, budget)
    except InvalidBudgetError:
        raise
    except Exception as exc:
        raise OptimizationExecutionError('Không nạp được nguồn kinh tế V5 đã chốt.',
                                         budget=budget, seed=int(seed), stage='LOAD_DATA',
                                         reason=type(exc).__name__) from exc
    hco, vnls = _run_algorithms(context, seed)
    final = vnls['final']
    if not final['is_feasible'] or final['total_cost'] > context.budget:
        raise OptimizationExecutionError('Không chấp nhận nghiệm vi phạm làm phương án cuối.',
                                         budget=context.budget, seed=int(seed), stage='AUDIT')
    checked = context.evaluate_solution(vnls['X'])
    for key in ['profit', 'total_cost', 'fitness', 'total_uplift', 'expected_sales']:
        if checked[key] != final[key]:
            raise OptimizationExecutionError(f'Đánh giá đối chiếu không khớp: {key}',
                                             budget=context.budget, seed=int(seed), stage='AUDIT')
    delta = final['profit'] - hco['result']['profit']
    if delta < 0:
        raise OptimizationExecutionError('VNLS không được làm giảm lợi nhuận của nghiệm khả thi.',
                                         budget=context.budget, seed=int(seed), stage='AUDIT')
    allocation = final['breakdown'][['family', 'promotion_level', 'promotion_cost_usd',
                                    'D_hat_selected_7d', 'incremental_profit']].copy()
    return {'status': 'success', 'seed': int(seed), 'store': store, 'planning_horizon': planning_horizon,
            'economic_unit': 'USD tham chiếu/mô phỏng, không phải lợi nhuận kế toán thực Store 44',
            'budget': context.budget, 'hco': hco, 'vnls': vnls, 'allocation': allocation,
            'summary': {'budget': context.budget, 'profit': final['profit'], 'total_cost': final['total_cost'],
                        'budget_utilization_percent': 100*final['total_cost']/context.budget,
                        'remaining_budget': context.budget-final['total_cost'],
                        'expected_sales': final['expected_sales'], 'total_uplift': final['total_uplift'],
                        'fitness': final['fitness'], 'is_feasible': final['is_feasible'],
                        'profit_improvement': delta,
                        'improvement_percent': None if hco['result']['profit'] == 0 else 100*delta/hco['result']['profit']},
            'comparison': {'hco_profit': hco['result']['profit'], 'final_profit': final['profit'],
                           'hco_total_cost': hco['result']['total_cost'], 'final_total_cost': final['total_cost'],
                           'profit_improvement': delta,
                           'improvement_percent': None if hco['result']['profit'] == 0 else 100*delta/hco['result']['profit']},
            'execution': {'runtime_seconds': time.perf_counter()-start,
                          'P_scale': context.p_scale, 'penalty_lambda': context.penalty_lambda,
                          'vnls_passes': len(vnls['passes']), 'accepted_improvements': len(vnls['accepted']),
                          'hco_logical_evaluations': hco['evaluations'],
                          'hco_evaluator_calls': hco['evaluator_calls'],
                          'vnls_candidate_requests': vnls['candidate_requests'],
                          'vnls_evaluator_calls': vnls['total_evaluator_calls'],
                          'audit_evaluator_calls': 1}}
