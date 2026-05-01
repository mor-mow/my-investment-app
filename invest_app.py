import streamlit as st
import pandas as pd

# 1. ページ基本設定（スマホ対応）
st.set_page_config(page_title="資産シミュレーター", layout="centered")

st.title("📱 ライフプラン・シミュレーター")

# --- 2. サイドバー設定エリア ---
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
        rate_2 = st.slider("年率②：中期 (%)", -15.0, 15.0, 3.0, 0.1) / 100
        change_rate_age_2 = st.slider("③への切替年齢", int(change_rate_age_1), int(end_age), int(max(change_rate_age_1, 65)))
        rate_3 = st.slider("年率③：後期 (%)", -15.0, 15.0, 1.0, 0.1) / 100

st.sidebar.header("🚪 取り崩し設定")
start_withdrawal_age = st.sidebar.slider("取り崩し開始年齢", int(current_age), int(end_age), int(max(current_age, 65)))
withdrawal_type = st.sidebar.radio("取り崩し方法", ["定額 (円)", "定率 (%)"])
if withdrawal_type == "定額 (円)":
    monthly_withdrawal_amount = st.sidebar.number_input("毎月の取り崩し額 (円)", value=0, step=5000)
else:
    annual_withdrawal_rate = st.sidebar.slider("年間の取り崩し率 (%)", 0.0, 20.0, 0.0, 0.1) / 100

# --- 3. 計算ロジック ---
def run_simulation():
    balance = initial_investment
    cumulative_investment = initial_investment
    data = []
    
    # 臨時出費のタイミングを月インデックスで作成
    special_expenses = {
        int((exp_1_age - current_age) * 12 + 1): exp_1_v,
        int((exp_2_age - current_age) * 12 + 1): exp_2_v,
        int((exp_3_age - current_age) * 12 + 1): exp_3_v
    }
    
    total_months = int((end_age - current_age) * 12)
    
    for month_idx in range(1, total_months + 1):
        elapsed_years = (month_idx - 1) // 12
        display_age = current_age + elapsed_years
        display_month = (month_idx - 1) % 12 + 1
        
        # 正しい利率（年率を12で割って月利にする）
        if is_simple_rate:
            annual_rate = fixed_rate
        else:
            annual_rate = rate_1 if display_age <= change_rate_age_1 else rate_2 if display_age <= change_rate_age_2 else rate_3
        monthly_rate = annual_rate / 12
            
        # 臨時出費
        expense = special_expenses.get(month_idx, 0)
        balance = max(0, balance - expense)
        
        # 月次キャッシュフロー
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
            
        # 資産残高の更新（複利計算）
        balance = max(0, balance + monthly_cashflow) * (1 + monthly_rate)
        
        data.append({
            "年齢": display_age,
            "月": f"{display_month}ヶ月目",
            "区分": action_name,
            "月間収支": int(monthly_cashflow),
            "臨時出費": int(expense),
            "投資元本": int(cumulative_investment),
            "資産残高": int(balance)
        })
        
        # 資産が尽きたら終了（取り崩し期間のみ）
        if balance <= 0 and display_age >= start_withdrawal_age:
            break
            
    return pd.DataFrame(data)

# --- 4. メイン画面の表示制御 ---
# 何らかの投資・積立設定があるかチェック
has_input = (initial_investment > 0 or monthly_deposit_1 > 0 or monthly_deposit_2 > 0)

if not has_input:
    st.info("👈 左側のメニューから、現在の一括投資額や毎月の積立額を入力してください。")
else:
    df = run_simulation()
    final_bal = df.iloc[-1]['資産残高']
    
    # 最終結果の強調表示
    st.metric(label=f"{end_age}歳時点の予想資産", value=f"¥{final_bal:,}")
    
    if final_bal <= 0 and df.iloc[-1]['年齢'] < end_age:
        st.error(f"⚠️ {df.iloc[-1]['年齢']}歳で資産がなくなります")

    # 資産推移グラフ
    st.line_chart(df.set_index("年齢")["資産残高"], height=300)

    # 詳細テーブル
    with st.expander("📊 月ごとの詳細データ（収支・元本）"):
        st.dataframe(
            df[["年齢", "月", "区分", "月間収支", "臨時出費", "投資元本", "資産残高"]], 
            use_container_width=True,
            hide_index=True
        )
