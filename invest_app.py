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
end_age_raw = int(get_p("end", 85))
end_age = int(st.sidebar.slider("終了年齢", current_age, 100, int(max(current_age, end_age_raw)), key="end"))
initial_sum = int(st.sidebar.number_input("現在の一括投資額 (円)", 0, None, int(get_p("init", 0)), 100000, key="init"))

# 動的な段階設定用関数
def dynamic_settings(label, prefix, default_val, is_rate=False, is_withdrawal=False):
    with st.sidebar.expander(label):
        count = int(st.number_input(f"{label}の段階数", 1, 5, int(get_p(f"{prefix}_c", 1)), key=f"{prefix}_c"))
        settings = []
        for i in range(count):
            st.markdown(f"**第 {i+1} 段階**")
            col1, col2 = st.columns(2)
            
            # 取り崩しの場合のみ、各段階で方法を選択
            row_mode = "定額 (円)"
            if is_withdrawal:
                row_mode = col1.selectbox(f"計算方法 {i+1}", ["定額 (円)", "定率 (%)"], 
                                         index=0 if get_p(f"{prefix}_m{i}", "定額 (円)") == "定額 (円)" else 1, 
                                         key=f"{prefix}_m{i}")
            
            min_age = current_age if i == 0 else settings[i-1]["age"]
            
            # 値の入力（定率か年率ならfloat、定額ならint）
            if is_rate or (is_withdrawal and row_mode == "定率 (%)"):
                val = float(col1.number_input(f"値", -15.0, 30.0, float(get_p(f"{prefix}_v{i}", default_val)), step=0.1, key=f"{prefix}_v{i}"))
            else:
                val = int(col1.number_input(f"円", 0, None, int(get_p(f"{prefix}_v{i}", int(default_val))), step=10000, key=f"{prefix}_v{i}"))
            
            # 年齢のガード
            saved_age = int(get_p(f"{prefix}_a{i}", min_age))
            safe_age = int(min(max(min_age, saved_age), end_age))
            age = int(col2.number_input(f"開始年齢", min_age, end_age, safe_age, key=f"{prefix}_a{i}"))
            
            settings.append({"val": val, "age": age, "mode": row_mode})
        return settings

# 各セクションの設定
deposits = dynamic_settings("💰 積立設定", "dep", 50000)
rates = dynamic_settings("📉 年率設定", "rate", 3.0, is_rate=True)
withdrawals = dynamic_settings("🚪 取り崩し設定", "wd", 0, is_withdrawal=True)

with st.sidebar.expander("🏥 臨時収支の設定"):
    exp_count = int(st.number_input("件数", 0, 5, int(get_p("exp_c", 0)), key="exp_c"))
    special_events = []
    for i in range(exp_count):
        col1, col2 = st.columns(2)
        v = int(col1.number_input(f"金額 {i+1}", value=int(get_p(f"ev{i}", 0)), step=100000, key=f"ev{i}"))
        saved_ea = int(get_p(f"ea{i}", current_age))
        safe_ea = int(min(max(current_age, saved_ea), end_age))
        a = int(col2.number_input(f"年齢 {i+1}", current_age, end_age, safe_ea, key=f"ea{i}"))
        if v != 0: special_events.append({"val": v, "age": a})

# --- 4. 計算ロジック ---
def run_simulation():
    balance = float(initial_sum)
    cum_inv = float(initial_sum)
    data = []
    total_months = (end_age - current_age) * 12
    event_dict = {int((e["age"] - current_age) * 12 + 1): e["val"] for e in special_events}
    
    for m in range(1, total_months + 1):
        p_age = current_age + (m / 12)
        display_age = int(p_age - 0.00001)
        
        def find_active_setting(s_list, target_age):
            active = s_list[0]
            for s in s_list:
                if target_age >= s["age"]: active = s
            return active

        curr_rate = find_active_setting(rates, p_age)["val"]
        ev_val = float(event_dict.get(m, 0))
        balance += ev_val
        if ev_val > 0: cum_inv += ev_val

        # 取り崩し・積立の判定
        active_w = find_active_setting(withdrawals, p_age)
        active_d = find_active_setting(deposits, p_age)
        
        # 実際に「取り崩し」が始まっているか（設定年齢に達し、かつ値が0でない）
        is_w_started = any(s["val"] > 0 and p_age >= s["age"] for s in withdrawals)
        
        m_flow, action = 0.0, "待機"
        if is_w_started:
            if active_w["mode"] == "定額 (円)":
                m_flow = -float(active_w["val"])
            else:
                m_flow = -(balance * (float(active_w["val"]) / 100)) / 12
            action = "取り崩し"
        elif p_age >= deposits[0]["age"] and active_d["val"] > 0:
            m_flow = float(active_d["val"])
            cum_inv += m_flow
            action = "積立"
            
        balance = max(0.0, balance + m_flow) * (1 + (float(curr_rate)/100) / 12)
        data.append({"年齢(グラフ)": round(p_age, 2), "年齢": display_age, "月": f"{(m-1)%12+1}ヶ月目", "区分": action, "月間収支": int(m_flow), "臨時収支": int(ev_val), "元本": int(cum_inv), "資産残高": int(balance)})
        if balance <= 0 and action == "取り崩し": break
    return pd.DataFrame(data)

# --- 5. 表示エリア ---
has_input = (initial_sum > 0 or any(s["val"] > 0 for s in deposits))
if not has_input:
    st.info("👈 左側のメニューから設定を入力してください。")
else:
    df = run_simulation()
    if not df.empty:
        f_bal = df.iloc[-1]['資産残高']
        c1, c2 = st.columns(2)
        with c1: st.metric(f"{end_age}歳時点の予想資産", f"¥{f_bal:,}")
        with c2:
            if f_bal <= 0: st.error(f"⚠️ {int(df.iloc[-1]['年齢(グラフ)'])}歳で資産消滅")
            else: st.success("✅ 資産を維持できています")

        # グラフ作成
        df_g = df.copy()
        df_g["資産(万円)"] = df_g["資産残高"] / 10000
        df_g["元本(万円)"] = df_g["元本"] / 10000
        max_v = max(df_g["資産(万円)"].max(), df_g["元本(万円)"].max())
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_g["年齢(グラフ)"], y=df_g["資産(万円)"], name="資産残高", line=dict(color="#1f77b4", width=3)))
        fig.add_trace(go.Scatter(x=df_g["年齢(グラフ)"], y=df_g["元本(万円)"], name="投資元本", line=dict(color="#ff7f0e", width=2, dash="dash")))
        fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=400, hovermode="x unified", legend=dict(orientation="h", y=1.1), template="plotly_white")
        gc, zc = "rgba(128,128,128,0.3)", "gray"
        fig.update_xaxes(title="年齢", range=[current_age-1, end_age+1], dtick=5, showgrid=True, gridcolor=gc, griddash='dot', zeroline=True, zerolinecolor=zc, zerolinewidth=2)
        fig.update_yaxes(title="金額 (万円)", range=[-max_v*0.05, max_v*1.15], ticksuffix="万", tickformat=",", showgrid=True, gridcolor=gc, griddash='dot', zeroline=True, zerolinecolor=zc, zerolinewidth=2)
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("📊 詳細データ"):
            st.dataframe(df[["年齢", "月", "区分", "月間収支", "臨時収支", "元本", "資産残高"]], use_container_width=True, hide_index=True)
        st.download_button(label="📥 CSV保存", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="sim_result.csv", mime="text/csv")

# --- 6. URLクエリパラメータ更新 ---
st.query_params.update({k: v for k, v in st.session_state.items() if not str(k).startswith("FormSubmit")})
