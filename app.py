import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
from datetime import datetime

# --- ファイル設定 ---
SETTINGS_FILE = 'settings.json'
HISTORY_FILE = 'history.csv'

# 今日の日付から「2026年05月」みたいな文字列を作る
current_month = datetime.now().strftime("%Y-%m")

def load_settings():
    defaults = {
        "accounts": [
            {"name": "メイン銀行", "amount": 1000000, "category": "個人"},
            {"name": "家族共有口座", "amount": 2000000, "category": "家族"}
        ],
        "p_income": 200000, "f_income": 400000,
        "p_expenses": [{"name": "お小遣い", "amount": 30000}],
        "f_expenses": [{"name": "家賃", "amount": 100000}, {"name": "食費", "amount": 60000}]
    }
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            try:
                data = json.load(f)
                for k, v in defaults.items():
                    if k not in data: data[k] = v
                return data
            except: return defaults
    return defaults

def save_settings(data):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(data, f)

def save_to_history(p_total, f_total):
    # 保存した瞬間の「月」で記録する
    new_data = pd.DataFrame([[current_month, p_total, f_total]], columns=["月", "個人資産", "家族資産"])
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        df = df[df["月"] != current_month] # 同じ月のデータがあれば最新で上書き
        df = pd.concat([df, new_data], ignore_index=True)
    else:
        df = new_data
    df.to_csv(HISTORY_FILE, index=False)

# --- アプリ初期化 ---
saved_data = load_settings()
st.set_page_config(page_title=f"資産管理Pro - {current_month}", layout="wide")

if 'account_list' not in st.session_state: st.session_state.account_list = saved_data["accounts"]
if 'p_exp_list' not in st.session_state: st.session_state.p_exp_list = saved_data["p_expenses"]
if 'f_exp_list' not in st.session_state: st.session_state.f_exp_list = saved_data["f_expenses"]

# --- サイドバー：共通管理 ---
st.sidebar.header(f"📅 {current_month} の管理")

if st.sidebar.button("➕ 新しい口座を追加"):
    st.session_state.account_list.append({"name": "新口座", "amount": 0, "category": "個人"})

updated_accounts = []
for i, acc in enumerate(st.session_state.account_list):
    with st.sidebar.expander(f"{acc['category']}: {acc['name']}", expanded=False):
        n = st.text_input("口座名", value=acc["name"], key=f"acc_n_{i}")
        c = st.selectbox("区分", ["個人", "家族"], index=0 if acc["category"]=="個人" else 1, key=f"acc_c_{i}")
        a = st.number_input("金額", value=int(acc["amount"]), key=f"acc_a_{i}", step=10000)
        if st.button("削除", key=f"acc_d_{i}"):
            st.session_state.account_list.pop(i)
            st.rerun()
        updated_accounts.append({"name": n, "amount": a, "category": c})

p_total = sum(acc["amount"] for acc in updated_accounts if acc["category"] == "個人")
f_total = sum(acc["amount"] for acc in updated_accounts if acc["category"] == "家族")

if st.sidebar.button(f"💾 {current_month} のデータを確定保存"):
    save_settings({
        "accounts": updated_accounts,
        "p_income": saved_data["p_income"], "f_income": saved_data["f_income"],
        "p_expenses": st.session_state.p_exp_list, "f_expenses": st.session_state.f_exp_list
    })
    save_to_history(p_total, f_total)
    st.sidebar.success(f"{current_month} の実績を保存したで！")
    st.rerun()

# --- メイン画面 ---
tab_p, tab_f, tab_h = st.tabs(["👤 個人の収支", "🏠 家族の収支", "📈 資産推移"])

