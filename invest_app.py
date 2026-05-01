import streamlit as st
import pandas as pd

st.set_page_config(page_title="資産シミュレーター", layout="centered")

st.title("📱 ライフプラン・シミュレーター")

# --- サイドバー設定 ---
st.sidebar.header("⚙️ 基本設定")
current_age = st.sidebar.number_input("現在の年齢", value=30, min_value=0, max_value=100)
end_age = st.sidebar.slider("終了年齢", int(current_age), 100, int(max(current_age, 85)))
initial_investment = st.sidebar.number_input("現在の一括投資額 (円)", value=0, step=100000)

with st.sidebar.expander("💰 積立の設定"):
    monthly_deposit_1 = st.number_input("初期の月間積立 (円)", value=0, step=5000)
    change_deposit_age = st.slider("積立額を変える年齢", int(current_age), int(end_age), int(max(current_age, 45)))
    monthly_deposit_2 = st.number_input("変更後の月間積立 (円)", value=0, step=5000)

with st.sidebar.expander("🏥 臨時出費の設定"):
    exp_1_age = st.number_input("出費1：年齢", int(current_age), int(end_age), int(max(current_age, 40)))
    exp_1_v = st.number_input("出費1：金額 (円)", value=0, step=100000)
    exp_2_age = st.number_input("出費2：年齢", int(current_age), int(end_age), int(max(current_age, 50)))
    exp_2_v = st.number_input("出費2：金額 (円)", value=0, step=100000)
    exp_3_age = st.number_input("出費3：年齢", int(current_age), int(end_age), int(max(current_age, 60)))
    exp_3_v = st.number_input("出費3：金額 (円)", value=0, step=100000)

st.sidebar.header("📉 年率設定")
is_simple_rate = st.sidebar.checkbox("年率を全期間で固定する", value=True)
if is_simple_rate:
    fixed_rate = st.sidebar.slider("固定年率 (%)", -15.0, 15.0, 3.0, 0.1) / 100
else:
    with st.sidebar.expander("年率の詳細設定（3段階）", expanded=True):
        rate_1 = st.slider("年率①：初期 (%)", -15.0, 15.0, 5.0, 0.1) / 100
        change_rate_age_1 = st.slider("②への切替年齢", int(current_age), int(end_age), int(max(current_age, 45)))
        rate_2 = st.slider("年率② (%)", -15.0, 15.0, 3.0, 0.1) / 100
        change_rate_age_2 = st.slider("③への切替年齢", int(change_rate_age_1), int(end_age), int(max(change_rate_age_1, 65)))
        rate_3 = st.slider("年率③ (%)", -15.0, 15.0, 1.0, 0.1) / 100

st.sidebar.header("🚪 取り崩し設定")
start_withdrawal_age = st.sidebar.slider("開始年齢", int(current_age), int(end_age), int(max(current_age, 65)))
withdrawal_type = st.sidebar.radio("取り崩し方法", ["定額 (円)", "定率 (%)"])
if withdrawal_type == "定額 (円)":
    monthly_withdrawal_amount = st.sidebar.number_input("毎月の取り崩し額 (円)", value=0, step=5000)
else:
    annual_withdrawal_rate = st.sidebar.slider("年間の取り崩し率 (%)", 0.0, 20.0, 0.0, 0.1) / 100

# --- 計算ロジック ---
def run_simulation():
    balance = initial_investment
    cumulative_investment = initial_investment
    data = []
    special_expenses = {
        int((exp_1_age - current_age) * 12): exp_1_v,
        int((exp_2_age - current_age) * 12): exp_2_v,
        int((exp_3_age - current_age) * 12): exp_3_v
    }
    
    # 運用月数を計算
    total_months = int((end_age - current_age) * 12)
    
    for month_idx in range(1, total_months + 1):
        # 現在の年齢と「その年の何ヶ月目か」を計算
        elapsed_years = (month_idx - 1) // 12
        display_age = current_age + elapsed_years
        display_month = (month_idx - 1) % 12 + 1
        
        # 利率決定
        current_rate = fixed_rate if is_simple_rate else (rate_1 if display_age <= change_rate_age_1 else rate_2 if display_age <= change_rate_age_2 else rate_3)
        
        # 臨時出費
        expense = special_expenses.get(month_idx, 0)
        balance = max(0, balance - expense)
        
        monthly_cashflow = 0
        if display_age >= start_withdrawal_age:
            if withdrawal_type == "定額 (円)":
                monthly_cashflow = -monthly_withdrawal_amount
            else:
                monthly_cashflow = -(balance * annual_withdrawal_rate) / 12
            action_name = "取り崩し"
        else:
            monthly_cashflow = monthly_deposit_1 if display_age < change_deposit_age else monthly_deposit_2
            cumulative_investment += monthly_cashflow
            action_name = "積立"
            
        balance = max(0, balance + monthly_cashflow) * (1 + current_rate / 12)
        
        data.append({
            "年齢": display_age,
            "月": f"{display_month}ヶ月目",
            "区分": action_name,
            "月間収支": int(monthly_cashflow),
            "臨時出費": int(expense),
            "投資元本": int(cumulative_investment),
            "資産残高": int(balance)
        })
        
        if balance <= 0 and display_age >= start_withdrawal_age:
            break
            
    return pd.DataFrame(data)

# --- 表示エリア ---
if not has_input:
    st.info("👈 左側のメニューから設定を入力してください。")
else:
    df = run_simulation()
    # ...（中略：メトリクスとグラフ表示）...
    
    with st.expander("📊 月ごとの詳細データ（全期間を表示）"):
        # 列の順番を整理して表示
        st.dataframe(
            df[["年齢", "月", "区分", "月間収支", "臨時出費", "投資元本", "資産残高"]], 
            use_container_width=True,
            hide_index=True # インデックスを隠してスッキリさせる
        )
