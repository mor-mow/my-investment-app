import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. ページ基本設定
st.set_page_config(page_title="資産シミュレーター", layout="centered")
st.markdown("### 📱 資産シミュレーター") 

# --- 2. URLから初期値を安全に取得する関数 ---
def get_param(key, default):
    params = st.query_params
    if key in params:
        val = params.get(key)
        try:
            if "." in str(val): return float(val)
            return int(val)
        except: return val
    return default

# --- 3. サイドバー設定エリア ---
st.sidebar.header("⚙️ 基本設定")
c_age_val = get_param("age", 30)
current_age = st.sidebar.number_input("現在の年齢", 0, 100, int(c_age_val), key="input_age")

e_age_def = get_param("end", 85)
end_age = st.sidebar.slider("終了年齢", int(current_age), 100, int(max(current_age, e_age_def)), key="input_end")

init_def = get_param("init", 0)
initial_sum = st.sidebar.number_input("現在の一括投資額 (円)", 0, None, int(init_def), 100000, key="input_init")

with st.sidebar.expander("💰 積立の設定（2段階）"):
    d1_def = get_param("d1", 0)
    dep1 = st.number_input("初期の月間積立 (円)", 0, None, int(d1_def), 5000, key="input_d1")
    cd_def = get_param("cd", 45)
    dep_change_age = st.slider("積立額を変える年齢", int(current_age), int(end_age), int(max(current_age, cd_def)), key="input_cd")
    d2_def = get_param("d2", 0)
    dep2 = st.number_input("変更後の月間積立 (円)", 0, None, int(d2_def), 5000, key="input_d2")

st.sidebar.header("📉 年率設定（3段階）")
is_simple = st.sidebar.checkbox("年率を全期間で固定する", value=True, key="input_simple")
if is_simple:
    fr_def = get_param("fr", 3.0)
    fixed_rate = st.sidebar.slider("固定年率 (%)", -15.0, 15.0, float(fr_def), 0.1, key="input_fr") / 100
else:
    r1 = st.sidebar.slider("年率①：初期 (%)", -15.0, 15.0, 5.0, 0.1, key="input_r1") / 100
    cr1 = st.sidebar.slider("②への切替年齢", int(current_age), int(end_age), 45, key="input_cr1")
    r2 = st.sidebar.slider("年率②：中期 (%)", -15.0, 15.0, 3.0, 0.1, key="input_r2") / 100
    cr2 = st.sidebar.slider("③への切替年齢", int(cr1), int(end_age), 65, key="input_cr2")
    r3 = st.sidebar.slider("年率③：後期 (%)", -15.0, 15.0, 1.0, 0.1, key="input_r3") / 100

st.sidebar.header("🚪 取り崩し設定（2段階）")
w_age_def = get_param("wa", 65)
w_start_age = st.sidebar.slider("取り崩し開始年齢", int(current_age), int(end_age), int(max(current_age, w_age_def)), key="input_wa")

with st.sidebar.expander("取り崩し額の設定"):
    wv1_def = get_param("wv1", 150000)
    w_val1 = st.number_input("初期の月額 (円)", 0, None, int(wv1_def), 5000, key="input_wv1")
    w_ch_age_def = get_param("wca", 75)
    w_change_age = st.slider("額を変える年齢", int(w_start_age), int(end_age), int(max(w_start_age, w_ch_age_def)), key="input_wca")
    wv2_def = get_param("wv2", 100000)
    w_val2 = st.number_input("変更後の月額 (円)", 0, None, int(wv2_def), 5000, key="input_wv2")

# --- 4. 計算ロジック ---
def run_simulation():
    balance = float(initial_sum)
    cum_inv = float(initial_sum)
    data = []
    total_months = (end_age - current_age) * 12
    
    for m in range(1, total_months + 1):
        m_age = current_age + (m-1)/12
        
        # 1. 利率の決定
        if is_simple:
            rate = fixed_rate
        else:
            rate = r1 if m_age < cr1 else r2 if m_age < cr2 else r3
            
        # 2. 収支の決定
        m_flow = 0.0
        act = "待機"
        if m_age >= w_start_age:
            act = "取り崩し"
            m_flow = -float(w_val1 if m_age < w_change_age else w_val2)
        else:
            act = "積立"
            m_flow = float(dep1 if m_age < dep_change_age else dep2)
            cum_inv += m_flow
            
        # 3. 残高更新（収支反映 → 利息）
        balance = max(0.0, balance + m_flow)
        balance *= (1 + rate / 12)
        
        data.append({
            "年齢(グラフ)": round(m_age + 1/12, 2),
            "年齢": int(m_age),
            "月": f"{(m-1)%12+1}ヶ月目",
            "区分": act,
            "月間収支": int(m_flow),
            "元本": int(cum_inv),
            "資産残高": int(balance)
        })
        if balance <= 0 and act == "取り崩し": break
    return pd.DataFrame(data)

# --- 5. 表示エリア ---
if initial_sum == 0 and dep1 == 0 and dep2 == 0:
    st.info("👈 左側のメニューから設定を入力してください。")
else:
    df = run_simulation()
    if not df.empty:
        f_bal = df.iloc[-1]['資産残高']
        f_age = df.iloc[-1]['年齢(グラフ)']
        
        c1, c2 = st.columns(2)
        with c1: st.metric(f"{end_age}歳時点の予想資産", f"¥{f_bal:,}")
        with c2:
            if f_bal <= 0: st.error(f"⚠️ {int(f_age)}歳で資産消滅")
            else: st.success("✅ 資産を維持できています")

        # グラフ作成
        df_g = df.copy()
        df_g["資産(万円)"] = df_g["資産残高"] / 10000
        df_g["元本(万円)"] = df_g["元本"] / 10000
        max_v = max(df_g["資産(万円)"].max(), df_g["元本(万円)"].max(), 10.0)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_g["年齢(グラフ)"], y=df_g["資産(万円)"], name="資産残高", line=dict(color="#1f77b4", width=3)))
        fig.add_trace(go.Scatter(x=df_g["年齢(グラフ)"], y=df_g["元本(万円)"], name="投資元本", line=dict(color="#ff7f0e", dash="dash")))
        
        fig.update_layout(
            margin=dict(l=10,r=10,t=10,b=10), height=400, hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            template="plotly_white"
        )
        grid_c, zero_c = "rgba(128, 128, 128, 0.3)", "gray"
        fig.update_xaxes(title="年齢 (歳)", range=[current_age-1, end_age+1], dtick=5, showgrid=True, gridcolor=grid_c, griddash='dot', zeroline=True, zerolinecolor=zero_c, zerolinewidth=2)
        fig.update_yaxes(title="金額 (万円)", range=[-max_v*0.05, max_v*1.15], ticksuffix="万", tickformat=",", showgrid=True, gridcolor=grid_c, griddash='dot', zeroline=True, zerolinecolor=zero_c, zerolinewidth=2)
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("📊 詳細データ"):
            st.dataframe(df[["年齢", "月", "区分", "月間収支", "元本", "資産残高"]], use_container_width=True, hide_index=True)
        st.download_button(label="📥 CSV保存", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="sim.csv", mime="text/csv")

# --- 6. URLパラメータ更新 ---
new_p = {"age": current_age, "end": end_age, "init": initial_sum, "d1": dep1, "cd": dep_change_age, "d2": dep2, "wa": w_start_age, "wv1": w_val1, "wca": w_change_age, "wv2": w_val2}
if is_simple: new_p["fr"] = fixed_rate * 100
st.query_params.update(**new_p)
