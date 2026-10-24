"""Phân tích từ kết quả đã hoàn tất; không gọi thuật toán hoặc evaluator."""
import numpy as np
import pandas as pd
from .presentation import money, number


def allocation_analytics(result, hide_zero=False):
    table = result['allocation'].copy(deep=True)
    budget = table.sort_values('promotion_cost_usd', ascending=False, kind='stable').copy()
    if hide_zero:
        budget = budget.loc[budget.promotion_cost_usd.ne(0)].copy()
    top = table.sort_values('incremental_profit', ascending=False, kind='stable').head(5).copy()
    levels = pd.DataFrame({'Mức khuyến mãi':range(4), 'Số nhóm':[
        int(table.promotion_level.eq(p).sum()) for p in range(4)]})
    promoted = int(table.promotion_level.gt(0).sum())
    cost_row = table.loc[table.promotion_cost_usd.idxmax()]
    profit_row = top.iloc[0]
    s = result['summary']
    cost_text = (f'Nhóm nhận chi phí cao nhất: {cost_row.family} ({money(cost_row.promotion_cost_usd)}).'
                 if table.promotion_cost_usd.gt(0).any() else 'Không có nhóm nào nhận chi phí khuyến mãi dương.')
    best_text = f'Nhóm có lợi nhuận tăng thêm cao nhất: {profit_row.family} ({money(profit_row.incremental_profit)}).'
    if top.incremental_profit.nunique() == 1:
        best_text += ' Có các nhóm đồng hạng; biểu đồ giữ thứ tự nghiên cứu khi bằng giá trị.'
    return {'budget':budget, 'top5':top, 'levels':levels, 'promoted':promoted,
            'zero':int(table.promotion_level.eq(0).sum()), 'level3':int(table.promotion_level.eq(3).sum()),
            'top_text':best_text,
            'interpretation':f'{promoted}/15 nhóm được khuyến mãi. {cost_text} {best_text} '
                f'Sử dụng {number(s["budget_utilization_percent"])}% ngân sách. '
                f'Phương án {"khả thi" if s["is_feasible"] else "không khả thi"}; không khẳng định tối ưu toàn cục.'}


def threshold_facts(context):
    """Kiểm tra từ bảng tra, không suy đoán mức 3 luôn là chi phí lớn nhất."""
    table = context._lookup.reset_index()
    high = table.loc[table.promotion_level.eq(3)].set_index('family').loc[list(context.families)]
    maxima = table.groupby('family').promotion_cost_usd.max().loc[list(context.families)]
    return {'all3_cost':float(high.promotion_cost_usd.sum()), 'maximum_cost':float(maxima.sum()),
            'level3_max_each':bool(np.array_equal(high.promotion_cost_usd.to_numpy(),maxima.to_numpy()))}


def threshold_interpretation(result, facts):
    h, v = tuple(result['hco']['X']), tuple(result['vnls']['X'])
    all3 = h == v == (3,)*15
    zero = result['summary']['profit_improvement'] == 0
    passes = result['vnls']['passes'].neighborhood.tolist()
    confirmed = all3 and zero and passes == ['N1','N2','N3']
    text = (f'Chi phí toàn mức 3 được tính từ bảng tra: {money(facts["all3_cost"])}; '
            f'tổng chi phí tối đa theo từng nhóm: {money(facts["maximum_cost"])}. '
            f'Mức 3 là lựa chọn chi phí cao nhất của từng nhóm: {"đúng" if facts["level3_max_each"] else "không đúng"}. ')
    if confirmed:
        text += ('Trong lần chạy này, HCO và HCO-VNLS đều chọn mức 3 cho cả 15 nhóm; '
                 'VNLS xét N1, N2, N3, nhận 0 bước và cải thiện 0%. Không còn bước tăng mức '
                 'trong miền 0–3; các lân cận đã xét không tạo cải thiện khả thi vượt ngưỡng. ')
    else:
        text += ('Kết quả thực tế không thỏa toàn bộ điều kiện toàn mức 3/không cải thiện/ba lượt; '
                 'không áp diễn giải 0% của ví dụ trước cho lần chạy này. ')
    return text + ('Dùng hết ngân sách hoặc không cải thiện cục bộ không tự chứng minh tối ưu toàn cục; '
                   'không suy ra kết quả cho seed khác hay mọi ngân sách lớn hơn. '
                   'Đóng góp của VNLS phụ thuộc nghiệm HCO xuất phát và các lân cận còn cải thiện được.')


def scenario_interpretation(frame):
    good = frame.loc[frame['Trạng thái'].eq('Thành công')].copy()
    if good.empty:
        return 'Không có kịch bản thành công để so sánh; không thay lỗi bằng giá trị dự báo.'
    def pick(column):
        row = good.loc[good[column].idxmax()]
        return f'{row["Kịch bản"]} (B = {money(row["Ngân sách"])})'
    ordered = good.sort_values('Ngân sách',kind='stable')
    differences = ordered['Lợi nhuận HCO-VNLS'].diff().dropna()
    trend = ('chỉ có một ngân sách thành công, chưa thể đánh giá xu hướng' if len(good)<2 else
             'tăng nghiêm ngặt theo ngân sách đã thử' if differences.gt(0).all() else
             'không giảm nhưng không phải lúc nào cũng tăng' if differences.ge(0).all() else
             'không tăng nhất quán theo ngân sách đã thử')
    pct = good.dropna(subset=['Cải thiện (%)'])
    improve = ('không xác định được tỷ lệ cải thiện' if pct.empty else
               f'tỷ lệ cải thiện VNLS lớn nhất: {pick_from(pct,"Cải thiện (%)")}')
    return (f'Trong {len(good)}/{len(frame)} kịch bản thành công: lợi nhuận quan sát cao nhất ở '
            f'{pick("Lợi nhuận HCO-VNLS")}; chi phí lớn nhất ở {pick("Đã sử dụng")}; '
            f'{improve}; ngân sách còn lại lớn nhất ở {pick("Còn lại")}. '
            f'Lợi nhuận {trend}. Các trường hợp đồng hạng được chọn theo thứ tự kịch bản. '
            'Chỉ xét các lần chạy thành công, một seed cố định; không phải benchmark nhiều seed '
            'hoặc bằng chứng về ngân sách tối ưu toàn cục.')


def pick_from(frame, column):
    row = frame.loc[frame[column].idxmax()]
    return f'{row["Kịch bản"]} (B = {money(row["Ngân sách"])}, {number(row[column])}%)'
