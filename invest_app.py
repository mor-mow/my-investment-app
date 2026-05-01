import streamlit as st
import pandas as pd

st.title("資産運用・2段階積立＆取り崩しシミュレーター")

# --- サイドバーで設定 ---
st.sidebar.header("1. 投資・積立設定")
years = st.sidebar.slider("シミュレーション期間 (年)", 1, 50, 30)
initial_investment = st.sidebar.number_input("一括投資額 (円)", value=1000000, step=100000)

st.sidebar.subheader("積立の2段階設定")
monthly_deposit_1 = st.sidebar.number_input("初期の月間積立額 (円)", value=50000, step=5000)
change_deposit_year = st.sidebar.slider("積立額を変える年", 0, years, 10)
monthly_deposit_2 = st.sidebar.number_input("変更後の月間積立額 (円)", value=100000, step=5000)

st.sidebar.header("2. 取り崩し設定")
start_withdrawal_year = st.sidebar.slider("取り崩しを開始する年", 0, years, 25)
monthly_withdrawal = st.sidebar.number_input("毎月の取り崩し額 (円)", value=150000, step=5000)

st.sidebar.header("3. 年率設定")
rate_early = st.sidebar.slider("初期の年率 (%)", 0.0, 15.0, 3.0, 0.1) / 100
change_rate_year = st.sidebar.slider("年率を変える年", 0, years, 20)
rate_later = st.sidebar.slider("変更後の年率 (%)", 0.0, 15.0, 5.0, 0.1) / 100

# --- 計算ロジック ---
def run_simulation():
    balance = initial_investment
    data = []
    total_investment = initial_investment
    
    for month in range(1, years * 12 + 1):
        # 1. 適用する利率の決定
        current_rate = rate_early if month <= change_rate_year * 12 else rate_later
        
        # 2. 状態（積立 or 取り崩し）の判定
        if month > start_withdrawal_year * 12:
            # 取り崩し期
            balance = max(0, balance - monthly_withdrawal) * (1 + current_rate / 12)
            action_type = "取り崩し"
        else:
            # 積立期（2段階）
            current_deposit = monthly_deposit_1 if month <= change_deposit_year * 12 else monthly_deposit_2
            balance = (balance + current_deposit) * (1 + current_rate / 12)
            total_investment += current_deposit
            action_type = "積立"
        
        data.append({
            "年": round(month/12, 2),
            "資産残高": int(balance),
            "累積投資額": int(total_investment) if action_type == "積立" else None,
            "タイプ": action_type
        })
        
        if balance <= 0 and action_type == "取り崩し":
            break
            
    return pd.DataFrame(data)

df = run_simulation()

# --- 結果表示 ---
final_balance = df.iloc[-1]['資産残高']
last_year = df.iloc[-1]['年']

if final_balance <= 0:
    st.error(f"⚠️ {last_year}年目で資産が底をつきます。")
else:
    st.success(f"{years}年後の最終残高: ¥{final_balance:,}")

# メトリック表示
col1, col2 = st.columns(2)
col1.metric("最終残高", f"¥{final_balance:,}")
col2.metric("運用継続期間", f"{last_year}年")

# グラフ表示
st.subheader("資産推移")
st.line_chart(df.set_index("年")["資産残高"])

# 詳細データ
if st.checkbox("詳細データを表示"):
    st.dataframe(df)
