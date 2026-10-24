"""Ánh xạ kết quả thật sang giao diện; không triển khai lại công thức kinh tế."""
import math
import numpy as np
import pandas as pd

RESULT_KEY = 'v5_completed_result'
CONFIG_KEY = 'v5_completed_config'
ERROR_KEY = 'v5_request_error'
CHANGED_KEY = 'v5_input_changed'
COLUMN_NAMES = {
    'family': 'Product Family', 'promotion_level': 'Promotion Level',
    'promotion_cost_usd': 'Allocated Budget', 'D_hat_selected_7d': 'Expected Sales',
    'incremental_profit': 'Incremental Profit',
}


def clear_output(state, *, changed=False):
    for key in [RESULT_KEY, CONFIG_KEY, ERROR_KEY]:
        state.pop(key, None)
    state[CHANGED_KEY] = changed


def money(value):
    return number(value, 2) + ' USD'


def quantity(value):
    return number(value, 3)


def number(value, decimals=2):
    """Chỉ định dạng hiển thị kiểu Việt Nam, không đổi số dùng tính toán."""
    return f'{value:,.{decimals}f}'.translate(str.maketrans({',':'.', '.':','}))


def validate_result(result, config, families):
    """Chỉ kiểm tra hợp đồng đầu ra và tổng; không tính lại lợi ích hoặc tối ưu."""
    if result['status'] != 'success' or any(result[k] != config[k] for k in ['budget','seed','store','planning_horizon']):
        raise ValueError('Kết quả không thuộc đúng cấu hình vừa gửi.')
    allocation, summary = result['allocation'], result['summary']
    if allocation.columns.tolist() != list(COLUMN_NAMES) or allocation.shape != (15,5):
        raise ValueError('Bảng phân bổ phải có đúng 15 dòng và năm cột quy định.')
    if allocation.family.tolist() != list(families) or allocation.family.duplicated().any():
        raise ValueError('Thứ tự nhóm sản phẩm không khớp nguồn V5.')
    if (not pd.api.types.is_integer_dtype(allocation.promotion_level)
            or not allocation.promotion_level.isin([0,1,2,3]).all()
            or tuple(allocation.promotion_level) != tuple(result['vnls']['X'])):
        raise ValueError('Mức khuyến mãi không khớp véc-tơ kết quả.')
    if not np.isfinite(allocation.drop(columns='family').to_numpy(dtype=float)).all():
        raise ValueError('Bảng phân bổ có số không hữu hạn.')
    if not summary['is_feasible'] or summary['total_cost'] > config['budget']:
        raise ValueError('Không hiển thị nghiệm vi phạm ngân sách.')
    checks = [
        (summary['budget'], config['budget']),
        (summary['total_cost'], allocation.promotion_cost_usd.sum()),
        (summary['expected_sales'], allocation.D_hat_selected_7d.sum()),
        (summary['profit'], allocation.incremental_profit.sum()),
        (summary['remaining_budget'], config['budget']-summary['total_cost']),
        (summary['fitness'], summary['profit']),
        (summary['total_uplift'], result['vnls']['final']['total_uplift']),
        (summary['total_uplift'], summary['expected_sales']-result['vnls']['final']['baseline_sales']),
        (result['comparison']['hco_profit'], result['hco']['result']['profit']),
        (result['comparison']['final_profit'], summary['profit']),
    ]
    if any(not math.isfinite(float(a)) or not math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-8) for a,b in checks):
        raise ValueError('Tổng hợp kết quả không khớp bảng phân bổ hoặc hàm đánh giá.')
    return allocation.rename(columns=COLUMN_NAMES).copy()


def csv_bytes(table):
    """Không làm tròn số; chỉ tạo tệp tải xuống trong bộ nhớ."""
    return table.to_csv(index=False).encode('utf-8-sig')
