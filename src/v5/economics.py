"""Nạp bảng V5 và đánh giá trong ngữ cảnh riêng, không dùng ngân sách toàn cục."""
from dataclasses import dataclass, field
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .config import LEVELS
from .errors import InvalidBudgetError

ROOT = Path(__file__).resolve().parents[2]
DATA_HASHES = {
    'step5_v5_family_index.csv': '33006757008a37027de588b9bf3805312a9e0f18385a71b813aab40500f5aa2a',
    'step5_v5_economic_lookup.csv': '41113b469af0c100cdef927e0f4f9c07de27ecac8761dd3b32c6d5121d30fa3c',
    'step5_v5_metadata.json': 'd84d634090f6991eb808275976944bb32a8ac8abc8c0415d1f24c4ee30d08a0e',
}


@dataclass(frozen=True)
class EconomicContext:
    """Ngân sách và bảng tra thuộc riêng một ngữ cảnh đánh giá.

    Ngân sách và hệ số phạt được tính riêng cho từng yêu cầu.
    Không sửa trực tiếp các thuộc tính bảng tra bắt đầu bằng dấu gạch dưới.
    """

    families: tuple
    budget: float
    p_scale: float
    penalty_lambda: float
    _lookup: pd.DataFrame
    _candidate_values: dict = field(init=False, repr=False)
    _family_rows: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        # Chỉ đổi cách truy xuất bảng tra; thứ tự cộng vẫn là thứ tự 15 nhóm.
        ordered = self._lookup.loc[[(f, p) for f in self.families for p in LEVELS]]
        values = {}
        for name in ('promotion_cost_usd', 'incremental_profit', 'uplift_7d',
                     'D_hat_selected_7d', 'D_hat_0_7d'):
            matrix = ordered[name].to_numpy(copy=True).reshape(len(self.families), len(LEVELS))
            matrix.setflags(write=False)
            values[name] = matrix
        rows = np.arange(len(self.families))
        rows.setflags(write=False)
        object.__setattr__(self, '_candidate_values', values)
        object.__setattr__(self, '_family_rows', rows)

    def evaluate_candidate(self, X):
        """Chấm nghiệm không tạo bảng chi tiết cho từng ứng viên bị loại."""
        if not isinstance(X, (list, tuple, np.ndarray)) or len(X) != len(self.families):
            raise ValueError('X cần đúng 15 mức khuyến mãi theo thứ tự nhóm đã quy định.')
        if any(isinstance(p, (bool, np.bool_)) or not isinstance(p, (int, np.integer)) or p not in LEVELS for p in X):
            raise ValueError('Mỗi phần tử của X phải là số nguyên thuộc 0, 1, 2, 3; không nhận bool hoặc số thực.')
        solution = tuple(int(p) for p in X)
        totals = {name: float(np.sum(matrix[self._family_rows, solution]))
                  for name, matrix in self._candidate_values.items()}
        total_cost = totals['promotion_cost_usd']
        profit = totals['incremental_profit']
        violation = max(0.0, total_cost-self.budget)
        penalty = self.penalty_lambda*violation
        return {'solution': solution, 'total_cost': total_cost, 'profit': profit, 'budget': self.budget,
                'budget_violation': violation, 'P_scale': self.p_scale, 'penalty_lambda': self.penalty_lambda,
                'penalty': penalty, 'fitness': profit-penalty, 'is_feasible': bool(total_cost <= self.budget),
                'total_uplift': totals['uplift_7d'], 'expected_sales': totals['D_hat_selected_7d'],
                'baseline_sales': totals['D_hat_0_7d']}

    def breakdown(self, solution):
        """Tạo bảng chi tiết khi đã chọn nghiệm, không chấm lại trong thuật toán."""
        return self._lookup.loc[[(f, p) for f, p in zip(self.families, solution)]].reset_index()

    def evaluate_solution(self, X):
        if not isinstance(X, (list, tuple, np.ndarray)) or len(X) != len(self.families):
            raise ValueError('X cần đúng 15 mức khuyến mãi theo thứ tự nhóm đã quy định.')
        if any(isinstance(p, (bool, np.bool_)) or not isinstance(p, (int, np.integer)) or p not in LEVELS for p in X):
            raise ValueError('Mỗi phần tử của X phải là số nguyên thuộc 0, 1, 2, 3; không nhận bool hoặc số thực.')
        solution = tuple(int(p) for p in X)
        chosen = self._lookup.loc[[(f, p) for f, p in zip(self.families, solution)]].reset_index()
        total_cost = float(chosen.promotion_cost_usd.sum())
        profit = float(chosen.incremental_profit.sum())
        violation = max(0.0, total_cost-self.budget)
        penalty = self.penalty_lambda*violation
        fitness = profit-penalty
        return {'solution': solution, 'total_cost': total_cost, 'profit': profit, 'budget': self.budget,
                'budget_violation': violation, 'P_scale': self.p_scale, 'penalty_lambda': self.penalty_lambda,
                'penalty': penalty, 'fitness': fitness, 'is_feasible': bool(total_cost <= self.budget),
                'total_uplift': float(chosen.uplift_7d.sum()), 'breakdown': chosen,
                'expected_sales': float(chosen.D_hat_selected_7d.sum()),
                'baseline_sales': float(chosen.D_hat_0_7d.sum())}


