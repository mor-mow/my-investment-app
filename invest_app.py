# --- 6. 表示エリア（グラフ設定のアップデート） ---
if not has_input:
    st.info("👈 左側のメニューから設定を入力してください。")
else:
    df = run_simulation()
    f_bal = df.iloc[-1]['資産残高']
    f_age = df.iloc[-1]['年齢（グラフ）']
    
    df["資産(万円)"] = df["資産残高"] / 10000
    df["元本(万円)"] = df["元本合計"] / 10000
    
    max_val = max(df["資産(万円)"].max(), df["元本(万円)"].max())
    y_upper = max_val * 1.15 if max_val > 0 else 100

    col1, col2 = st.columns(2)
    with col1: st.metric(label=f"{end_age}歳時点の予想資産", value=f"¥{f_bal:,}")
    with col2:
        if f_bal <= 0: st.error(f"⚠️ {int(f_age)}歳で資産消滅")
        else: st.success("✅ 資産を維持できています")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["年齢（グラフ）"], y=df["資産(万円)"], name="資産残高", line=dict(color="#1f77b4", width=3)))
    fig.add_trace(go.Scatter(x=df["年齢（グラフ）"], y=df["元本(万円)"], name="投資元本", line=dict(color="#ff7f0e", width=2, dash="dash")))

    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10), height=400, hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title="金額 (万円)", template="plotly_white"
    )
    
    # --- 横軸の調整（グリッドを点線に） ---
    fig.update_xaxes(
        title="年齢 (歳)", 
        range=[current_age - 2, end_age + 2], 
        dtick=5, 
        showgrid=True, 
        gridcolor='LightGray', 
        gridwidth=1, 
        griddash='dot', # 点線に設定
        zeroline=True,
        zerolinecolor='Black'
    )
    
    # --- 縦軸の調整（グリッドを点線に） ---
    fig.update_yaxes(
        range=[-max_val*0.05, y_upper], 
        ticksuffix="万", 
        tickformat=",", 
        showgrid=True,
        gridcolor='LightGray',
        gridwidth=1,
        griddash='dot', # 点線に設定
        zeroline=True,
        zerolinecolor='Black'
    ) 

    # 注釈
    fig.add_annotation(x=current_age, y=0, text=f"開始:{current_age}歳", showarrow=True, arrowhead=1, yshift=-20)
    fig.add_annotation(x=f_age, y=df.iloc[-1]["資産(万円)"], text=f"終了:{int(f_age)}歳", showarrow=True, arrowhead=1, ax=40, ay=-40)
    
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("📊 詳細データ（円単位）"):
        st.dataframe(df[["年齢", "月", "区分", "月間収支", "臨時出費", "元本合計", "資産残高"]], use_container_width=True, hide_index=True)
    st.download_button(label="📥 CSV保存", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="sim_result.csv", mime="text/csv")
