"""Biểu đồ và so sánh ngân sách của giao diện, không đổi công thức nghiên cứu."""
import math
import logging
import altair as alt
import pandas as pd
import streamlit as st
from src.v5 import load_context
from .presentation import money,quantity,number,csv_bytes
from .analytics import allocation_analytics,threshold_facts,threshold_interpretation,scenario_interpretation
from .scenarios import (DEFAULT_BUDGETS,SCENARIO_KEY,SCENARIO_CONFIG,SCENARIO_CHANGED,
                        clear_scenarios,run_four_budgets,scenario_frame,EngineBusyError)

ACCENT='#17665B'


def bar_chart(frame, category, value, unit, *, horizontal=False, height=290):
    """Tooltip định dạng Việt Nam; số dùng vẽ vẫn là số gốc."""
    data=frame.copy()
    data['Giá trị hiển thị']=data[value].map(lambda x:number(x,2)+' '+unit)
    cat=alt.Y(category+':N',sort=data[category].tolist(),title=None) if horizontal else alt.X(category+':N',sort=data[category].tolist(),title=None,axis=alt.Axis(labelAngle=0))
    val=alt.X(value+':Q',title=unit,scale=alt.Scale(zero=True)) if horizontal else alt.Y(value+':Q',title=unit,scale=alt.Scale(zero=True))
    encoding={'y':cat,'x':val} if horizontal else {'x':cat,'y':val}
    chart=alt.Chart(data).mark_bar(color=ACCENT,cornerRadiusEnd=3).encode(
        **encoding,tooltip=[alt.Tooltip(category+':N',title='Nhóm / kịch bản'),
                            alt.Tooltip('Giá trị hiển thị:N',title=value)])
    return chart.properties(height=height).configure_view(stroke=None)


def show_allocation_analytics(result):
    st.subheader('PHÂN TÍCH PHƯƠNG ÁN PHÂN BỔ')
    hide=st.checkbox('Ẩn nhóm có ngân sách bằng 0',key='v5_hide_zero')
    a=allocation_analytics(result,hide)
    s=result['summary']
    st.caption(f'{a["promoted"]} nhóm được khuyến mãi · {a["zero"]} nhóm mức 0 · '
               f'{a["level3"]} nhóm mức 3 · Sử dụng {number(s["budget_utilization_percent"])}% ngân sách')
    left,right=st.columns([1.1,1])
    with left:
        st.markdown('**PHÂN BỔ NGÂN SÁCH THEO NHÓM SẢN PHẨM**')
        if a['budget'].empty:
            st.info('Không có nhóm nhận ngân sách dương để vẽ theo bộ lọc này.')
        else:
            st.altair_chart(bar_chart(a['budget'],'family','promotion_cost_usd','USD mô phỏng',horizontal=True,height=370),width='stretch')
    with right:
        st.markdown('**TOP 5 NHÓM SẢN PHẨM ĐÓNG GÓP LỢI NHUẬN TĂNG THÊM**')
        st.altair_chart(bar_chart(a['top5'],'family','incremental_profit','USD mô phỏng',horizontal=True,height=310),width='stretch')
        st.caption(a['top_text'])
    left,right=st.columns([1,1])
    with left:
        st.markdown('**PHÂN BỐ MỨC KHUYẾN MÃI**')
        levels=a['levels'].copy();levels['Mức khuyến mãi']=levels['Mức khuyến mãi'].map(lambda p:f'Mức {p}')
        st.altair_chart(bar_chart(levels,'Mức khuyến mãi','Số nhóm','nhóm',height=180),width='stretch')
    with right:
        st.markdown('**MỨC SỬ DỤNG NGÂN SÁCH**')
        ratio=s['total_cost']/s['budget']
        st.progress(min(1.0,max(0.0,ratio)),text=f'{number(s["budget_utilization_percent"])}% ngân sách được phân bổ')
        st.write(f'Đã dùng: {money(s["total_cost"])} · Còn lại: {money(s["remaining_budget"])}')
        st.caption('Không mặc định rằng sử dụng hết 100% ngân sách là tốt hơn. Mục tiêu là lợi nhuận tăng thêm dưới ràng buộc.')
    st.info(a['interpretation'])


