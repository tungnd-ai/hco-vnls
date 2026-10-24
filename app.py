"""Demo V5 độc lập: chỉ gọi bộ máy đã nghiệm thu, không ghi output nghiên cứu."""
import logging
import streamlit as st
import pandas as pd

from src.v5 import (run_hco_vnls, load_context, InvalidBudgetError,
                    NoFeasibleSolutionError, OptimizationExecutionError)
from src.v5_ui.presentation import (RESULT_KEY, CONFIG_KEY, ERROR_KEY, CHANGED_KEY,
                                     clear_output, validate_result, money, quantity, csv_bytes)
from src.v5_ui.dashboard import show_allocation_analytics,show_scenarios,show_threshold,show_diagnostics
from src.v5_ui.scenarios import run_main,EngineBusyError

st.set_page_config(page_title='Hỗ trợ phân bổ khuyến mãi | HCO-VNLS V5', page_icon='📊', layout='wide')
DEMO_SEED = 42


def input_changed():
    clear_output(st.session_state, changed=True)


def scientific_notes():
    with st.expander('Cơ sở khoa học và giới hạn sử dụng'):
        st.markdown('''- **Phạm vi:** Store 44, 15 nhóm sản phẩm, bốn mức khuyến mãi 0-3. Kỳ dự báo lịch sử là **16/08/2017 - 22/08/2017**, không phải bảy ngày tiếp theo từ hôm nay.
- **Dự báo:** dùng các kịch bản CatBoost đã tính sẵn của chuỗi nghiên cứu, kết hợp mô hình đánh giá hiệu quả kinh tế. Đổi ngân sách không huấn luyện lại CatBoost hoặc dự báo lại.
- **Tối ưu thật:** mỗi lần bấm chạy, HCO tìm phương án khả thi rồi VNLS thử cải thiện bằng các lân cận đã chốt. Không lấy nghiệm lưu sẵn ở Bước 7/8; không bảo đảm tối ưu toàn cục hoặc VNLS luôn cải thiện.
- **Mức khuyến mãi:** 0-3 là lựa chọn mã hóa theo từng nhóm, không phải phần trăm giảm giá.
- **Lượng bán và uplift:** là dự báo và chênh lệch dự báo so với không khuyến mãi, không phải doanh số thực quan sát hoặc bằng chứng nhân quả.
- **Mô hình đánh giá hiệu quả kinh tế:** lợi nhuận tăng thêm bằng lợi ích tăng thêm trừ chi phí khuyến mãi. Chỉ tiêu “Tổng lợi nhuận tăng thêm dự kiến từ khuyến mãi” đã trừ chi phí, không trừ thêm lần nữa; không phải tổng lợi nhuận kế toán của cửa hàng. 
- **Đơn vị hiển thị:** “Sản phẩm” là cách diễn đạt dễ hiểu cho lượng bán và chênh lệch dự báo tổng hợp của 15 nhóm; không chuyển đổi hoặc thay đổi phép đo sales gốc. “Bán thêm nhờ khuyến mãi” là chênh lệch mô hình dự báo, không phải kết luận nhân quả.
- **Ràng buộc:** chỉ hiển thị nghiệm khả thi. Nếu HCO chưa tìm được nghiệm khả thi, ứng dụng báo lỗi, không tự sửa nghiệm hoặc thêm nghiệm mồi.
- **Giới hạn so sánh:** một seed không chứng minh ưu thế thống kê; demo không chứng minh HCO-VNLS tốt hơn GA, PSO hoặc DE. Bốn ngân sách được thử không xác định ngân sách tối ưu toàn cục.
- **Tái lập:** mỗi nút chạy tạo yêu cầu mới, không chia sẻ cache (bộ nhớ đệm ứng viên) giữa các lần. Máy chủ xử lý tuần tự để hạn chế tranh chấp tài nguyên; phiên người dùng tách biệt. Làm mới trang có thể mất kết quả phiên, cần chạy lại.''')


