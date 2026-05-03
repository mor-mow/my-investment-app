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
end_p = get_p("end", 85)
end_age = int(st.sidebar.slider("終了年齢", current_age, 100, int(max(current_age, end_p)), key="end"))
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
                row_mode = col1.selectbox(f"方法 {i+1}", ["定額 (円)", "定率 (%)"], 
                                         index=0 if str(get_p(f"{prefix}_m{i}", "定額 (円)")) == "定額 (円)" else 1, 
                                         key=f"{prefix}_m{i}")
            
            min_a = current_age if i == 0 else res_list[i-1]["age"]
            raw_val = get_p(f"{prefix}_v{i}", default_val)
            
            if is_rate or (is_withdrawal and row_mode == "定率 (%)"):
                f_val = float(raw_val)
                if f_val > 100: f_val = 4.0
                val = float(col1.number_input(f"値 {i+1}", -15.0, 100.0, f_val, step=0.1, key=f"{prefix}_v{i}"))
            else:
                i_val = int(raw_val) if float(raw_val) > 100 else int(default_val)
                val = int(col1.number_input(f"円 {i+1}", 0, None, i_val, step=10000, key=f"{prefix}_v{i}"))
            
            saved_a = int(get_p(f"{prefix}_a{i}", min_a))
            safe_a = int(min(max(min_a, saved_a), end_age))
            age = int(col2.number_input(f"開始年齢 {i+1}", min_a, end_age, safe_a, key=f"{prefix}_a{i}"))
            
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
        saved_ea = int(get_p(f"ea{i}", current_age))
        safe_ea = int(min(max(current_age, saved_ea), end_age))
        a = int(col2.number_input(f"年齢 {i+1}", current_age, end_age, safe_ea, key=f"ea{i}"))
        if v != 0: special_events.append({"val": v, "age": a})

# --- 4. 計算ロジック (徹底修正) ---
def run_simulation():
    # 計算用変数を初期化
    current_balance = float(initial_sum)
    cumulative_invested = float(initial_sum)
    data_log = []
    total_months = (end_age - current_age) * 12
    
    # 臨時イベントを月単位の辞書に変換
    event_map = {int((e["age"] - current_age) * 12 + 1): e["val"] for e in special_events}
    
    # 取り崩しが開始される最小の年齢を特定
    valid_withdrawal_starts = [s["age"] for s in withdrawals_list if s["val"] > 0]
    w_start_threshold = min(valid_withdrawal_starts) if valid_withdrawal_starts else 999

    for m in range(1, total_months + 1):
        month_age = current_age + ((m - 1) / 12)
        display_age_int = int(month_age)
        
        # 1. 適用する設定（利率、積立、取り崩し）を決定
        def get_setting(s_list, target_age):
            active = s_list[0] if s_list else None
            for s in s_list:
                if target_age >= s["age"]: active = s
            return active

        s_rate = get_setting(rates_list, month_age)
        annual_rate = s_rate["val"] if s_rate else 0.0
        
        # 2. 臨時収支の反映
        monthly_event_val = float(event_map.get(m, 0))
        current_balance += monthly_event_val
        if monthly_event_val > 0:
            cumulative_invested += monthly_event_val

        # 3. 積立 or 取り崩しの計算
        m_cashflow = 0.0
        current_action = "待機"
        
        # 取り崩しフェーズの判定
        if month_age >= w_start_threshold:
            s_w = get_setting(withdrawals_list, month_age)
            if s_w and s_w["val"] > 0:
                if s_w["mode"] == "定額 (円)":
                    m_cashflow = -float(s_w["val"])
                else:
                    # 定率取り崩し (残高 × 率 / 12)
                    m_cashflow = -(current_balance * (float(s_w["val"]) / 100)) / 12
                current_action = "取り崩し"
        else:
            # 積立フェーズ
            s_d = get_setting(deposits_list, month_age)
            if s_d and s_d["val"] > 0 and month_age >= s_d["age"]:
                m_cashflow = float(s_d["val"])
                cumulative_invested += m_cashflow
                current_action = "積立"
        
        # 4. 残高に収支を反映し、利息計算
        current_balance = max(0.0, current_balance + m_cashflow)
        if current_balance > 0:
            # 利息を付与
            current_balance *= (1 + (annual_rate / 100) / 12)
        
        # 5. ログに追加
        data_log.append({
            "年齢(グラフ)": round(month_age + 1/12, 2),
            "年齢": display_age_int,
            "月": f"{(m-1)%12+1}ヶ月目",
            "区分": current_action,
            "月間収支": int(m_cashflow),
            "臨時収支": int(monthly_event_val),
            "元本合計": int(cumulative_invested),
            "資産残高": int(current_balance)
        })
        
        # 資産が尽きたら終了
        if current_balance <= 0 and current_action == "取り崩し":
            break
            
    return pd.DataFrame(data_log)

# --- 5. 表示エリア ---
has_input_data = (initial_sum > 0 or any(s["val"] > 0 for s in deposits_list))
if not has_input_data:
    st.info("👈 左側のメニューから数値を入力してください。")
else:
    sim_df = run_simulation()
    if not sim_df.empty:
        final_balance_val = sim_df.iloc[-1]['資産残高']
        c1, c2 = st.columns(2)
        with c1: st.metric(f"{end_age}歳時点の予想資産", f"¥{final_balance_val:,}")
        with c2:
            if final_balance_val <= 0: st.error(f"⚠️ {int(sim_df.iloc[-1]['年齢(グラフ)'])}歳で資産消滅")
            else: st.success("✅ 資産を維持できています")

        # グラフ描画
        graph_df = sim_df.copy()
        graph_df["資産(万円)"] = graph_df["資産残高"] / 10000
        graph_df["元本(万円)"] = graph_df["元本合計"] / 10000
        y_max = max(graph_df["資産(万円)"].max(), graph_df["元本(万円)"].max(), 10.0)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=graph_df["年齢(グラフ)"], y=graph_df["資産(万円)"], name="資産残高", line=dict(color="#1f77b4", width=3)))
        fig.add_trace(go.Scatter(x=graph_df["年齢(グラフ)"], y=graph_df["元本(万円)"], name="投資元本", line=dict(color="#ff7f0e", width=2, dash="dash")))
        fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=400, hovermode="x unified", legend=dict(orientation="h", y=1.1), template="plotly_white")
        grid_c, zero_c = "rgba(128, 128, 128, 0.3)", "gray"
        fig.update_xaxes(title="年齢", range=[current_age-1, end_age+1], dtick=5, showgrid=True, gridcolor=grid_c, griddash='dot', zeroline=True, zerolinecolor=zero_c, zerolinewidth=2)
        fig.update_yaxes(title="金額 (万円)", range=[-y_max*0.05, y_max*1.15], ticksuffix="万", tickformat=",", showgrid=True, gridcolor=grid_c, griddash='dot', zeroline=True, zerolinecolor=zero_c, zerolinewidth=2)
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("📊 月ごとの詳細データ"):
            st.dataframe(sim_df[["年齢", "月", "区分", "月間収支", "臨時収支", "元本合計", "資産残高"]], use_container_width=True, hide_index=True)
        st.download_button(label="📥 CSV保存", data=sim_df.to_csv(index=False).encode('utf-8-sig'), file_name="sim_result.csv", mime="text/csv")

# --- 6. URLクエリパラメータ更新 ---
st.query_params.update({k: v for k, v in st.session_state.items() if not str(k).startswith("FormSubmit")})
