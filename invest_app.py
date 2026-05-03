import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="資産シミュレーター", layout="centered")
st.markdown("### 📱 資産シミュレーター (安定版)")

# --- 1. サイドバー設定 ---
st.sidebar.header("⚙️ 基本設定")
age = st.sidebar.number_input("現在の年齢", 0, 100, 30)
end_age = st.sidebar.slider("終了年齢", age, 100, 85)
balance = float(st.sidebar.number_input("現在の一括投資額 (円)", 0, None, 1000000, 100000))

st.sidebar.header("💰 積立設定")
dep1 = st.sidebar.number_input("積立1 (月額/円)", 0, None, 50000, 5000)
dep_change_age = st.sidebar.slider("積立額を変える年齢", age, end_age, 45)
dep2 = st.sidebar.number_input("積立2 (月額/円)", 0, None, 100000, 5000)

st.sidebar.header("📈 年率設定")
r1 = st.sidebar.slider("年率1 (%)", -10.0, 20.0, 5.0, 0.1) / 100
r_change_age = st.sidebar.slider("年率を変える年齢", age, end_age, 60)
r2 = st.sidebar.slider("年率2 (%)", -10.0, 20.0, 3.0, 0.1) / 100

st.sidebar.header("🚪 取り崩し設定")
w_age = st.sidebar.slider("取り崩し開始年齢", age, end_age, 65)
w_type = st.sidebar.radio("方法", ["定額 (円)", "定率 (%)"])
w_val = st.sidebar.number_input("取り崩し額(月) または 率(年)", 0.0, None, 150000.0 if w_type=="定額 (円)" else 4.0, 5000.0)

# --- 2. 計算ロジック ---
data = []
total_months = (end_age - age) * 12
cum_inv = balance

for m in range(1, total_months + 1):
    curr_age = age + (m-1)/12
    
    # 利率の決定
    rate = r1 if curr_age < r_change_age else r2
    
    # 収支の決定
    m_flow = 0.0
    action = "待機"
    
    if curr_age >= w_age:
        # 取り崩し
        action = "取り崩し"
        if w_type == "定額 (円)":
            m_flow = -float(w_val)
        else:
            m_flow = -(balance * (w_val / 100)) / 12
    else:
        # 積立
        action = "積立"
        m_flow = float(dep1 if curr_age < dep_change_age else dep2)
        cum_inv += m_flow
    
    # 【最重要】残高更新：収支を足し引きしてから、利息をつける
    balance = max(0.0, balance + m_flow)
    balance *= (1 + rate / 12)
    
    data.append({
        "年齢": round(curr_age + 1/12, 2),
        "区分": action,
        "月間収支": int(m_flow),
        "資産残高": int(balance),
        "投資元本": int(cum_inv)
    })
    if balance <= 0 and action == "取り崩し": break

# --- 3. 表示 ---
df = pd.DataFrame(data)
if not df.empty:
    st.metric("最終資産残高", f"¥{df.iloc[-1]['資産残高']:,}")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["年齢"], y=df["資産残高"]/10000, name="資産残高", line=dict(color="#1f77b4", width=3)))
    fig.add_trace(go.Scatter(x=df["年齢"], y=df["投資元本"]/10000, name="投資元本", line=dict(color="#ff7f0e", dash="dash")))
    fig.update_layout(template="plotly_white", margin=dict(l=10,r=10,t=10,b=10), height=400, yaxis_title="万円", hovermode="x unified")
    fig.update_xaxes(dtick=5, showgrid=True, gridcolor='rgba(128,128,128,0.2)', griddash='dot')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)', griddash='dot')
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("詳細データ"):
        st.dataframe(df, use_container_width=True)