def show_threshold(result, facts=None):
    facts=facts or threshold_facts(load_context())
    if not math.isclose(result['budget'],facts['all3_cost'],rel_tol=0,abs_tol=1e-9):
        return
    with st.expander('PHÂN TÍCH NGƯỠNG NGÂN SÁCH 2.091 USD',expanded=True):
        st.write(threshold_interpretation(result,facts))


def show_diagnostics(result):
    with st.expander('CHẨN ĐOÁN QUÁ TRÌNH TỐI ƯU'):
        st.caption('FE logic là số yêu cầu chấm nghiệm; lần gọi evaluator là số lần tính thật; cache hit là kết quả được dùng lại trong cùng pha.')
        h,v,e=result['hco'],result['vnls'],result['execution']
        st.write('Seed:',result['seed'])
        st.write('Ngân sách:',money(result['budget']))
        st.write('Véc-tơ HCO:',str(h['X']))
        st.write('Véc-tơ HCO-VNLS:',str(v['X']))
        st.write(f'Lợi nhuận HCO: {money(h["result"]["profit"])} · Cuối: {money(v["final"]["profit"])}')
        st.write(f'Chi phí cuối: {money(v["final"]["total_cost"])} · Khả thi: {v["final"]["is_feasible"]}')
        counters=pd.DataFrame([
            ['HCO',e['hco_logical_evaluations'],e['hco_evaluator_calls'],e['hco_logical_evaluations']-e['hco_evaluator_calls']],
            ['Ứng viên VNLS',v['candidate_requests'],v['unique_candidate_calls'],v['cache_hits']],
            ['Khởi đầu VNLS',v['initial_evaluator_calls'],v['initial_evaluator_calls'],0],
            ['Đối chiếu cuối',e['audit_evaluator_calls'],e['audit_evaluator_calls'],0],
        ],columns=['Pha','Yêu cầu đánh giá','Lần tính thật','Dùng lại bộ nhớ đệm'])
        st.dataframe(counters,hide_index=True,width='stretch')
        st.write(f'{e["accepted_improvements"]} bước được nhận · {e["vnls_passes"]} lượt lân cận · {number(e["runtime_seconds"],3)} giây')
        st.json({'P_scale':e['P_scale'],'penalty_lambda':e['penalty_lambda']})


def scenarios_changed():
    clear_scenarios(st.session_state)


