import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. ページ基本設定
st.set_page_config(page_title="資産シミュレーター", layout="centered", page_icon="💰")
st.markdown("### 📱 資産シミュレーター")

# --- 2. 初期値取得ロジック ---
def get_p(key, default):
    if key in st.session_state:
        return st.session_state[key]
    params = st.query_params
    if key in params:
        val = params.get(key)
        try:
            if isinstance(default, float): return float(val)
            if isinstance(default, int): return int(float(val))
            return val
        except: return default
    return default

# --- 3. サイドバー設定エリア ---
st.sidebar.header("⚙️ 基本設定")
current_age = st.sidebar.number_input("現在の年齢", 0, 100, int(get_p("age", 30)), key="age")
end_age = st.sidebar.slider("終了年齢", current_age + 1, 100, int(max(current_age + 1, get_p("end", 85))), key="end")
initial_sum = int(st.sidebar.number_input("現在の一括投資額 (円)", 0, None, int(get_p("init", 1000000)), 100000, key="init"))

def dynamic_settings(label, prefix, default_val, is_rate=False, is_withdrawal=False):
    with st.sidebar.expander(label):
        count = int(st.number_input(f"{label}の段階数", 1, 5, int(get_p(f"{prefix}_c", 1)), key=f"{prefix}_c"))
        res_list = []
        for i in range(count):
            st.markdown(f"**第 {i+1} 段階**")
            col1, col2 = st.columns(2)
            row_mode = "定額 (円)"
            if is_withdrawal:
                row_mode = col1.selectbox(f"方法 {i+1}", ["定額 (円)", "定率 (%)"], 
                                         index=0 if str(get_p(f"{prefix}_m{i}", "定額 (円)")) == "定額 (円)" else 1, 
                                         key=f"{prefix}_m{i}")
            raw_v = get_p(f"{prefix}_v{i}", default_val)
            min_a = current_age if i == 0 else res_list[i-1]["age"]
            if is_rate or (is_withdrawal and row_mode == "定率 (%)"):
                val = col1.number_input(f"値 {i+1}", -15.0, 100.0, float(raw_v), 0.1, key=f"{prefix}_v{i}")
            else:
                val = col1.number_input(f"円 {i+1}", 0, None, int(raw_v), 10000, key=f"{prefix}_v{i}")
            age = col2.number_input(f"開始年齢 {i+1}", min_a, end_age, int(min(max(min_a, get_p(f"{prefix}_a{i}", min_a)), end_age)), key=f"{prefix}_a{i}")
            res_list.append({"val": val, "age": age, "mode": row_mode})
        return res_list

deposits_list = dynamic_settings("💰 積立設定", "dep", 50000)
rates_list = dynamic_settings("📉 年率設定", "rate", 3.0, is_rate=True)
withdrawals_list = dynamic_settings("🚪 取り崩し設定", "wd", 0, is_withdrawal=True)

with st.sidebar.expander("🏥 臨時収支の設定"):
    exp_c = int(st.number_input("収支の件数", 0, 5, int(get_p("exp_c", 0)), key="exp_c"))
    special_events = []
    for i in range(exp_c):
        st.markdown(f"**イベント {i+1}**")
        col1, col2 = st.columns(2)
        v = int(col1.number_input(f"金額 {i+1}", value=int(get_p(f"ev{i}", 0)), step=100000, key=f"ev{i}"))
        a = int(col2.number_input(f"年齢 {i+1}", current_age, end_age, int(min(max(current_age, get_p(f"ea{i}", current_age)), end_age)), key=f"ea{i}"))
        if v != 0: special_events.append({"val": v, "age": a})

# --- 4. 計算ロジック ---
def calculate_true_avg():
    total_y = end_age - current_age
    if total_y <= 0: return 0.0
    w_sum = 0
    for i, s in enumerate(rates_list):
        start = s["age"]
        nxt = rates_list[i+1]["age"] if i+1 < len(rates_list) else end_age
        w_sum += s["val"] * max(0, nxt - start)
    return w_sum / total_y

