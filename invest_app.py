import streamlit as st
import pandas as pd

st.title("ライフプラン・資産運用シミュレーター")

# --- サイドバーで設定 ---
st.sidebar.header("1. 基本設定")
current_age = st.sidebar.number_input("現在の年齢", value=30, min_value=0, max_value=100)
end_age = st.sidebar.slider("シミュレーション終了年齢", current_age, 100, 80)
simulation_years = end_age - current_age # 運用期間を計算

initial_investment = st.sidebar.number_input("現在の一括投資額 (円)", value=1000000, step=100000)

st.sidebar.subheader("積立の2段階設定")
monthly_deposit_1 = st.sidebar.number_input("初期の月間積立額 (円)", value=50000, step=5000)
change_deposit_age = st.sidebar.slider("積立額を変える年齢", current_age, end_age, 40)
monthly_deposit_2 = st.sidebar.number_input("変更後の月間積立額 (円)", value=100000, step=5000)

st.sidebar.header("2. 取り崩し設定")
start_withdrawal_age = st.sidebar.slider("取り崩しを開始する年齢", current_age, end_age, 65)
monthly_withdrawal = st.sidebar.number_input("毎月の取り崩し額 (円)", value=150000, step=5000)

st.sidebar.header("3. 臨時出費の設定")
exp_1_age = st.sidebar.number_input("出費1：何歳？", current_age, end_age, current_age + 5)
exp_1_v = st.sidebar.number_input("出費1：金額 (円)", value=0, step=100000)

exp_2_age = st.sidebar.number_input("出費2：何歳？", current_age, end_age, current_age + 10)
exp_2_v = st.sidebar.number_input("出費2：金額 (円)", value=0, step=100000)

exp_3_age = st.sidebar.number_input("出費3：何歳？", current_age, end_age, current_age + 15)
exp_3_v = st.sidebar.number_input("出費3：金額 (円)", value=0, step=100000)

st.sidebar.header("4. 年率設定")
rate_early = st.sidebar.slider("初期の年率 (%)", 0.0, 15.0, 3.0, 0.1) / 100
change_rate_age = st.sidebar.slider("年率を変える年齢", current_age, end_age, 60)
rate_later = st.sidebar.slider("変更後の年率 (%)", 0.0, 15.0, 3.0, 0.1) / 100

# --- 計算ロジック ---
def run_simulation():
    balance = initial_investment
    data = []
    
    # 臨時出費のタイミング（月数）を計算
    special_expenses = {
        int((exp_1_age - current_age) * 12): exp_1_v,
        int((exp_2_age - current_age) * 12): exp_2_v,
        int((exp_3_age - current_age) * 12): exp_3_v
    }
    
    for month in range(1, (end_age - current_age) * 12 + 1):
        age = current_age + (month / 12)
        
        # 1. 利率決定
        current_rate = rate_early if age <= change_rate_age else rate_later
        
        # 2. 臨時出費
        expense_today = special_expenses.get(month, 0)
        balance = max(0, balance - expense_today)
        
        # 3. 積立 or 取り崩し
        if age > start_withdrawal_age:
            balance = max(0, balance - monthly_withdrawal) * (1 + current_rate / 12)
        else:
            current_deposit = monthly_deposit_1 if age <= change_deposit_age else monthly_deposit_2
            balance = (balance + current_deposit) * (1 + current_rate / 12)
        
        data.append({
            "年齢": round(age, 1),
            "資産残高": int(balance)
        })
        
        if balance <= 0 and age > start_withdrawal_age:
            break
            
    return pd.DataFrame(data)

df = run_simulation()

# --- 表示 ---
st.subheader(f"{end_age}歳時点の資産残高: ¥{df.iloc[-1]['資産残高']:,}")
if df.iloc[-1]['資産残高'] <= 0:
    st.error(f"⚠️ {df.iloc[-1]['年齢']}歳で資産が底をつきます。")

st.line_chart(df.set_index("年齢")["資産残高"])

if st.checkbox("詳細データを表示"):
    st.dataframe(df)