def show_scenarios():
    st.subheader('PHÂN TÍCH VÀ SO SÁNH CÁC KỊCH BẢN NGÂN SÁCH')
    st.caption('Bốn lần tối ưu thật, tuần tự, cùng seed 42 và mô hình V5. Không ghi đè phương án chính; không dùng nghiệm lưu sẵn.')
    budgets=tuple(col.number_input(f'Ngân sách kịch bản {i+1} (USD)',value=b,format='%.6g',
                  key=f'v5_scenario_budget_{i}',on_change=scenarios_changed)
                  for i,(col,b) in enumerate(zip(st.columns(4),DEFAULT_BUDGETS)))
    if st.button('CHẠY SO SÁNH 4 KỊCH BẢN',key='v5_run_scenarios',type='secondary',width='stretch'):
        clear_scenarios(st.session_state,changed=False)
        progress=st.progress(0.0,text='Chuẩn bị so sánh bốn kịch bản')
        def update(done,total,budget):
            text=f'Hoàn tất {done}/{total} kịch bản'
            if budget is not None:
                text+=f' · Đang chạy kịch bản {done+1}: B = {money(budget)}'
            progress.progress(done/total,text=text)
        try:
            st.session_state[SCENARIO_KEY]=run_four_budgets(budgets,progress=update)
            st.session_state[SCENARIO_CONFIG]=budgets
        except EngineBusyError as exc:
            st.warning(str(exc))
        except Exception:
            logging.exception('Không hoàn tất bộ so sánh kịch bản')
            st.error('Không hoàn tất bộ so sánh. Không có kết quả cũ được dùng thay thế.')
    records=st.session_state.get(SCENARIO_KEY)
    if records is not None and st.session_state.get(SCENARIO_CONFIG)!=budgets:
        clear_scenarios(st.session_state)
        records=None
    if records is None:
        st.info('Nhập bốn ngân sách rồi bấm nút so sánh. Thay đầu vào sẽ ẩn bảng so sánh cũ, không tự tối ưu.')
        return
    frame=scenario_frame(records)
    formats={c:(quantity if c in ['Lượng bán dự báo','Uplift dự báo'] else lambda x:number(x,2))
             for c in frame.select_dtypes(include='number').columns}
    st.dataframe(frame.style.format(formats,na_rep='—'),hide_index=True,width='stretch')
    st.download_button('Tải bảng so sánh CSV',csv_bytes(frame),file_name='so_sanh_4_ngan_sach.csv',
                       mime='text/csv',key='v5_download_scenarios',on_click='ignore')
    for record in records:
        if record['error']:
            st.error(f'Kịch bản {record["scenario"]}: {record["error"]} ({record["code"]})')
    good=frame.loc[frame['Trạng thái'].eq('Thành công')].copy()
    if good.empty:
        st.warning('Không có kết quả thành công để vẽ; không biến lỗi thành số 0.')
        return
    good['Nhãn ngân sách']=good.apply(lambda row:f'{row["Kịch bản"]} · {number(row["Ngân sách"],0)} USD',axis=1)
    st.caption('Biểu đồ chỉ gồm kịch bản thành công; trường hợp lỗi được giữ trong bảng và CSV, không gán giá trị giả.')
    left,right=st.columns(2)
    with left:
        st.markdown('**LỢI NHUẬN HCO-VNLS THEO NGÂN SÁCH**')
        st.altair_chart(bar_chart(good,'Nhãn ngân sách','Lợi nhuận HCO-VNLS','USD mô phỏng',horizontal=True),width='stretch')
    with right:
        st.markdown('**TỶ LỆ CẢI THIỆN VNLS THEO NGÂN SÁCH**')
        known=good.dropna(subset=['Cải thiện (%)'])
        if known.empty:
            st.info('Tỷ lệ không xác định khi lợi nhuận HCO bằng 0; không thay bằng 0%.')
        else:
            st.altair_chart(bar_chart(known,'Nhãn ngân sách','Cải thiện (%)','%',horizontal=True),width='stretch')
        if len(known)<len(good):
            st.caption('Một số tỷ lệ không xác định vì lợi nhuận HCO bằng 0; xem bảng để biết kịch bản.')
    st.markdown('**NGÂN SÁCH ĐẦU VÀO VÀ CHI PHÍ ĐÃ PHÂN BỔ**')
    long=good.melt(id_vars=['Nhãn ngân sách'],value_vars=['Ngân sách','Đã sử dụng'],var_name='Đại lượng',value_name='USD mô phỏng')
    st.altair_chart(alt.Chart(long).mark_bar().encode(y=alt.Y('Nhãn ngân sách:N',sort=good['Nhãn ngân sách'].tolist(),title=None),
        x=alt.X('USD mô phỏng:Q'),yOffset='Đại lượng:N',color=alt.Color('Đại lượng:N',scale=alt.Scale(range=['#B7CFC8',ACCENT])),
        tooltip=['Nhãn ngân sách','Đại lượng','USD mô phỏng']).properties(height=250),width='stretch')
    st.info(scenario_interpretation(frame))
    facts=threshold_facts(load_context())
    for record in records:
        if record['result'] is not None:
            show_threshold(record['result'],facts)
