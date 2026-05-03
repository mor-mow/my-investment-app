import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. ページ基本設定
st.set_page_config(page_title="資産シミュレーター", layout="centered")
st.markdown("### 📱 資産シミュレーター (自由設定版)")

# --- 2. URLから初期値を安全に取得する関数 ---
def get_p(key, default):
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
current_age = int(st.sidebar.number_input("現在の年齢", 0, 100, int(get_p("age", 30)), key="age"))
end_age = int(st.sidebar.slider("終了年齢", current_age, 100, int(max(current_age, get_p("end", 85))), key="end"))
initial_sum = int(st.sidebar.number_input("現在の一括投資額 (円)", 0, None, int(get_p("init", 0)), 100000, key="init"))

# 動的な段階設定用関数
def dynamic_settings(label, prefix, default_val, is_rate=False, is_withdrawal=False):
    with st.sidebar.expander(label):
        count = int(st.number_input(f"{label}の段階数", 1, 5, int(get_p(f"{prefix}_c", 1)), key=f"{prefix}_c"))
        res_list = []
        for i in range(count):
            st.markdown(f"**第 {i+1} 段階**")
            col1, col2 = st.columns(2)
            row_mode = "定額 (円)"
            if is_withdrawal:
                row_mode = col1.selectbox(f"方法 {i+1}", ["定額 (円)", "定率 (%)"], index=0 if str(get_p(f"{prefix}_m{i}", "定額 (円)")) == "定額 (円)" else 1, key=f"{prefix}_m{i}")
            min_a = current_age if i == 0 else res_list[i-1]["age"]
            raw_val = get_p(f"{prefix}_v{i}", default_val)
            if is_rate or (is_withdrawal and row_mode == "定率 (%)"):
                val = float(col1.number_input(f"値 {i+1}", -15.0, 100.0, float(raw_val) if float(raw_val) < 100 else 4.0, step=0.1, key=f"{prefix}_v{i}"))
            else:
                val = int(col1.number_input(f"円 {i+1}", 0, None, int(raw_val) if float(raw_val) > 100 else int(default_val), step=10000, key=f"{prefix}_v{i}"))
            age = int(col2.number_input(f"開始年齢 {i+1}", min_a, end_age, int(min(max(min_a, get_p(f"{prefix}_a{i}", min_a)), end_age)), key=f"{prefix}_a{i}"))
            res_list.append({"val": val, "age": age, "mode": row_mode})
        return res_list

deposits_list = dynamic_settings("💰 積立設定", "dep", 50000)
rates_list = dynamic_settings("📉 年率設定", "rate", 3.0, is_rate=True)
withdrawals_list = dynamic_settings("🚪 取り崩し設定", "wd", 150000, is_withdrawal=True)

with st.sidebar.expander("🏥 臨時収支の設定"):
    exp_c = int(st.number_input("件数", 0, 5, int(get_p("exp_c", 0)), key="exp_c"))
    special_events = []
    for i in range(exp_c):
        col1, col2 = st.columns(2)
        v = int(col1.number_input(f"金額 {i+1}", value=int(get_p(f"ev{i}", 0)), step=100000, key=f"ev{i}"))
        a = int(col2.number_input(f"年齢 {i+1}", current_age, end_age, int(min(max(current_age, get_p(f"ea{i}", current_age)), end_age)), key=f"ea{i}"))
        if v != 0: special_events.append({"val": v, "age": a})

# --- 4. 計算ロジック (バグ完全修正版) ---
def run_simulation():
    # 計算用のローカル変数をしっかり分ける
    sim_balance = float(initial_sum)
    sim_cum_inv = float(initial_sum)
    log = []
    event_map = {int((e["age"] - current_age) * 12 + 1): e["val"] for e in special_events}
    
    # 取り崩しが「有効」になる最小年齢
    w_start_ages = [s["age"] for s in withdrawals_list if s["val"] > 0]
    min_w_age = min(w_start_ages) if w_start_ages else 999

    for m in range(1, (end_age - current_age) * 12 + 1):
        m_age = current_age + ((m - 1) / 12)
        
        def get_s(s_list, target_age):
            active = s_list if s_list else None
            for s in s_list:
                if target_age >= s["age"]: active = s
            return active

        # 1. 臨時収支
        ev = float(event_map.get(m, 0))
        sim_balance += ev
        if ev > 0: sim_cum_inv += ev

        # 2. 収支(積立 or 取り崩し)の判定
        m_flow = 0.0
        act = "待機"
        
        if m_age >= min_w_age: # 取り崩しフェーズ
            s_w = get_s(withdrawals_list, m_age)
            if s_w:
                m_flow = -float(s_w["val"]) if s_w["mode"] == "定額 (円)" else -(sim_balance * (s_w["val"]/100))/12
                act = "取り崩し"
        else: # 積立フェーズ
            s_d = get_s(deposits_list, m_age)
            if s_d and m_age >= s_d["age"]:
                m_flow = float(s_d["val"])
                sim_cum_inv += m_flow
                act = "積立"

        # 3. 残高の更新 (収支を反映してから利息)
        sim_balance = max(0.0, sim_balance + m_flow)
        rate = get_s(rates_list, m_age)["val"]
        sim_balance *= (1 + (rate / 100) / 12)

        log.append({"年齢(グラフ)": round(m_age + 1/12, 2), "年齢": int(m_age), "月": f"{(m-1)%12+1}ヶ月目", "区分": act, "月間収支": int(m_flow), "元本": int(sim_cum_inv), "資産残高": int(sim_balance)})
        if sim_balance <= 0 and act == "取り崩し": break
    return pd.DataFrame(log)

# --- 5. 表示エリア ---
if initial_sum == 0 and not any(s["val"] > 0 for s in deposits_list):
    st.info("👈 左側のメニューから設定を入力してください。")
else:
    df = run_simulation()
    if not df.empty:
        st.metric(f"{end_age}歳時点の資産", f"¥{df.iloc[-1]['資産残高']:,}")
        max_v = max(df["資産残高"].max(), df["元本"].max()) / 10000
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["年齢(グラフ)"], y=df["資産残高"]/10000, name="資産残高", line=dict(color="#1f77b4", width=3)))
        fig.add_trace(go.Scatter(x=df["年齢(グラフ)"], y=df["元本"]/10000, name="投資元本", line=dict(color="#ff7f0e", width=2, dash="dash")))
        fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=400, hovermode="x unified", legend=dict(orientation="h", y=1.1), template="plotly_white")
        grid_c, zero_c = "rgba(128, 128, 128, 0.3)", "gray"
        fig.update_xaxes(title="年齢", range=[current_age-1, end_age+1], dtick=5, showgrid=True, gridcolor=grid_c, griddash='dot', zeroline=True, zerolinecolor=zero_c, zerolinewidth=2)
        fig.update_yaxes(title="金額 (万円)", range=[-max_v*0.05, max_v*1.15], ticksuffix="万", tickformat=",", showgrid=True, gridcolor=grid_c, griddash='dot', zeroline=True, zerolinecolor=zero_c, zerolinewidth=2)
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("📊 詳細データ"):
            st.dataframe(df[["年齢", "月", "区分", "月間収支", "元本", "資産残高"]], use_container_width=True, hide_index=True)
        st.download_button(label="📥 CSV保存", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="sim.csv", mime="text/csv")

# --- 6. URLクエリパラメータ更新 ---
st.query_params.update({k: v for k, v in st.session_state.items() if not str(k).startswith("FormSubmit")})
