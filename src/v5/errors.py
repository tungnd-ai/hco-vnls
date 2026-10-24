"""Phân biệt ngân sách sai, chưa tìm được nghiệm khả thi và lỗi thực thi."""
import math


class V5EngineError(Exception):
    code = 'V5_ENGINE_ERROR'

    def __init__(self, message, *, budget=None, seed=None, stage=None, reason=None):
        super().__init__(message)
        self.budget = budget
        self.seed = seed
        self.stage = stage
        self.reason = reason

    def to_dict(self):
        """Trả thông tin lỗi, không có nghiệm hoặc kết quả cũ; xuất JSON được."""
        try:
            value = float(self.budget)
            safe_budget = value if math.isfinite(value) else repr(self.budget)
        except (TypeError, ValueError, OverflowError):
            safe_budget = repr(self.budget)[:200]
        return {'status': 'error', 'code': self.code, 'message': str(self),
                'requested_budget': safe_budget, 'seed': self.seed,
                'stage': self.stage, 'reason': self.reason}


class InvalidBudgetError(V5EngineError, ValueError):
    code = 'INVALID_BUDGET'


class NoFeasibleSolutionError(V5EngineError, RuntimeError):
    code = 'NO_FEASIBLE_SOLUTION_FOUND'


class OptimizationExecutionError(V5EngineError, RuntimeError):
    code = 'OPTIMIZATION_EXECUTION_ERROR'
