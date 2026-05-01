import streamlit as st
import pandas as pd

st.title("ライフプラン・資産運用シミュレーター Pro")

# --- サイドバー設定 ---
st.sidebar.header("1. 基本設定")
current_age = st.sidebar.number_input("現在の年齢", value=30, min_value=0, max_value=100)
end_age = st.sidebar.slider("シミュレーション終了年齢", int(current_age), 100, int(max(current_age, 85)))
initial_investment = st.sidebar.number_input("現在の一括投資額 (円)", value=1000000, step=100000)

st.sidebar.subheader("積立の2段階設定")
monthly_deposit_1 = st.sidebar.number_input("初期の月間積立額 (円)", value=50000, step=5000)
change_deposit_age = st.sidebar.slider("積立額を変える年齢", int(current_age), int(end_age), int(max(current_age, 45)))
monthly_deposit_2 = st.sidebar.number_input("変更後の月間積立額 (円)", value=100000, step=5000)

st.sidebar.header("2. 取り崩し設定")
start_withdrawal_age = st.sidebar.slider("取り崩しを開始する年齢", int(current_age), int(end_age), int(max(current_age, 65)))
monthly_withdrawal = st.sidebar.number_input("毎月の取り崩し額 (円)", value=150000, step=5000)

st.sidebar.header("3. 臨時出費の設定")
exp_1_age = st.sidebar.number_input("出費1：何歳？", int(current_age), int(end_age), int(max(current_age, 40)))
exp_1_v = st.sidebar.number_input("出費1：金額 (円)", value=0, step=100000)
exp_2_age = st.sidebar.number_input("出費2：何歳？", int(current_age), int(end_age), int(max(current_age, 50)))
exp_2_v = st.sidebar.number_input("出費2：金額 (円)", value=0, step=100000)
exp_3_age = st.sidebar.number_input("出費3：何歳？", int(current_age), int(end_age), int(max(current_age, 60)))
exp_3_v = st.sidebar.number_input("出費3：金額 (円)", value=0, step=100000)

st.sidebar.header("4. 年率設定（マイナス対応）")
# 最小値を -15.0% に設定
rate_1 = st.sidebar.slider("年率①：初期 (%)", -15.0, 15.0, 5.0, 0.1) / 100
change_rate_age_1 = st.sidebar.slider("年率②へ切替年齢", int(current_age), int(end_age), int(max(current_age, 45)))
rate_2 = st.sidebar.slider("年率②：中期 (%)", -15.0, 15.0, 3.0, 0.1) / 100
change_rate_age_2 = st.sidebar.slider("年率③へ切替年齢", int(change_rate_age_1), int(end_age), int(max(change_rate_age_1, 65)))
rate_3 = st.sidebar.slider("年率③：後期 (%)", -15.0, 15.0, 1.0, 0.1) / 100

# --- 計算ロジック ---
def run_simulation():
    balance = initial_investment
    data = []
    special_expenses = {
        int((exp_1_age - current_age) * 12): exp_1_v,
        int((exp_2_age - current_age) * 12): exp_2_v,
        int((exp_3_age - current_age) * 12): exp_3_v
    }
    
    for month in range(1, (end_age - current_age) * 12 + 1):
        age = current_age + (month / 12)
        if age <= change_rate_age_1:
            current_rate = rate_1
        elif age <= change_rate_age_2:
            current_rate = rate_2
        else:
            current_rate = rate_3
        
        # 臨時出費
        balance = max(0, balance - special_expenses.get(month, 0))
        
        # 積立 or 取り崩し
        if age > start_withdrawal_age:
            balance = max(0, balance - monthly_withdrawal) * (1 + current_rate / 12)
        else:
            deposit = monthly_deposit_1 if age <= change_deposit_age else monthly_deposit_2
            balance = (balance + deposit) * (1 + current_rate / 12)
        
        data.append({"年齢": round(age, 1), "資産残高": int(balance)})
        if balance <= 0 and age > start_withdrawal_age:
            break
    return pd.DataFrame(data)

df = run_simulation()

# --- メイン画面表示 ---
st.subheader(f"{end_age}歳時点の資産残高: ¥{df.iloc[-1]['資産残高']:,}")
if df.iloc[-1]['資産残高'] <= 0:
    st.error(f"⚠️ {df.iloc[-1]['年齢']}歳で資産が底をつきます。")

st.line_chart(df.set_index("年齢")["資産残高"])
if st.checkbox("詳細データを表示"):
    st.dataframe(df)
