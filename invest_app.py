import streamlit as st
import pandas as pd
import plotly.express as px

# 1. ページ基本設定
st.set_page_config(page_title="資産シミュレーター", layout="centered")
st.markdown("### 📱 資産シミュレーター") 

# --- 2. URLから初期値を取得する関数 ---
def get_param(key, default):
    params = st.query_params
    if key in params:
        val = params[key]
        try:
            return float(val) if "." in val else int(val)
        except:
            return val
    return default

# --- 3. サイドバー設定エリア ---
st.sidebar.header("⚙️ 基本設定")
current_age = st.sidebar.number_input("現在の年齢", value=int(get_param("age", 30)), min_value=0, max_value=100)
end_age = st.sidebar.slider("終了年齢", int(current_age), 100, int(max(current_age, get_param("end", 85))))
initial_investment = st.sidebar.number_input("現在の一括投資額 (円)", value=int(get_param("init", 0)), step=100000)

with st.sidebar.expander("💰 積立の設定（2段階）"):
    monthly_deposit_1 = st.number_input("初期の月間積立 (円)", value=int(get_param("d1", 0)), step=5000)
    change_deposit_age = st.slider("積立額を変える年齢", int(current_age), int(end_age), int(max(current_age, get_param("cd", 45))))
    monthly_deposit_2 = st.number_input("変更後の月間積立 (円)", value=int(get_param("d2", 0)), step=5000)

with st.sidebar.expander("🏥 臨時出費の設定"):
    exp_1_v = st.number_input("出費1：金額 (円)", value=int(get_param("e1v", 0)), step=100000)
    exp_1_age = st.number_input("出費1：年齢", int(current_age), int(end_age), int(max(current_age, get_param("e1a", 40))))
    exp_2_v = st.number_input("出費2：金額 (円)", value=int(get_param("e2v", 0)), step=100000)
    exp_2_age = st.number_input("出費2：年齢", int(current_age), int(end_age), int(max(current_age, get_param("e2a", 50))))
    exp_3_v = st.number_input("出費3：金額 (円)", value=int(get_param("e3v", 0)), step=100000)
    exp_3_age = st.number_input("出費3：年齢", int(current_age), int(end_age), int(max(current_age, get_param("e3a", 60))))

st.sidebar.header("📉 年率設定")
is_simple_rate = st.sidebar.checkbox("年率を全期間で固定する", value=True)
if is_simple_rate:
    fixed_rate_val = st.sidebar.slider("固定年率 (%)", -15.0, 15.0, float(get_param("fr", 3.0)), 0.1)
    fixed_rate = fixed_rate_val / 100
else:
    with st.sidebar.expander("年率の詳細設定（3段階）", expanded=True):
        rate_1_val = st.slider("年率①：初期 (%)", -15.0, 15.0, 5.0, 0.1)
        cr1_age = st.slider("年率②への切替年齢", int(current_age), int(end_age), int(max(current_age, get_param("cr1", 45))))
        rate_2_val = st.slider("年率②：中期 (%)", -15.0, 15.0, 3.0, 0.1)
        cr2_age = st.slider("年率③への切替年齢", int(cr1_age), int(end_age), int(max(cr1_age, get_param("cr2", 65))))
        rate_3_val = st.slider("年率③：後期 (%)", -15.0, 15.0, 1.0, 0.1)
        rate_1, rate_2, rate_3 = rate_1_val/100, rate_2_val/100, rate_3_val/100

st.sidebar.header("🚪 取り崩し設定")
start_withdrawal_age = st.sidebar.slider("取り崩し開始年齢", int(current_age), int(end_age), int(max(current_age, get_param("wa", 65))))
withdrawal_type = st.sidebar.radio("取り崩し方法", ["定額 (円)", "定率 (%)"], index=0 if get_param("wt", "定額 (円)") == "定額 (円)" else 1)

