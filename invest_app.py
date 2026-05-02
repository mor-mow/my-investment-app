import streamlit as st
import pandas as pd

# 1. ページ基本設定
st.set_page_config(page_title="資産シミュレーター", layout="centered")

# タイトルをコンパクトに表示
st.markdown("### 📱 資産シミュレーター") 

# --- 2. URLから初期値を取得する関数 ---
def get_param(key, default):
    params = st.query_params
    if key in params:
        val = params[key]
        try:
            return float(val) if "." in val else int(val)
        except:
            return val # 文字列（取り崩し方法など）の場合はそのまま返す
    return default

# --- 3. サイドバー設定エリア ---
st.sidebar.header("⚙️ 基本設定")
c_age_val = get_param("age", 30)
current_age = st.sidebar.number_input("現在の年齢", value=int(c_age_val), min_value=0, max_value=100)
end_age = st.sidebar.slider("終了年齢", int(current_age), 100, int(max(current_age, get_param("end", 85))))
initial_investment = st.sidebar.number_input("現在の一括投資額 (円)", value=int(get_param("init", 0)), step=100000)

with st.sidebar.expander("💰 積立の設定"):
    monthly_deposit_1 = st.number_input("初期の月間積立 (円)", value=int(get_param("d1", 0)), step=5000)
    change_deposit_age = st.slider("積立額を変える年齢", int(current_age), int(end_age), int(max(current_age, get_param("cd", 45))))
    monthly_deposit_2 = st.number_input("変更後の月間積立 (円)", value=int(get_param("d2", 0)), step=5000)

with st.sidebar.expander("🏥 臨時出費の設定"):
    exp_1_age = st.number_input("出費1：年齢", int(current_age), int(end_age), int(max(current_age, get_param("e1a", 40))))
    exp_1_v = st.number_input("出費1：金額 (円)", value=int(get_param("e1v", 0)), step=100000)
    exp_2_age = st.number_input("出費2：年齢", int(current_age), int(end_age), int(max(current_age, get_param("e2a", 50))))
    exp_2_v = st.number_input("出費2：金額 (円)", value=int(get_param("e2v", 0)), step=100000)
    exp_3_age = st.number_input("出費3：年齢", int(current_age), int(end_age), int(max(current_age, get_param("e3a", 60))))
    exp_3_v = st.number_input("出費3：金額 (円)", value=int(get_param("e3v", 0)), step=100000)

st.sidebar.header("📉 年率設定")
is_simple_rate = st.sidebar.checkbox("年率を全期間で固定する", value=True)
if is_simple_rate:
    fixed_rate_val = st.sidebar.slider("固定年率 (%)", -15.0, 15.0, float(get_param("fr", 3.0)), 0.1)
    fixed_rate = fixed_rate_val / 100
else:
    with st.sidebar.expander("年率の詳細設定（3段階）", expanded=True):
        rate_1_val = st.sidebar.slider("年率①：初期 (%)", -15.0, 15.0, 5.0, 0.1)
        change_rate_age_1 = st.sidebar.slider("②への切替年齢", int(current_age), int(end_age), int(max(current_age, get_param("cr1", 45))))
        rate_2_val = st.sidebar.slider("年率②：中期 (%)", -15.0, 15.0, 3.0, 0.1)
        change_rate_age_2 = st.sidebar.slider("③への切替年齢", int(change_rate_age_1), int(end_age), int(max(change_rate_age_1, get_param("cr2", 65))))
        rate_3_val = st.sidebar.slider("年率③：後期 (%)", -15.0, 15.0, 1.0, 0.1)
        rate_1, rate_2, rate_3 = rate_1_val/100, rate_2_val/100, rate_3_val/100

st.sidebar.header("🚪 取り崩し設定")
start_withdrawal_age = st.sidebar.slider("取り崩し開始年齢", int(current_age), int(end_age), int(max(current_age, get_param("wa", 65))))

# 修正：取り崩し方法（定額か定率か）の記憶
w_types = ["定額 (円)", "定率 (%)"]
w_type_default = get_param("wt", "定額 (円)")
withdrawal_type = st.sidebar.radio("取り崩し方法", w_types, index=w_types.index(w_type_default) if w_type_default in w_types else 0)

if withdrawal_type == "定額 (円)":
    monthly_withdrawal_amount = st.sidebar.number_input("毎月の取り崩し額 (円)", value=int(get_param("wv", 0)), step=5000)
