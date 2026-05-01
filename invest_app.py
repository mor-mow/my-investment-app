import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="資産シミュレーター", layout="centered")

st.title("📱 ライフプラン・シミュレーター")

# --- サイドバー設定 ---
st.sidebar.header("⚙️ 基本設定")
current_age = st.sidebar.number_input("現在の年齢", value=30, min_value=0, max_value=100)
end_age = st.sidebar.slider("終了年齢", int(current_age), 100, int(max(current_age, 85)))
initial_investment = st.sidebar.number_input("現在の一括投資額 (円)", value=1000000, step=100000)

with st.sidebar.expander("💰 積立の設定"):
    monthly_deposit_1 = st.number_input("初期の月間積立 (円)", value=50000, step=5000)
    change_deposit_age = st.slider("積立額を変える年齢", int(current_age), int(end_age), int(max(current_age, 45)))
    monthly_deposit_2 = st.number_input("変更後の月間積立 (円)", value=100000, step=5000)

with st.sidebar.expander("🏥 臨時出費の設定"):
    exp_1_age = st.number_input("出費1：年齢", int(current_age), int(end_age), int(max(current_age, 40)))
    exp_1_v = st.number_input("出費1：金額 (円)", value=0, step=100000)
    
    exp_2_age = st.number_input("出費2：年齢", int(current_age), int(end_age), int(max(current_age, 50)))
    exp_2_v = st.number_input("出費2：金額 (円)", value=0, step=100000)
    
    exp_3_age = st.number_input("出費3：年齢", int(current_age), int(end_age), int(max(current_age, 60)))
    exp_3_v = st.number_input("出費3：金額 (円)", value=0, step=100000)

with st.sidebar.expander("📉 年率設定（3段階）"):
    rate_1 = st.slider("年率① (%)", -15.0, 15.0, 5.0, 0.1) / 100
    change_rate_age_1 = st.slider("②への切替年齢", int(current_age), int(end_age), int(max(current_age, 45)))
    rate_2 = st.slider("年率② (%)", -15.0, 15.0, 3.0, 0.1) / 100
    change_rate_age_2 = st.slider("③への切替年齢", int(change_rate_age_1), int(end_age), int(max(change_rate_age_1, 65)))
    rate_3 = st.slider("年率③ (%)", -15.0, 15.0, 1.0, 0.1) / 100

st.sidebar.header("🚪 取り崩し設定")
start_withdrawal_age = st.sidebar.slider("開始年齢", int(current_age), int(end_age), int(max(current_age, 65)))
monthly_withdrawal = st.sidebar.number_input("毎月の取り崩し (円)", value=150000, step=5000)

# --- 計算ロジック ---
def run_simulation():
    balance = initial_investment
    data = []
    # 出費3をしっかり追加
    special_expenses = {
        int((exp_1_age - current_age) * 12): exp_1_v,
        int((exp_2_age - current_age) * 12): exp_2_v,
        int((exp_3_age - current_age) * 12): exp_3_v
    }
    
    for month in range(1, (end_age - current_age) * 12 + 1):
        age = current_age + (month / 12)
        # 利率決定
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

# --- メイン表示 ---
final_bal = df.iloc[-1]['資産残高']
st.metric(label=f"{end_age}歳時点の予想資産", value=f"¥{final_bal:,}")

if final_bal <= 0:
    st.error(f"⚠️ {df.iloc[-1]['年齢']}歳で資産がなくなります")

st.line_chart(df.set_index("年齢")["資産残高"], height=300)

with st.expander("📊 月ごとの詳細データ"):
    st.dataframe(df, use_container_width=True)