def load_context(root=ROOT, budget=768.0):
    """Chỉ nạp ba đầu vào V5; không phụ thuộc notebook hay kết quả tối ưu đã lưu."""
    if isinstance(budget, (bool, np.bool_)) or not isinstance(budget, (int, float, np.integer, np.floating)):
        raise InvalidBudgetError('Ngân sách phải là số hữu hạn, không nhận bool hoặc chuỗi.',
                                 budget=budget, stage='INPUT', reason='TYPE')
    try:
        budget = float(budget)
    except (ValueError, OverflowError) as exc:
        raise InvalidBudgetError('Ngân sách vượt khả năng biểu diễn số thực của bộ máy.',
                                 budget=budget, stage='INPUT', reason='NUMERIC_RANGE') from exc
    if not np.isfinite(budget) or budget <= 0:
        raise InvalidBudgetError('Ngân sách phải hữu hạn và lớn hơn 0.',
                                 budget=budget, stage='INPUT', reason='NONPOSITIVE_OR_NONFINITE')
    out = Path(root) / 'outputs'
    for name, expected in DATA_HASHES.items():
        path = out / name
        if not path.is_file():
            raise ValueError(f'Thiếu đầu vào V5: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Đầu vào V5 khác bản đã chốt: {name}')
    metadata = json.loads((out / 'step5_v5_metadata.json').read_text(encoding='utf-8-sig'))
    index = pd.read_csv(out / 'step5_v5_family_index.csv')
    lookup = pd.read_csv(out / 'step5_v5_economic_lookup.csv')
    families = tuple(index.family)
    if (metadata['version'] != 'V5' or metadata['store'] != 44 or metadata['planning_horizon_days'] != 7
            or metadata['promotion_levels'] != list(LEVELS) or len(families) != 15
            or len(set(families)) != 15 or list(families) != metadata['family_order']
            or index.family_index.tolist() != list(range(1, 16))):
        raise ValueError('Phiên bản, phạm vi hoặc thứ tự nhóm V5 không hợp lệ.')
    required = {'family', 'promotion_level', 'mapped_onpromotion', 'D_hat_0_7d', 'D_hat_selected_7d',
                'uplift_7d', 'price_usd_reference', 'margin_rate', 'unit_margin_usd_reference',
                'gross_incremental_margin', 'promotion_cost_usd', 'incremental_profit'}
    if not required <= set(lookup) or len(lookup) != 60 or lookup.duplicated(['family', 'promotion_level']).any():
        raise ValueError('Bảng kinh tế phải có đủ 60 khóa nhóm–mức duy nhất.')
    keys = set(zip(lookup.family, lookup.promotion_level))
    if keys != {(f, p) for f in families for p in LEVELS} or lookup.isna().any().any():
        raise ValueError('Bảng kinh tế thiếu lựa chọn hoặc có giá trị thiếu.')
    numeric = lookup.drop(columns='family').to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise ValueError('Bảng kinh tế có số không hữu hạn.')
    reference_budget = float(lookup.loc[lookup.promotion_level.eq(1), 'promotion_cost_usd'].sum())
    p_scale = float(lookup.groupby('family').incremental_profit.max().sum())
    if reference_budget != metadata['budget']:
        raise ValueError('Ngân sách tham chiếu không khớp dữ liệu V5.')
    if not np.isclose(p_scale, metadata['P_scale'], rtol=1e-12, atol=1e-10):
        raise ValueError('Thang lợi nhuận không khớp dữ liệu V5.')
    if not np.isclose(p_scale/reference_budget, metadata['penalty_lambda'], rtol=1e-12, atol=1e-10):
        raise ValueError('Hệ số phạt không khớp dữ liệu V5.')
    penalty_lambda = p_scale / budget
    max_violation = max(0.0, float(lookup.groupby('family').promotion_cost_usd.max().sum())-budget)
    if (not np.isfinite(penalty_lambda) or penalty_lambda <= 0
            or (max_violation > 0 and penalty_lambda > sys.float_info.max/max_violation)):
        raise InvalidBudgetError('Ngân sách quá nhỏ để tính hệ số phạt và điểm phạt hữu hạn bằng số thực 64-bit.',
                                 budget=budget, stage='INPUT', reason='NUMERIC_RANGE')
    return EconomicContext(families, float(budget), p_scale, penalty_lambda,
                           lookup.set_index(['family', 'promotion_level']).copy(deep=True))