def show_results(result):
    table = validate_result(result, st.session_state[CONFIG_KEY], load_context().families)
    summary, comparison = result['summary'], result['comparison']
    st.success('Đã hoàn tất: phương án phân bổ khuyến mãi do HCO-VNLS tìm được là khả thi.')
    st.caption(f"Kết quả lần chạy đã hoàn tất: Store 44 | 7 ngày | B = {money(result['budget'])}. "
               'Sửa đầu vào sẽ ẩn kết quả; chỉ nút chạy mới thực hiện tối ưu lại.')
    st.subheader('TỔNG HỢP KẾT QUẢ TỐI ƯU')
    metrics = [
        ('Tổng ngân sách', money(summary['budget'])),
        ('Ngân sách đã sử dụng', money(summary['total_cost'])),
        ('Ngân sách còn lại', money(summary['remaining_budget'])),
        ('Tổng số sản phẩm dự báo bán được', quantity(summary['expected_sales'])+' Sản phẩm'),
        ('Tổng số sản phẩm dự báo bán thêm nhờ khuyến mãi', quantity(summary['total_uplift'])+' Sản phẩm'),
        ('Tổng lợi nhuận tăng thêm dự kiến từ khuyến mãi', money(summary['profit'])),
    ]
    for start in [0,3]:
        for column, (label, value) in zip(st.columns(3), metrics[start:start+3]):
            with column:
                st.metric(label, value, border=True)
    st.caption('Lượng bán và uplift là dự báo; Profit đã trừ chi phí khuyến mãi.')
    show_allocation_analytics(result)
    st.subheader('BẢNG PHÂN BỔ NGÂN SÁCH KHUYẾN MÃI')
    st.caption('Đủ 15 nhóm theo thứ tự nghiên cứu. Mức 0 vẫn có thể có lượng bán dự báo dương.')
    st.dataframe(table.style.format({'Allocated Budget':money,'Expected Sales':quantity,'Incremental Profit':money}), hide_index=True, width='stretch', height=565, column_config={
        'Product Family': st.column_config.TextColumn('Product Family', help='Nhóm sản phẩm theo thứ tự chính thức.'),
        'Promotion Level': st.column_config.NumberColumn('Promotion Level', format='%d', help='Mức mã hóa 0-3, không phải phần trăm giảm giá.'),
        'Allocated Budget': st.column_config.NumberColumn('Allocated Budget', help='Chi phí khuyến mãi của nhóm.'),
        'Expected Sales': st.column_config.NumberColumn('Expected Sales', help='Lượng bán dự báo bảy ngày, đơn vị sản phẩm, không phải USD.'),
        'Incremental Profit': st.column_config.NumberColumn('Incremental Profit', help='Lợi nhuận tăng thêm của nhóm sau chi phí.'),
    })
    st.download_button('Tải bảng phân bổ CSV', csv_bytes(table),
                       file_name=f"phan_bo_B{result['budget']:g}.csv",
                       mime='text/csv', on_click='ignore')
    st.subheader('HIỆU QUẢ CẢI TIẾN HCO BẰNG VNLS')
    left, right = st.columns([1,1])
    with left:
        st.dataframe(pd.DataFrame({
            'Phương pháp': ['HCO ban đầu', 'HCO-VNLS cuối'],
            'Lợi nhuận tăng thêm (USD)': [comparison['hco_profit'], comparison['final_profit']],
            'Chi phí phân bổ (USD)': [comparison['hco_total_cost'], comparison['final_total_cost']],
        }), hide_index=True, width='stretch', column_config={
            'Lợi nhuận tăng thêm (USD)': st.column_config.NumberColumn(format='%.2f'),
            'Chi phí phân bổ (USD)': st.column_config.NumberColumn(format='%.2f')})
        st.metric('Cải thiện lợi nhuận tuyệt đối', money(comparison['profit_improvement']))
        pct = comparison['improvement_percent']
        from src.v5_ui.presentation import number
        st.metric('Cải thiện lợi nhuận (%)', 'Không xác định' if pct is None else number(pct)+'%')
        if pct is None:
            st.caption('Lợi nhuận HCO bằng 0 nên không tính phần trăm cải thiện.')
    with right:
        chart = pd.DataFrame({'Phương pháp':['HCO','HCO-VNLS'],
                              'Lợi nhuận tăng thêm (USD)':[comparison['hco_profit'],comparison['final_profit']]}).set_index('Phương pháp')
        st.bar_chart(chart, color='#237760', height=275, y_label='Lợi nhuận tăng thêm (USD)')
    if comparison['profit_improvement'] == 0:
        st.info('VNLS không tìm được cải thiện lợi nhuận trong lần chạy này.')
    st.caption('HCO cung cấp nghiệm khả thi xuất phát. VNLS xét hết từng lân cận và chỉ nhận cải thiện đủ điều kiện. Cải thiện 0% có thể là kết quả hợp lệ, không phải lỗi thuật toán.')
    execution = result['execution']
    st.caption(f"{execution['accepted_improvements']} bước cải thiện VNLS | "
               f"{execution['vnls_passes']} lượt lân cận | Thời gian bộ máy: {execution['runtime_seconds']:.2f} giây.")
    show_threshold(result)
    show_diagnostics(result)


