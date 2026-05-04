import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. ページ基本設定
st.set_page_config(page_title="資産シミュレーター", layout="centered", page_icon="💰")
st.markdown("### 📱 資産シミュレーター")

# --- 2. 初期値取得ロジック（最新の画面入力を優先） ---
def get_p(key, default):
    # すでにセッション(画面上の入力)にある場合はそれを優先
    if key in st.session_state:
        return st.session_state[key]
    
    # セッションになければURLから取得
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

# keyを明示的に指定し、初期値取得関数を噛ませる
current_age = st.sidebar.number_input("現在の年齢", 0, 100, int(get_p("age", 30)), key="age")
end_age = st.sidebar.slider("終了年齢", current_age + 1, 100, int(max(current_age + 1, get_p("end", 85))), key="end")
# ここの計算ズレを防ぐため float で確実に処理
initial_sum_raw = st.sidebar.number_input("現在の一括投資額 (円)", 0, None, int(get_p("init", 0)), 100000, key="init")
initial_sum = float(initial_sum_raw)

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
                val = col1.number_input(f"値 {i+1}", -15.0, 100.0, float(raw_v), 0.1, key=f"{prefix}_v{i}")
            else:
                val = col1.number_input(f"円 {i+1}", 0, None, int(raw_v), 10000, key=f"{prefix}_v{i}")
            
            age = col2.number_input(f"開始年齢 {i+1}", min_a, end_age, int(min(max(min_a, get_p(f"{prefix}_a{i}", min_a)), end_age)), key=f"{prefix}_a{i}")
            res_list.append({"val": val, "age": age, "mode": row_mode})
        return res_list

deposits_list = dynamic_settings("💰 積立設定", "dep", 50000)
rates_list = dynamic_settings("📉 年率設定", "rate", 3.0, is_rate=True)
withdrawals_list = dynamic_settings("🚪 取り崩し設定", "wd", 0, is_withdrawal=True)

# --- 4. 計算ロジック (ここがズレの核心) ---
def run_simulation():
    # 画面上の最新値を直接使う
    curr_bal = float(initial_sum)
    sim_genpon = float(initial_sum)
    
    log = []
    total_months = (end_age - current_age) * 12
    
    # 臨時収支
    special_events = []
    if "exp_c" in st.session_state:
        for i in range(int(st.session_state.exp_c)):
            v = st.session_state.get(f"ev{i}", 0)
            a = st.session_state.get(f"ea{i}", current_age)
            if v != 0: special_events.append({"val": v, "age": a})
    
    event_dict = {int((e["age"] - current_age) * 12 + 1): e["val"] for e in special_events}
    
    w_active_starts = [s["age"] for s in withdrawals_list if s["val"] > 0]
    first_wd_age = min(w_active_starts) if w_active_starts else 999

    for m in range(1, total_months + 1):
        m_age = current_age + ((m - 1) / 12)
        
        def get_active_setting(s_list):
            active = s_list[0]
            for s in s_list:
                if m_age >= s["age"]: active = s
            return active

        curr_rate = get_active_setting(rates_list)["val"]
        
        # 臨時収支の加算
        ev_val = float(event_dict.get(m, 0))
        curr_bal += ev_val
        if ev_val > 0: sim_genpon += ev_val

        m_flow, action = 0.0, "待機"
        if m_age >= first_wd_age:
            s_wd = get_active_setting(withdrawals_list)
            if s_wd["val"] > 0:
                m_flow = -float(s_wd["val"]) if s_wd["mode"] == "定額 (円)" else -(curr_bal * (s_wd["val"] / 100)) / 12
                action = "取り崩し"
        else:
            s_dep = get_active_setting(deposits_list)
            if m_age >= s_dep["age"]:
                m_flow = float(s_dep["val"])
                sim_genpon += m_flow
                action = "積立"
        
        # 残高更新
        curr_bal = max(0.0, curr_bal + m_flow)
        curr_bal *= (1 + (curr_rate / 100) / 12)
        
        log.append({
            "年齢(グラフ)": round(m_age + 1/12, 2), "年齢": int(m_age), 
            "資産残高": int(curr_bal), "元本": int(sim_genpon)
        })
        if curr_bal <= 0 and action == "取り崩し": break
    return pd.DataFrame(log)

# --- 5. 描画と表示 ---
df = run_simulation()

is_input_empty = (initial_sum == 0 and not any(s["val"] > 0 for s in deposits_list))

if is_input_empty:
    st.info("👋 左メニューから「一括投資額」や「積立」を入力してください。")
else:
    if not df.empty:
        last_row = df.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric(f"{end_age}歳時点の資産", f"¥{last_row['資産残高']:,}")
        c2.metric("投資元本合計", f"¥{int(last_row['元本']):,}")
        
        if last_row['資産残高'] <= 0:
            c3.warning("⚠️ 途中で見直しが必要")
        else:
            c3.success("✅ 順調なプラン")

        # グラフ表示
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["年齢(グラフ)"], y=df["資産残高"], name="資産残高", line=dict(color="#1f77b4", width=3), fill='tozeroy', fillcolor='rgba(31, 119, 180, 0.1)'))
        fig.add_trace(go.Scatter(x=df["年齢(グラフ)"], y=df["元本"], name="投資元本", line=dict(color="#ff7f0e", dash="dash")))
        fig.update_layout(height=400, hovermode="x unified", template="plotly_white", margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig, use_container_width=True)

# --- 6. URL同期（不具合防止のため最後にまとめて更新） ---
# セッション状態をURLに反映
new_params = {k: v for k, v in st.session_state.items() if not str(k).startswith("FormSubmit")}
st.query_params.update(new_params)