else:
    annual_withdrawal_rate_val = st.sidebar.slider("年間の取り崩し率 (%)", 0.0, 20.0, float(get_param("wr", 0.0)), 0.1)
    annual_withdrawal_rate = annual_withdrawal_rate_val / 100

# --- 4. URLクエリパラメータの更新 ---
new_params = {
    "age": current_age, "end": end_age, "init": initial_investment,
    "d1": monthly_deposit_1, "cd": change_deposit_age, "d2": monthly_deposit_2,
    "e1a": exp_1_age, "e1v": exp_1_v, "e2a": exp_2_age, "e2v": exp_2_v, "e3a": exp_3_age, "e3v": exp_3_v,
    "wa": start_withdrawal_age, "fr": fixed_rate_val if is_simple_rate else 3.0,
    "wt": withdrawal_type # 取り崩しタイプを保存
}
if not is_simple_rate:
    new_params.update({"cr1": change_rate_age_1, "cr2": change_rate_age_2})
if withdrawal_type == "定額 (円)": new_params["wv"] = monthly_withdrawal_amount
else: new_params["wr"] = annual_withdrawal_rate_val

st.query_params.update(**new_params)

# --- 5. 計算ロジック ---
def run_simulation():
    balance = initial_investment
    cumulative_investment = initial_investment
    data = []
    special_expenses = {
        int((exp_1_age - current_age) * 12 + 1): exp_1_v,
        int((exp_2_age - current_age) * 12 + 1): exp_2_v,
        int((exp_3_age - current_age) * 12 + 1): exp_3_v
    }
    total_months = int((end_age - current_age) * 12)
    
    for month_idx in range(1, total_months + 1):
        precise_age = current_age + (month_idx / 12)
        display_age = int(current_age + (month_idx - 1) // 12)
        display_month = (month_idx - 1) % 12 + 1
        
        annual_rate = fixed_rate if is_simple_rate else (rate_1 if precise_age <= change_rate_age_1 else rate_2 if precise_age <= change_rate_age_2 else rate_3)
        monthly_rate = annual_rate / 12
        balance = max(0, balance - special_expenses.get(month_idx, 0))
        
        monthly_cashflow = 0
        if precise_age > start_withdrawal_age:
            monthly_cashflow = -monthly_withdrawal_amount if withdrawal_type == "定額 (円)" else -(balance * annual_withdrawal_rate) / 12
            action_name = "取り崩し"
        else:
            monthly_cashflow = monthly_deposit_1 if precise_age <= change_deposit_age else monthly_deposit_2
            cumulative_investment += monthly_cashflow
            action_name = "積立"
            
        balance = max(0, balance + monthly_cashflow) * (1 + monthly_rate)
        data.append({"年齢（グラフ）": precise_age, "年齢": display_age, "月": f"{display_month}ヶ月目", "区分": action_name, "月間収支": int(monthly_cashflow), "臨時出費": int(expense if (expense := special_expenses.get(month_idx, 0)) else 0), "投資元本": int(cumulative_investment), "資産残高": int(balance)})
        if balance <= 0 and precise_age > start_withdrawal_age: break
    return pd.DataFrame(data)

# --- 6. 表示エリア ---
has_input = (initial_investment > 0 or monthly_deposit_1 > 0 or monthly_deposit_2 > 0)
if not has_input:
    st.info("👈 左側のメニューから設定を入力してください。")
else:
    df = run_simulation()
    final_bal = df.iloc[-1]['資産残高']
    col1, col2 = st.columns(2)
    with col1: st.metric(label=f"{end_age}歳時点の予想資産", value=f"¥{final_bal:,}")
    with col2:
        if final_bal <= 0: st.error(f"⚠️ {int(df.iloc[-1]['年齢（グラフ）'])}歳で資産消滅")
        else: st.success("✅ シミュレーション完了")
        st.caption("※現在の設定はURLに保存されています。ブックマーク推奨")
    st.line_chart(df.set_index("年齢（グラフ）")["資産残高"], height=350, use_container_width=True)
    with st.expander("📊 月ごとの詳細データ"):
        st.dataframe(df[["年齢", "月", "区分", "月間収支", "臨時出費", "投資元本", "資産残高"]], use_container_width=True, hide_index=True)
