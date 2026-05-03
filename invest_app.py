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

# 動的な段階設定用関数
def dynamic_settings(label, prefix, default_val, is_rate=False, is_withdrawal=False):
    with st.sidebar.expander(label):
        count = int(st.number_input(f"{label}の段階数", 1, 5, int(get_p(f"{prefix}_c", 1)), key=f"{prefix}_c"))
        res_list = []
        for i in range(count):
            st.markdown(f"**第 {i+1} 段階**")
            col1, col2 = st.columns(2)
            
            # 方法の選択（取り崩しのみ）
            row_mode = "定額"
            if is_withdrawal:
                row_mode = col1.selectbox(f"方法 {i+1}", ["定額 (円)", "定率 (%)"], 
                                         index=0 if str(get_p(f"{prefix}_m{i}", "定額 (円)")) == "定額 (円)" else 1, 
                                         key=f"{prefix}_m{i}")
            
            min_a = current_age if i == 0 else res_list[i-1]["age"]
            raw_v = get_p(f"{prefix}_v{i}", default_val)
            
            # 数値入力（利率 or 定率ならfloat, 定額ならint）
            if is_rate or (is_withdrawal and row_mode == "定率 (%)"):
                f_val = float(raw_v)
                if f_val > 100: f_val = 4.0 # 定額からの切替ガード
                val = col1.number_input(f"値 {i+1}", -15.0, 100.0, f_val, 0.1, key=f"{prefix}_v{i}")
            else:
                i_val = int(raw_v) if float(raw_v) > 100 else int(default_val)
                val = col1.number_input(f"円 {i+1}", 0, None, i_val, 10000, key=f"{prefix}_v{i}")
            
            # 年齢設定
            age = col2.number_input(f"開始年齢 {i+1}", min_a, end_age, int(min(max(min_a, get_p(f"{prefix}_a{i}", min_a)), end_age)), key=f"{prefix}_a{i}")
            
            res_list.append({"val": val, "age": age, "mode": row_mode})
        return res_list

deposits = dynamic_settings("💰 積立設定", "dep", 50000)
rates = dynamic_settings("📉 年率設定", "rate", 3.0, is_rate=True)
withdrawals = dynamic_settings("🚪 取り崩し設定", "wd", 150000, is_withdrawal=True)

# --- 4. 計算ロジック ---
def run_simulation():
    current_bal = float(initial_sum)
    sim_元本 = float(initial_sum)
    log = []
    total_months = (end_age - current_age) * 12
    
    # 取り崩しが実際に始まる最小年齢
    w_active_ages = [s["age"] for s in withdrawals if s["val"] > 0]
    w_start_threshold = min(w_active_ages) if w_active_ages else 999

    for m in range(1, total_months + 1):
        m_age = current_age + ((m - 1) / 12)
        
        # 現在適用すべき設定を抽出
        def find_s(s_list, target_age):
            active = s_list[0]
            for s in s_list:
                if target_age >= s["age"]: active = s
            return active

        curr_rate = find_s(rates, m_age)["val"]
        
        m_flow, action = 0.0, "待機"
        
        if m_age >= w_start_threshold:
            # 取り崩し期
            s_w = find_s(withdrawals, m_age)
            if s_w["mode"] == "定額 (円)":
                m_flow = -float(s_w["val"])
            else:
                m_flow = -(current_bal * (s_w["val"] / 100)) / 12
            action = "取り崩し"
        else:
            # 積立期
            s_d = find_s(deposits, m_age)
            if m_age >= s_d["age"]:
                m_flow = float(s_d["val"])
                sim_元本 += m_flow
                action = "積立"
        
        # 残高更新（収支を反映してから利息）
        current_bal = max(0.0, current_bal + m_flow)
        current_bal *= (1 + (curr_rate / 100) / 12)
        
        log.append({
            "年齢(グラフ)": round(m_age + 1/12, 2), "年齢": int(m_age), "月": f"{(m-1)%12+1}ヶ月目",
            "区分": action, "月間収支": int(m_flow), "元本": int(sim_元本), "資産残高": int(current_bal)
        })
        if current_bal <= 0 and action == "取り崩し": break
    return pd.DataFrame(log)

# --- 5. 表示エリア ---
if initial_sum == 0 and all(s["val"] == 0 for s in deposits):
    st.info("👈 左側のメニューから数値を入力してください。")
else:
    df = run_simulation()
    if not df.empty:
        st.metric(f"{end_age}歳時点の予想資産", f"¥{df.iloc[-1]['資産残高']:,}")
        
        # グラフ
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
        gc, zc = "rgba(128,128,128,0.3)", "gray"
        fig.update_xaxes(title="年齢", range=[current_age-1, end_age+1], dtick=5, showgrid=True, gridcolor=gc, griddash='dot', zeroline=True, zerolinecolor=zc, zerolinewidth=2)
        fig.update_yaxes(title="万円", range=[-max_v*0.05, max_v*1.15], ticksuffix="万", tickformat=",", showgrid=True, gridcolor=gc, griddash='dot', zeroline=True, zerolinecolor=zc, zerolinewidth=2)
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("📊 詳細データ"):
            st.dataframe(df[["年齢", "月", "区分", "月間収支", "元本", "資産残高"]], use_container_width=True, hide_index=True)
        st.download_button(label="📥 CSV保存", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="sim.csv", mime="text/csv")

# --- 6. URLクエリパラメータ更新 ---
st.query_params.update({k: v for k, v in st.session_state.items() if not str(k).startswith("FormSubmit")})
