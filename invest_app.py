import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. ページ基本設定
st.set_page_config(page_title="資産シミュレーター", layout="centered")
st.markdown("### 📱 資産シミュレーター") 

# --- 2. URLから初期値を取得する関数 ---
def get_param(key, default):
    params = st.query_params
    if key in params:
        val = params.get(key)
        try:
            return float(val) if "." in val else int(val)
        except:
            return val
    return default

# --- 3. サイドバー設定エリア ---
st.sidebar.header("⚙️ 基本設定")
current_age = st.sidebar.number_input("現在の年齢", value=int(get_param("age", 30)), min_value=0, max_value=100, key="input_age")
end_age = st.sidebar.slider("終了年齢", int(current_age), 100, int(max(current_age, get_param("end", 85))), key="input_end")
initial_investment = st.sidebar.number_input("現在の一括投資額 (円)", value=int(get_param("init", 0)), step=100000, key="input_init")

with st.sidebar.expander("💰 積立の設定（2段階）"):
    monthly_deposit_1 = st.number_input("初期の月間積立 (円)", value=int(get_param("d1", 0)), step=5000, key="input_d1")
    change_deposit_age = st.slider("積立額を変える年齢", int(current_age), int(end_age), int(max(current_age, get_param("cd", 45))), key="input_cd")
    monthly_deposit_2 = st.number_input("変更後の月間積立 (円)", value=int(get_param("d2", 0)), step=5000, key="input_d2")

with st.sidebar.expander("🏥 臨時出費の設定"):
    exp_1_v = st.number_input("出費1：金額 (円)", value=int(get_param("e1v", 0)), step=100000, key="input_e1v")
    exp_1_age = st.number_input("出費1：年齢", int(current_age), int(end_age), int(max(current_age, get_param("e1a", 40))), key="input_e1a")
    exp_2_v = st.number_input("出費2：金額 (円)", value=int(get_param("e2v", 0)), step=100000, key="input_e2v")
    exp_2_age = st.number_input("出費2：年齢", int(current_age), int(end_age), int(max(current_age, get_param("e2a", 50))), key="input_e2a")
    exp_3_v = st.number_input("出費3：金額 (円)", value=int(get_param("e3v", 0)), step=100000, key="input_e3v")
    exp_3_age = st.number_input("出費3：年齢", int(current_age), int(end_age), int(max(current_age, get_param("e3a", 60))), key="input_e3a")

st.sidebar.header("📉 年率設定")
is_simple_rate = st.sidebar.checkbox("年率を全期間で固定する", value=True, key="input_simple")
if is_simple_rate:
    fixed_rate_val = st.sidebar.slider("固定年率 (%)", -15.0, 15.0, float(get_param("fr", 3.0)), 0.1, key="input_fr")
    fixed_rate = fixed_rate_val / 100
    avg_annual_rate = fixed_rate_val # 固定の場合はそのまま
else:
    with st.sidebar.expander("年率の詳細設定（3段階）", expanded=True):
        rate_1_val = st.slider("年率①：初期 (%)", -15.0, 15.0, 5.0, 0.1, key="input_r1")
        change_rate_age_1 = st.slider("②への切替年齢", int(current_age), int(end_age), int(max(current_age, get_param("cr1", 45))), key="input_cr1")
        rate_2_val = st.slider("年率②：中期 (%)", -15.0, 15.0, 3.0, 0.1, key="input_r2")
        change_rate_age_2 = st.slider("③への切替年齢", int(change_rate_age_1), int(end_age), int(max(change_rate_age_1, get_param("cr2", 65))), key="input_cr2")
        rate_3_val = st.slider("年率③：後期 (%)", -15.0, 15.0, 1.0, 0.1, key="input_r3")
        rate_1, rate_2, rate_3 = rate_1_val/100, rate_2_val/100, rate_3_val/100
        
        # 加重平均年率の計算
        total_y = end_age - current_age
        if total_y > 0:
            y1 = change_rate_age_1 - current_age
            y2 = change_rate_age_2 - change_rate_age_1
            y3 = end_age - change_rate_age_2
            avg_annual_rate = (rate_1_val * y1 + rate_2_val * y2 + rate_3_val * y3) / total_y
        else:
            avg_annual_rate = 0

st.sidebar.header("🚪 取り崩し設定（2段階）")
start_withdrawal_age = st.sidebar.slider("取り崩し開始年齢", int(current_age), int(end_age), int(max(current_age, get_param("wa", 65))), key="input_wa")
wt1_def = get_param("wt1", "定額 (円)")
wt1 = st.sidebar.radio("方法①", ["定額 (円)", "定率 (%)"], index=0 if wt1_def == "定額 (円)" else 1, key="input_wt1")
wv1 = st.sidebar.number_input("額/率①", value=float(get_param("wv1", 0.0)), step=5000.0 if wt1 == "定額 (円)" else 0.1, key="input_wv1")
cw_age = st.sidebar.slider("切り替える年齢", int(start_withdrawal_age), int(end_age), int(max(start_withdrawal_age, get_param("cw", 75))), key="input_cw")
wt2_def = get_param("wt2", "定額 (円)")
wt2 = st.sidebar.radio("方法②", ["定額 (円)", "定率 (%)"], index=0 if wt2_def == "定額 (円)" else 1, key="input_wt2")
wv2 = st.sidebar.number_input("額/率②", value=float(get_param("wv2", 0.0)), step=5000.0 if wt2 == "定額 (円)" else 0.1, key="input_wv2")

