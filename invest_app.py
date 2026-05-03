import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. ページ基本設定
st.set_page_config(page_title="資産シミュレーター", layout="centered")
st.markdown("### 📱 資産シミュレーター (自由設定版)")

# --- 2. URLから初期値を取得する関数 ---
def get_p(key, default):
    params = st.query_params
    if key in params:
        val = params.get(key)
        try: return float(val) if "." in val else int(val)
        except: return val
    return default

# --- 3. サイドバー設定エリア ---
st.sidebar.header("⚙️ 基本設定")
current_age = st.sidebar.number_input("現在の年齢", 0, 100, int(get_p("age", 30)), key="age")
end_age = st.sidebar.slider("終了年齢", current_age, 100, int(max(current_age, get_p("end", 85))), key="end")
initial_sum = st.sidebar.number_input("現在の一括投資額 (円)", 0, None, int(get_p("init", 0)), 100000, key="init")

# 動的な設定値を管理するための関数
def dynamic_settings(label, prefix, default_val, is_rate=False):
    with st.sidebar.expander(label):
        count = st.number_input(f"{label}の段階数", 1, 5, int(get_p(f"{prefix}_c", 1)), key=f"{prefix}_c")
        settings = []
        for i in range(count):
            col1, col2 = st.columns(2)
            val = col1.number_input(f"値 {i+1}", -15.0 if is_rate else 0, None, 
                                   get_p(f"{prefix}_v{i}", default_val), 
                                   step=0.1 if is_rate else 5000, key=f"{prefix}_v{i}")
            if i == 0:
                age = current_age
                col2.text_input(f"開始年齢", f"{age}歳", disabled=True, key=f"{prefix}_a{i}_d")
            else:
                prev_age = settings[i-1]["age"]
                age = col2.number_input(f"切替年齢 {i+1}", int(prev_age), int(end_age), 
                                       int(max(prev_age, get_p(f"{prefix}_a{i}", prev_age+10))), key=f"{prefix}_a{i}")
            settings.append({"val": val, "age": age})
        return settings

# 各セクションの設定取得
deposits = dynamic_settings("💰 積立設定", "dep", 50000)
rates = dynamic_settings("📉 年率設定", "rate", 3.0, is_rate=True)
withdrawals_start_age = st.sidebar.slider("取り崩し開始年齢", current_age, end_age, int(max(current_age, get_p("wa", 65))), key="wa")
withdrawals = dynamic_settings("🚪 取り崩し額設定", "wd", 100000)

# --- 臨時出費の設定 (ここを5段階対応に拡張) ---
with st.sidebar.expander("🏥 臨時出費の設定"):
    exp_count = st.number_input("出費の件数", 0, 5, int(get_p("exp_c", 0)), key="exp_c")
    special_expenses = []
    for i in range(exp_count):
        c1, c2 = st.columns(2)
        v = c1.number_input(f"出費{i+1}：額(円)", 0, None, int(get_p(f"ev{i}", 0)), 100000, key=f"ev{i}")
        a = c2.number_input(f"出費{i+1}：年齢", current_age, end_age, int(max(current_age, get_p(f"ea{i}", current_age+10))), key=f"ea{i}")
        if v > 0:
            special_expenses.append({"val": v, "age": a})

# --- 4. 計算ロジック ---
def run_simulation():
    balance = initial_sum
    cum_inv = initial_sum
    data = []
    total_months = (end_age - current_age) * 12
    
    # 臨時出費を月ベースに変換
    expense_dict = {}
    for e in special_expenses:
        m_idx = int((e["age"] - current_age) * 12 + 1)
        expense_dict[m_idx] = expense_dict.get(m_idx, 0) + e["val"]
    
    for m in range(1, total_months + 1):
        p_age = current_age + (m / 12)
        d_age = int(p_age - 0.00001)
        
        def get_current_v(s_list, target_age):
            res = s_list[0]["val"]
            for s in s_list:
                if target_age >= s["age"]: res = s["val"]
            return res

        # 利率
        ann_rate = get_current_v(rates, p_age) / 100
        # 臨時出費の実行
        current_exp = expense_dict.get(m, 0)
        balance = max(0, balance - current_exp)
        
        m_flow = 0
        if p_age > withdrawals_start_age:
            m_flow = -get_current_v(withdrawals, p_age)
            action = "取り崩し"
        else:
            m_flow = get_current_v(deposits, p_age)
            cum_inv += m_flow
            action = "積立"
            
        balance = max(0, balance + m_flow) * (1 + ann_rate / 12)
        data.append({"年齢(グラフ)": p_age, "年齢": d_age, "月": f"{(m-1)%12+1}ヶ月", "区分": action, "月間収支": int(m_flow), "臨時出費": int(current_exp), "元本": int(cum_inv), "資産残高": int(balance)})
        if balance <= 0 and p_age > withdrawals_start_age: break
    return pd.DataFrame(data)

# --- 5. 表示エリア ---
has_input = (initial_sum > 0 or deposits[0]["val"] > 0)
if not has_input:
    st.info("👈 左側のメニューから投資額や積立額を入力してください。")
else:
    df = run_simulation()
    f_bal = df.iloc[-1]['資産残高']
    
    c1, c2 = st.columns(2)
    with c1: st.metric(f"{end_age}歳時点の資産", f"¥{f_bal:,}")
    with c2:
        if f_bal <= 0: st.error(f"⚠️ {int(df.iloc[-1]['年齢(グラフ)'])}歳で資産消滅")
        else: st.success("✅ 資産を維持できています")

    max_v = max(df["資産残高"].max(), df["元本"].max()) / 10000
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["年齢(グラフ)"], y=df["資産残高"]/10000, name="資産残高", line=dict(color="#1f77b4", width=3)))
    fig.add_trace(go.Scatter(x=df["年齢(グラフ)"], y=df["元本"]/10000, name="投資元本", line=dict(color="#ff7f0e", width=2, dash="dash")))
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=400, hovermode="x unified", legend=dict(orientation="h", y=1.02, x=1), template="plotly_white")
    gc, zc = "rgba(128,128,128,0.3)", "gray"
    fig.update_xaxes(title="年齢 (歳)", range=[current_age-2, end_age+2], dtick=5, showgrid=True, gridcolor=gc, griddash='dot', zeroline=True, zerolinecolor=zc, zerolinewidth=2)
    fig.update_yaxes(title="金額 (万円)", range=[-max_v*0.05, max_v*1.15], ticksuffix="万", tickformat=",", showgrid=True, gridcolor=gc, griddash='dot', zeroline=True, zerolinecolor=zc, zerolinewidth=2)
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("📊 詳細データ"):
        st.dataframe(df[["年齢", "月", "区分", "月間収支", "臨時出費", "元本", "資産残高"]], use_container_width=True, hide_index=True)
    st.download_button(label="📥 CSV保存", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="sim_result.csv", mime="text/csv")

# --- 6. URLクエリパラメータ更新 ---
st.query_params.update({k: v for k, v in st.session_state.items() if not k.startswith("FormSubmit")})