def main():
    st.markdown('''<style>
    .block-container {max-width:1320px;padding-top:2rem;padding-bottom:3rem;}
    h1 {font-size:clamp(1.7rem,2.5vw,2.3rem) !important;letter-spacing:-.025em;color:#193A35;text-wrap:balance;}
    h2,h3 {letter-spacing:-.01em;}
    h3 {font-size:1.2rem !important;margin-top:1.1rem;}
    [data-testid="stMetric"] {background:#F2F7F5;border-color:#D8E4DE;padding:1rem;}
    button:focus-visible {outline:2px solid #17665B !important;outline-offset:3px;}
    [data-testid="stMetricValue"] {font-size:clamp(1rem,1.8vw,1.5rem);font-variant-numeric:tabular-nums;}
    [data-testid="stMetricValue"] > div {white-space:normal;overflow-wrap:anywhere;line-height:1.35;}
    [data-testid="stMetricLabel"] {font-size:.9rem;min-height:3.8em;align-items:flex-start;}
    [data-testid="stMetricLabel"] p {white-space:normal;overflow:visible;text-overflow:unset;line-height:1.35;}
    @media(max-width:768px) {.block-container{padding:1rem;} [data-testid="stMetricValue"]{font-size:1.35rem;}}
    </style>''', unsafe_allow_html=True)
    st.title('HỆ THỐNG HỖ TRỢ PHÂN BỔ NGÂN SÁCH KHUYẾN MÃI')
    st.write('Dự báo CatBoost kết hợp tối ưu HCO-VNLS cho 15 nhóm sản phẩm')
    st.caption('Store 44 | Kỳ lịch sử 16/08/2017 - 22/08/2017')
    st.caption('Các giá trị tiền là USD tham chiếu/mô phỏng, không phải số liệu kế toán thực của Favorita.')
    st.subheader('CẤU HÌNH KẾ HOẠCH KHUYẾN MÃI')
    with st.container(border=True):
        store, horizon, amount = st.columns([1,1,1.4])
        store.text_input('Cửa hàng đã kiểm chứng', 'Store 44', disabled=True)
        horizon.text_input('Thời hạn dự báo', '7 ngày', disabled=True,
                           help='Dự báo lịch sử 16/08/2017 - 22/08/2017, không phải bảy ngày từ hôm nay.')
        budget = amount.number_input('Ngân sách (USD)', value=768.0,
                                     format='%.6g', key='v5_budget', on_change=input_changed,
                                     help='Nhập số hữu hạn lớn hơn 0. Không có trần ngân sách tùy ý; ngân sách không phải số tiền thực quan sát tại Favorita.')
        st.caption('Chỉ tối ưu khi bấm nút bên dưới. Đổi ngân sách không huấn luyện lại CatBoost.')
        submitted = st.button('CHẠY TỐI ƯU HCO-VNLS', type='primary', width='stretch')
    if submitted:
        clear_output(st.session_state)
        config = {'budget':budget, 'seed':DEMO_SEED, 'store':44, 'planning_horizon':7}
        try:
            context = load_context(budget=budget)
            with st.spinner('Đang chạy HCO-VNLS, vui lòng đợi...'):
                result = run_main(budget)
                validate_result(result, config, context.families)
            st.session_state[CONFIG_KEY] = config
            st.session_state[RESULT_KEY] = result
        except EngineBusyError as exc:
            st.session_state[ERROR_KEY] = (str(exc),'ENGINE_BUSY')
        except MemoryError:
            st.session_state[ERROR_KEY] = ('Máy chủ không đủ bộ nhớ cho yêu cầu này. Vui lòng thử lại sau.','OUT_OF_MEMORY')
        except InvalidBudgetError as exc:
            st.session_state[ERROR_KEY] = ('Ngân sách không hợp lệ. '+str(exc), exc.code)
        except NoFeasibleSolutionError as exc:
            st.session_state[ERROR_KEY] = (str(exc), exc.code)
        except OptimizationExecutionError as exc:
            logging.exception('Lỗi bộ máy V5; không chấp nhận kết quả mới')
            st.session_state[ERROR_KEY] = ('Không hoàn thành tối ưu. Vui lòng kiểm tra nguồn dữ liệu hoặc liên hệ người vận hành.', exc.code)
        except Exception:
            logging.exception('Lỗi giao diện V5; không chấp nhận kết quả mới')
            st.session_state[ERROR_KEY] = ('Có lỗi ngoài dự kiến. Không có phương án mới được chấp nhận. Vui lòng kiểm tra nhật ký kỹ thuật.', 'UI_EXECUTION_ERROR')
    error = st.session_state.get(ERROR_KEY)
    if error:
        st.error(error[0])
        st.caption(f'Mã chẩn đoán: {error[1]}')
    result = st.session_state.get(RESULT_KEY)
    config = st.session_state.get(CONFIG_KEY)
    if result and config == {'budget':budget, 'seed':DEMO_SEED, 'store':44, 'planning_horizon':7}:
        try:
            show_results(result)
        except Exception:
            clear_output(st.session_state)
            logging.exception('Không thể kiểm tra hoặc hiển thị kết quả V5')
            st.error('Không thể kiểm tra hoặc hiển thị phương án. Kết quả đã được xóa; vui lòng kiểm tra nguồn dữ liệu và chạy lại.')
    elif result:
        clear_output(st.session_state, changed=True)
        st.info('Đầu vào đã thay đổi. Kết quả cũ đã được ẩn; hãy bấm chạy để tối ưu theo cấu hình mới.')
    elif st.session_state.get(CHANGED_KEY):
        st.info('Đầu vào đã thay đổi. Hãy bấm chạy để tính phương án cho cấu hình mới.')
    elif not error:
        st.info('Chưa có phương án. Nhập ngân sách rồi bấm CHẠY TỐI ƯU HCO-VNLS.')
    show_scenarios()
    scientific_notes()


if __name__ == '__main__':
    main()
