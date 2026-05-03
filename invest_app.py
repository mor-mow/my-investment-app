import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. ページ基本設定
st.set_page_config(page_title="資産シミュレーター", layout="centered")
st.markdown("### 📱 資産シミュレーター (自由段階版)")

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
            
            min_a = current_age if i == 0 else res_list[i-1]["age"]
            raw_v = get_p(f"{prefix}_v{i}", default_val)
            
            if is_rate or (is_withdrawal and row_mode == "定率 (%)"):
                f_val = float(raw_v)
                if f_val > 500: f_val = 4.0
                val = col1.number_input(f"値 {i+1}", -15.0, 100.0, f_val, 0.1, key=f"{prefix}_v{i}")
            else:
                i_val = int(raw_v) if float(raw_v) > 500 else int(default_val)
                val = col1.number_input(f"円 {i+1}", 0, None, i_val, 10000, key=f"{prefix}_v{i}")
            
            age = col2.number_input(f"開始年齢 {i+1}", min_a, end_age, int(min(max(min_a, get_p(f"{prefix}_a{i}", min_a)), end_age)), key=f"{prefix}_a{i}")
            res_list.append({"val": val, "age": age, "mode": row_mode})
        return res_list

deposits_list = dynamic_settings("💰 積立設定", "dep", 50000)
rates_list = dynamic_settings("📉 年率設定", "rate", 3.0, is_rate=True)
withdrawals_list = dynamic_settings("🚪 取り崩し設定", "wd", 150000, is_withdrawal=True)

with st.sidebar.expander("🏥 臨時収支の設定"):
    exp_c = int(st.number_input("収支の件数", 0, 5, int(get_p("exp_c", 0)), key="exp_c"))
    special_events = []
    for i in range(exp_c):
        col1, col2 = st.columns(2)
        v = int(col1.number_input(f"金額 {i+1}", value=int(get_p(f"ev{i}", 0)), step=100000, key=f"ev{i}"))
        a = int(col2.number_input(f"年齢 {i+1}", current_age, end_age, int(min(max(current_age, get_p(f"ea{i}", current_age)), end_age)), key=f"ea{i}"))
        if v != 0: special_events.append({"val": v, "age": a})

# --- 4. ワーニングチェックと平均年率計算 ---
active_dep_ages = [s["age"] for s in deposits_list if s["val"] > 0]
active_wd_ages = [s["age"] for s in withdrawals_list if s["val"] > 0]
first_wd_age = min(active_wd_ages) if active_wd_ages else 999

# 【修正】平均年率の計算ロジック
def calculate_true_avg_rate():
    total_y = end_age - current_age
    if total_y <= 0: return 0.0
    weighted_sum = 0
    for i, s in enumerate(rates_list):
        start = s["age"]
        # 次の設定年齢、もしくは終了年齢までを期間とする
        nxt = rates_list[i+1]["age"] if i+1 < len(rates_list) else end_age
        duration = max(0, nxt - start)
        weighted_sum += s["val"] * duration
    return weighted_sum / total_y

def run_simulation():
    current_bal = float(initial_sum)
    sim_genpon = float(initial_sum)
    log = []
    event_dict = {int((e["age"] - current_age) * 12 + 1): e["val"] for e in special_events}
    
    for m in range(1, (end_age - current_age) * 12 + 1):
        m_age = current_age + ((m - 1) / 12)
        
        def find_active(s_list, target_age):
            active = None
            for s in s_list:
                if target_age >= s["age"]: active = s
            return active

        curr_rate = find_active(rates_list, m_age)["val"]
        active_dep = find_active(deposits_list, m_age)
        active_wd = find_active(withdrawals_list, m_age)
        ev_val = float(event_dict.get(m, 0))
        current_bal += ev_val
        if ev_val > 0: sim_genpon += ev_val
        m_flow, action = 0.0, "待機"
        
        if m_age >= first_wd_age:
            if active_wd and active_wd["val"] > 0:
                if active_wd["mode"] == "定額 (円)": m_flow = -float(active_wd["val"])
                else: m_flow = -(current_bal * (active_wd["val"] / 100)) / 12
                action = "取り崩し"
        elif active_dep and m_age >= active_dep["age"] and active_dep["val"] > 0:
            m_flow = float(active_dep["val"])
            sim_genpon += m_flow
            action = "積立"
            
        current_bal = max(0.0, current_bal + m_flow)
        current_bal *= (1 + (curr_rate / 100) / 12)
        log.append({"年齢(グラフ)": round(m_age + 1/12, 2), "年齢": int(m_age), "月": f"{(m-1)%12+1}ヶ月目", "区分": action, "月間収支": int(m_flow), "臨時収支": int(ev_val), "元本": int(sim_genpon), "資産残高": int(current_bal)})
        if current_bal <= 0 and action == "取り崩し": break
    return pd.DataFrame(log)

# --- 5. 表示エリア ---
invalid_deposits = [a for a in active_dep_ages if first_wd_age <= a]
if invalid_deposits:
    st.warning(f"⚠️ **設定の矛盾**: 取り崩し開始（{first_wd_age}歳）以降の積立設定（{min(invalid_deposits)}歳〜）は無視されます。")

if initial_sum == 0 and not any(s["val"] > 0 for s in deposits_list):
    st.info("👈 左側のメニューから設定を入力してください。")
else:
    df = run_simulation()
    avg_r = calculate_true_avg_rate()
    
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric(f"{end_age}歳時点の予想資産", f"¥{df.iloc[-1]['資産残高']:,}")
        c2.metric("全体の平均年率", f"{avg_r:.2f}%")
        if df.iloc[-1]['資産残高'] <= 0: c3.error("⚠️ 資産消滅")
        else: c3.success("✅ 資産維持")
        
        df_g = df.copy()
        df_g["資産(万円)"], df_g["元本(万円)"] = df_g["資産残高"]/10000, df_g["元本"]/10000
        max_v = max(df_g["資産(万円)"].max(), df_g["元本(万円)"].max(), 10.0)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_g["年齢(グラフ)"], y=df_g["資産(万円)"], name="資産残高", line=dict(color="#1f77b4", width=3)))
        fig.add_trace(go.Scatter(x=df_g["年齢(グラフ)"], y=df_g["元本(万円)"], name="投資元本", line=dict(color="#ff7f0e", dash="dash")))
        fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=400, hovermode="x unified", legend=dict(orientation="h", y=1.1), template="plotly_white")
        grid_c, zero_c = "rgba(128, 128, 128, 0.3)", "gray"
        fig.update_xaxes(title="年齢", range=[current_age-1, end_age+1], dtick=5, showgrid=True, gridcolor=grid_c, griddash='dot', zeroline=True, zerolinecolor=zero_c, zerolinewidth=2)
        fig.update_yaxes(title="金額 (万円)", range=[-max_v*0.05, max_v*1.15], ticksuffix="万", tickformat=",", showgrid=True, gridcolor=grid_c, griddash='dot', zeroline=True, zerolinecolor=zero_c, zerolinewidth=2)
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("📊 詳細データ"):
            st.dataframe(df[["年齢", "月", "区分", "月間収支", "臨時収支", "元本", "資産残高"]], use_container_width=True, hide_index=True)
        st.download_button(label="📥 CSV保存", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="sim.csv", mime="text/csv")

# --- 6. URLクエリパラメータ更新 ---
st.query_params.update({k: v for k, v in st.session_state.items() if not str(k).startswith("FormSubmit")})