# --- 個人ページ ---
with tab_p:
    st.title(f"👤 個人マネー ({current_month})")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("💰 個人資産の内訳")
        p_df = pd.DataFrame([a for a in updated_accounts if a["category"] == "個人"])
        st.metric("個人資産合計", f"¥{p_total:,}")
        if not p_df.empty:
            st.plotly_chart(px.pie(p_df, values='amount', names='name', hole=0.4), use_container_width=True)
            st.dataframe(p_df, hide_index=True, use_container_width=True)

    with col2:
        st.subheader("💸 今月のやりくり")
        p_inc = st.number_input("個人の手取り", value=int(saved_data["p_income"]), step=10000, key="p_inc_p")
        saved_data["p_income"] = p_inc
        
        if st.button("➕ 出費を追加", key="p_add"): st.session_state.p_exp_list.append({"name": "新出費", "amount": 0})
        
        p_updated_exps = []
        for i, exp in enumerate(st.session_state.p_exp_list):
            c1, c2, c3 = st.columns([2, 2, 1])
            en = c1.text_input(f"出費名{i}", value=exp["name"], key=f"pe_n_{i}", label_visibility="collapsed")
            ea = c2.number_input(f"額{i}", value=int(exp["amount"]), key=f"pe_a_{i}", step=1000, label_visibility="collapsed")
            if c3.button("❌", key=f"pe_d_{i}"): 
                st.session_state.p_exp_list.pop(i)
                st.rerun()
            p_updated_exps.append({"name": en, "amount": ea})
        st.session_state.p_exp_list = p_updated_exps
        
        p_exp_total = sum(e["amount"] for e in p_updated_exps)
        st.metric("個人支出合計", f"¥{p_exp_total:,}", delta=f"-{p_exp_total:,}", delta_color="inverse")
        st.info(f"今月の残り予算: ¥{p_inc - p_exp_total:,}")

# --- 家族ページ ---
with tab_f:
    st.title(f"🏠 家族マネー ({current_month})")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("💰 家族資産の内訳")
        f_df = pd.DataFrame([a for a in updated_accounts if a["category"] == "家族"])
        st.metric("家族資産合計", f"¥{f_total:,}")
        if not f_df.empty:
            st.plotly_chart(px.pie(f_df, values='amount', names='name', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)
            st.dataframe(f_df, hide_index=True, use_container_width=True)

    with col2:
        st.subheader("💸 家族のやりくり")
        f_inc = st.number_input("家族の合算手取り", value=int(saved_data["f_income"]), step=10000, key="f_inc_f")
        saved_data["f_income"] = f_inc
        
        if st.button("➕ 家族出費を追加", key="f_add"): st.session_state.f_exp_list.append({"name": "新出費", "amount": 0})
        
        f_updated_exps = []
        for i, exp in enumerate(st.session_state.f_exp_list):
            c1, c2, c3 = st.columns([2, 2, 1])
            en = c1.text_input(f"家族出費名{i}", value=exp["name"], key=f"fe_n_{i}", label_visibility="collapsed")
            ea = c2.number_input(f"額{i}", value=int(exp["amount"]), key=f"fe_a_{i}", step=1000, label_visibility="collapsed")
            if c3.button("❌", key=f"fe_d_{i}"): 
                st.session_state.f_exp_list.pop(i)
                st.rerun()
            f_updated_exps.append({"name": en, "amount": ea})
        st.session_state.f_exp_list = f_updated_exps
        
        f_exp_total = sum(e["amount"] for e in f_updated_exps)
        st.metric("家族支出合計", f"¥{f_exp_total:,}", delta=f"-{f_exp_total:,}", delta_color="inverse")
        st.success(f"家族の残り予算: ¥{f_inc - f_exp_total:,}")

# --- 歴史ページ ---
with tab_h:
    st.title("📈 資産の歴史")
    if os.path.exists(HISTORY_FILE):
        h_df = pd.read_csv(HISTORY_FILE).sort_values("月")
        st.plotly_chart(px.line(h_df, x="月", y=["個人資産", "家族資産"], markers=True), use_container_width=True)
        st.dataframe(h_df.sort_values("月", ascending=False), hide_index=True, use_container_width=True)