def run_simulation():
    curr_bal = float(initial_sum)
    sim_genpon = float(initial_sum)
    log = []
    total_months = (end_age - current_age) * 12
    event_dict = {int((e["age"] - current_age) * 12 + 1): e["val"] for e in special_events}
    
    w_active_starts = [s["age"] for s in withdrawals_list if s["val"] > 0]
    first_wd_age = min(w_active_starts) if w_active_starts else 999

    for m in range(1, total_months + 1):
        m_age = current_age + ((m - 1) / 12)
        def get_setting(s_list):
            active = s_list
            for s in s_list:
                if m_age >= s["age"]: active = s
            return active

        curr_rate = get_setting(rates_list)["val"]
        ev_val = float(event_dict.get(m, 0))
        curr_bal += ev_val
        if ev_val > 0: sim_genpon += ev_val

        m_flow, action = 0.0, "待機"
        if m_age >= first_wd_age:
            s_wd = get_setting(withdrawals_list)
            if s_wd["val"] > 0:
                m_flow = -float(s_wd["val"]) if s_wd["mode"] == "定額 (円)" else -(curr_bal * (s_wd["val"] / 100)) / 12
                action = "取り崩し"
        else:
            s_dep = get_setting(deposits_list)
            if m_age >= s_dep["age"]:
                m_flow = float(s_dep["val"])
                sim_genpon += m_flow
                action = "積立"
        
        curr_bal = max(0.0, curr_bal + m_flow)
        curr_bal *= (1 + (curr_rate / 100) / 12)
        
        log.append({
            "年齢_グラフ": round(m_age + 1/12, 2), 
            "年齢": int(m_age), 
            "月": f"{(m-1)%12+1}ヶ月目",
            "区分": action,
            "月間収支": int(m_flow),
            "臨時収支": int(ev_val),
            "資産(万円)": int(curr_bal / 10000), 
            "元本(万円)": int(sim_genpon / 10000)
        })
        if curr_bal <= 0 and action == "取り崩し": break
    return pd.DataFrame(log)

# --- 5. 表示エリア ---
df = run_simulation()
avg_r = calculate_true_avg()
is_empty = (initial_sum == 0 and not any(s["val"] > 0 for s in deposits_list) and not special_events)

if is_empty:
    st.info("👋 左メニューから「一括投資額」や「積立」を設定してください。")
else:
    if not df.empty:
        last_row = df.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric(f"{end_age}歳時点の資産", f"{int(last_row['資産(万円)']):,} 万円")
        c2.metric("全体の平均年率", f"{avg_r:.2f} %")
        c3.metric("投資元本合計", f"{int(last_row['元本(万円)']):,} 万円")
        
        if last_row['資産(万円)'] <= 0:
            st.warning("⚠️ 資産の見直しが必要かもしれません")
        else:
            st.success("✅ 資産を維持できる見通しです")

        # グラフ（x軸には小数点ありの「年齢_グラフ」を使用）
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["年齢_グラフ"], y=df["資産(万円)"], name="資産残高", line=dict(color="#1f77b4", width=3), fill='tozeroy', fillcolor='rgba(31, 119, 180, 0.1)'))
        fig.add_trace(go.Scatter(x=df["年齢_グラフ"], y=df["元本(万円)"], name="投資元本", line=dict(color="#ff7f0e", dash="dash")))
        fig.update_layout(hovermode="x unified", template="plotly_white", margin=dict(l=0, r=0, t=30, b=0),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                          yaxis=dict(ticksuffix="万", tickformat=",d", separatethousands=True))
        st.plotly_chart(fig, use_container_width=True)

        # 📊 詳細データ（年齢を「整数」にして表示）
        with st.expander("📊 詳細データを確認する"):
            st.dataframe(df[["年齢", "月", "区分", "月間収支", "臨時収支", "資産(万円)", "元本(万円)"]], 
                         use_container_width=True, hide_index=True)
        
        st.download_button(label="📥 CSV保存", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="asset_sim.csv", mime="text/csv")

# URL同期
st.query_params.update({k: v for k, v in st.session_state.items() if not str(k).startswith("FormSubmit")})
