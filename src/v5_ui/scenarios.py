"""Điều phối yêu cầu độc lập; khóa CPU chung, không giữ cache kết quả toàn cục."""
import logging
import threading
from contextlib import contextmanager
import pandas as pd
from src import v5
from .presentation import validate_result

DEFAULT_BUDGETS = (650.0, 768.0, 900.0, 2091.0)
SCENARIO_KEY = 'v5_scenario_results'
SCENARIO_CONFIG = 'v5_scenario_config'
SCENARIO_CHANGED = 'v5_scenario_changed'
_RUN_LOCK = threading.Lock()


class EngineBusyError(RuntimeError):
    """Một yêu cầu khác đang chạy trong cùng tiến trình máy chủ."""


@contextmanager
def optimization_slot():
    if not _RUN_LOCK.acquire(blocking=False):
        raise EngineBusyError('Máy chủ đang xử lý một yêu cầu tối ưu khác. Vui lòng thử lại sau.')
    try:
        yield
    finally:
        _RUN_LOCK.release()


def clear_scenarios(state, *, changed=True):
    state.pop(SCENARIO_KEY,None)
    state.pop(SCENARIO_CONFIG,None)
    state[SCENARIO_CHANGED] = changed


def _fresh(budget, runner=None):
    context = v5.load_context(budget=budget)
    result = (runner or v5.run_hco_vnls)(budget=budget, seed=42, store=44, planning_horizon=7)
    validate_result(result,dict(budget=budget,seed=42,store=44,planning_horizon=7),context.families)
    return result


def run_main(budget):
    with optimization_slot():
        return _fresh(budget)


def run_four_budgets(budgets, progress=None, runner=None):
    if len(budgets)!=4:
        raise ValueError('Cần đúng bốn ngân sách kịch bản.')
    records=[]
    with optimization_slot():
        for i,budget in enumerate(budgets):
            if progress:
                progress(i,4,budget)
            try:
                result = _fresh(budget,runner)
                records.append({'scenario':i+1,'budget':budget,'result':result,'error':None,'code':None})
            except Exception as exc:
                code = getattr(exc,'code','OUT_OF_MEMORY' if isinstance(exc,MemoryError) else 'SCENARIO_EXECUTION_ERROR')
                message = str(exc) if isinstance(exc,(v5.InvalidBudgetError,v5.NoFeasibleSolutionError)) else 'Không hoàn tất kịch bản; kiểm tra nhật ký máy chủ hoặc thử lại.'
                logging.exception('Lỗi kịch bản ngân sách %s',i+1)
                records.append({'scenario':i+1,'budget':budget,'result':None,'error':message,'code':code})
        if progress:
            progress(4,4,None)
    return records


def scenario_frame(records):
    rows=[]
    for record in records:
        row={'Kịch bản':f'Kịch bản {record["scenario"]}', 'Ngân sách':record['budget'],
             'Trạng thái':'Thành công' if record['result'] is not None else 'Thất bại',
             'Lỗi':record['error'] or '', 'Mã lỗi':record['code'] or ''}
        r=record['result']
        mapping={'Đã sử dụng':'total_cost','Còn lại':'remaining_budget','Sử dụng (%)':'budget_utilization_percent',
                 'Lượng bán dự báo':'expected_sales','Uplift dự báo':'total_uplift','Lợi nhuận HCO-VNLS':'profit',
                 'Cải thiện tuyệt đối':'profit_improvement','Cải thiện (%)':'improvement_percent','Khả thi':'is_feasible'}
        row.update({label:r['summary'][key] if r else None for label,key in mapping.items()})
        row['Lợi nhuận HCO']=r['comparison']['hco_profit'] if r else None
        row['Thời gian (giây)']=r['execution']['runtime_seconds'] if r else None
        rows.append(row)
    return pd.DataFrame(rows)