# --- 4. 計算ロジック ---
def run_simulation():
    balance = initial_investment
    cumulative_inv = initial_investment
    data = []
    special_exp = {int((exp_1_age-current_age)*12+1): exp_1_v, int((exp_2_age-current_age)*12+1): exp_2_v, int((exp_3_age-current_age)*12+1): exp_3_v}
    total_months = int((end_age - current_age) * 12)
    
    for m in range(1, total_months + 1):
        p_age = current_age + (m / 12)
        d_age = int(current_age + (m - 1) // 12)
        ann_rate = fixed_rate if is_simple_rate else (rate_1 if p_age <= change_rate_age_1 else rate_2 if p_age <= change_rate_age_2 else rate_3)
        balance = max(0, balance - special_exp.get(m, 0))
        m_flow = 0
        if p_age > start_withdrawal_age:
            target_wt = wt1 if p_age <= cw_age else wt2
            target_wv = wv1 if p_age <= cw_age else wv2
            m_flow = -target_wv if target_wt == "定額 (円)" else -(balance * (target_wv / 100)) / 12
            action = "取り崩し"
        else:
            m_flow = monthly_deposit_1 if p_age <= change_deposit_age else monthly_deposit_2
            cumulative_inv += m_flow
            action = "積立"
        balance = max(0, balance + m_flow) * (1 + ann_rate / 12)
        data.append({"年齢(グラフ)": p_age, "年齢": d_age, "月": f"{(m-1)%12+1}ヶ月目", "区分": action, "月間収支": int(m_flow), "臨時出費": int(special_exp.get(m, 0)), "元本合計": int(cumulative_inv), "資産残高": int(balance)})
        if balance <= 0 and p_age > start_withdrawal_age: break
    return pd.DataFrame(data)

# --- 5. 表示エリア ---
has_input = (initial_investment > 0 or monthly_deposit_1 > 0 or monthly_deposit_2 > 0)
if not has_input:
    st.info("👈 左側のメニューから設定を入力してください。")
else:
    df = run_simulation()
    f_bal = df.iloc[-1]['資産残高']
    f_age = df.iloc[-1]['年齢(グラフ)']
    
    # 画面上部のサマリー
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label=f"{end_age}歳時点の予想資産", value=f"¥{f_bal:,}")
    with col2:
        st.metric(label="全期間の平均年率", value=f"{avg_annual_rate:.2f}%")
    with col3:
        if f_bal <= 0: st.error(f"⚠️ {int(f_age)}歳で消滅")
        else: st.success("✅ 資産維持")

    df["資産(万円)"] = df["資産残高"] / 10000
    df["元本(万円)"] = df["元本合計"] / 10000
    max_val = max(df["資産(万円)"].max(), df["元本(万円)"].max())
    y_upper = max_val * 1.15 if max_val > 0 else 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["年齢(グラフ)"], y=df["資産(万円)"], name="資産残高", line=dict(color="#1f77b4", width=3)))
    fig.add_trace(go.Scatter(x=df["年齢(グラフ)"], y=df["元本(万円)"], name="投資元本", line=dict(color="#ff7f0e", width=2, dash="dash")))

    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=400, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), yaxis_title="金額 (万円)", template="plotly_white")
    grid_color, zero_line_color = "rgba(128, 128, 128, 0.3)", "gray"
    fig.update_xaxes(title="年齢 (歳)", range=[current_age - 2, end_age + 2], dtick=5, showgrid=True, gridcolor=grid_color, gridwidth=1, griddash='dot', zeroline=True, zerolinecolor=zero_line_color, zerolinewidth=2)
    fig.update_yaxes(range=[-max_val*0.05, y_upper], ticksuffix="万", tickformat=",", showgrid=True, gridcolor=grid_color, gridwidth=1, griddash='dot', zeroline=True, zerolinecolor=zero_line_color, zerolinewidth=2) 
    fig.add_annotation(x=current_age, y=0, text=f"開始:{current_age}歳", showarrow=True, arrowhead=1, yshift=-20)
    fig.add_annotation(x=f_age, y=df.iloc[-1]["資産(万円)"], text=f"終了:{int(f_age)}歳", showarrow=True, arrowhead=1, ax=40, ay=-40)
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("📊 詳細データ"):
        st.dataframe(df[["年齢", "月", "区分", "月間収支", "臨時出費", "元本合計", "資産残高"]], use_container_width=True, hide_index=True)
    st.download_button(label="📥 CSV保存", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="sim_result.csv", mime="text/csv")

# --- 6. URLクエリパラメータ更新 ---
new_params = {"age": current_age, "end": end_age, "init": initial_investment, "d1": monthly_deposit_1, "cd": change_deposit_age, "d2": monthly_deposit_2, "e1a": exp_1_age, "e1v": exp_1_v, "e2a": exp_2_age, "e2v": exp_2_v, "e3a": exp_3_age, "e3v": exp_3_v, "wa": start_withdrawal_age, "wt1": wt1, "wv1": wv1, "cw": cw_age, "wt2": wt2, "wv2": wv2}
if is_simple_rate: new_params["fr"] = fixed_rate_val
else: new_params.update({"cr1": change_rate_age_1, "cr2": change_rate_age_2, "r1": rate_1_val, "r2": rate_2_val, "r3": rate_3_val})
st.query_params.update(**new_params)