with st.sidebar.expander("取り崩し額/率の設定（2段階）"):
    if withdrawal_type == "定額 (円)":
        wv1 = st.number_input("初期の取り崩し額 (円)", value=int(get_param("wv1", 0)), step=5000)
        cw_age = st.slider("取り崩し額を変える年齢", int(start_withdrawal_age), int(end_age), int(max(start_withdrawal_age, get_param("cw", 75))))
        wv2 = st.number_input("変更後の取り崩し額 (円)", value=int(get_param("wv2", 0)), step=5000)
    else:
        wr1 = st.slider("初期の取り崩し率 (%)", 0.0, 20.0, float(get_param("wr1", 0.0)), 0.1) / 100
        cw_age = st.slider("取り崩し率を変える年齢", int(start_withdrawal_age), int(end_age), int(max(start_withdrawal_age, get_param("cw", 75))))
        wr2 = st.slider("変更後の取り崩し率 (%)", 0.0, 20.0, float(get_param("wr2", 0.0)), 0.1) / 100

# --- 4. URLクエリパラメータの更新 ---
new_params = {
    "age": current_age, "end": end_age, "init": initial_investment,
    "d1": monthly_deposit_1, "cd": change_deposit_age, "d2": monthly_deposit_2,
    "e1a": exp_1_age, "e1v": exp_1_v, "e2a": exp_2_age, "e2v": exp_2_v, "e3a": exp_3_age, "e3v": exp_3_v,
    "wa": start_withdrawal_age, "wt": withdrawal_type, "cw": cw_age,
    "fr": fixed_rate_val if is_simple_rate else 3.0
}
if withdrawal_type == "定額 (円)": 
    new_params.update({"wv1": wv1, "wv2": wv2})
else: 
    new_params.update({"wr1": round(wr1*100,1), "wr2": round(wr2*100,1)})
st.query_params.update(**new_params)

# --- 5. 計算ロジック ---
def run_simulation():
    balance = initial_investment
    cumulative_inv = initial_investment
    data = []
    special_exp = {int((exp_1_age-current_age)*12+1): exp_1_v, int((exp_2_age-current_age)*12+1): exp_2_v, int((exp_3_age-current_age)*12+1): exp_3_v}
    total_months = int((end_age - current_age) * 12)
    
    for m in range(1, total_months + 1):
        p_age = current_age + (m / 12)
        d_age = int(current_age + (m - 1) // 12)
        
        ann_rate = fixed_rate if is_simple_rate else (rate_1 if p_age <= cr1_age else rate_2 if p_age <= cr2_age else rate_3)
        balance = max(0, balance - special_exp.get(m, 0))
        
        m_flow = 0
        if p_age > start_withdrawal_age:
            if withdrawal_type == "定額 (円)":
                m_flow = -(wv1 if p_age <= cw_age else wv2)
            else:
                curr_wr = wr1 if p_age <= cw_age else wr2
                m_flow = -(balance * curr_wr) / 12
            action = "取り崩し"
        else:
            m_flow = monthly_deposit_1 if p_age <= change_deposit_age else monthly_deposit_2
            cumulative_inv += m_flow
            action = "積立"
            
        balance = max(0, balance + m_flow) * (1 + ann_rate / 12)
        data.append({"年齢(グラフ)": p_age, "年齢": d_age, "月": f"{(m-1)%12+1}ヶ月目", "区分": action, "月間収支": int(m_flow), "臨時出費": int(special_exp.get(m, 0)), "元本": int(cumulative_inv), "資産残高": int(balance)})
        if balance <= 0 and p_age > start_withdrawal_age: break
    return pd.DataFrame(data)

# --- 6. 表示エリア ---
has_input = (initial_investment > 0 or monthly_deposit_1 > 0 or monthly_deposit_2 > 0)
if not has_input:
    st.info("👈 左側のメニューから設定を入力してください。")
else:
    df = run_simulation()
    f_bal = df.iloc[-1]['資産残高']
    col1, col2 = st.columns(2)
    with col1: st.metric(label=f"{end_age}歳時点の予想資産", value=f"¥{f_bal:,}")
    with col2:
        if f_bal <= 0: st.error(f"⚠️ {int(df.iloc[-1]['年齢(グラフ)'])}歳で資産消滅")
        else: st.success("✅ 資産を維持できています")
    
    fig = px.line(df, x="年齢(グラフ)", y="資産残高", labels={"年齢(グラフ)": "年齢", "資産残高": "資産残高(円)"}, template="plotly_white")
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=350, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
    
    with st.expander("📊 詳細データ"):
        st.dataframe(df[["年齢", "月", "区分", "月間収支", "臨時出費", "元本", "資産残高"]], use_container_width=True, hide_index=True)
    
    st.download_button(label="📥 CSV保存", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="sim_result.csv", mime="text/csv")
