import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. 資料庫連線與初始化 ---
DB_FILE = 'badminton.db'

def init_db():
    """初始化資料庫，建立所需表格"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 建立學生表 (含剩餘堂數)
    c.execute('''CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT,
                    balance INTEGER DEFAULT 0
                )''')
    
    # 建立教練表
    c.execute('''CREATE TABLE IF NOT EXISTS coaches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    specialty TEXT
                )''')
    
    # 建立交易/上課紀錄表 (Log)
    # type: 'TOPUP' (儲值), 'CLASS' (上課)
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    student_id INTEGER,
                    coach_id INTEGER,
                    change_amount INTEGER,
                    note TEXT,
                    FOREIGN KEY(student_id) REFERENCES students(id)
                )''')
    conn.commit()
    conn.close()

# 執行初始化
init_db()

# --- 2. 資料庫操作函數 ---

def add_student(name, phone):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO students (name, phone, balance) VALUES (?, ?, 0)', (name, phone))
    conn.commit()
    conn.close()

def add_coach(name, specialty):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO coaches (name, specialty) VALUES (?, ?)', (name, specialty))
    conn.commit()
    conn.close()

def update_balance(student_id, amount, note, coach_id=None):
    """
    核心功能：更新餘額並寫入 Log
    amount: 正數代表購買，負數代表扣課
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. 更新學生餘額
    c.execute('UPDATE students SET balance = balance + ? WHERE id = ?', (amount, student_id))
    
    # 2. 寫入流水帳
    c.execute('''INSERT INTO logs (timestamp, student_id, coach_id, change_amount, note) 
                 VALUES (?, ?, ?, ?, ?)''', 
                 (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), student_id, coach_id, amount, note))
    
    conn.commit()
    conn.close()

def get_data(table_name):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

# --- 3. Streamlit 介面設計 ---

st.set_page_config(page_title="🏓桌球教練派課系統", layout="wide")
st.title("🏓桌球教練派課管理系統")

# 側邊欄導航
menu = ["派課與點名 (扣課)", "學生管理 (儲值)", "教練管理", "歷史紀錄"]
choice = st.sidebar.selectbox("功能選單", menu)

# --- 功能 A: 派課與點名 (最常用的功能) ---
if choice == "派課與點名 (扣課)":
    st.subheader("📅 教練排課 / 學生簽到")
    
    # 讀取資料供選單使用
    students = get_data('students')
    coaches = get_data('coaches')
    
    if not students.empty and not coaches.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # 建立 ID 到 Name 的對照選單
            student_list = dict(zip(students['id'], students['name'] + " (餘額: " + students['balance'].astype(str) + ")"))
            selected_student_id = st.selectbox("選擇學生", options=list(student_list.keys()), format_func=lambda x: student_list[x])
        
        with col2:
            coach_list = dict(zip(coaches['id'], coaches['name']))
            selected_coach_id = st.selectbox("指定教練", options=list(coach_list.keys()), format_func=lambda x: coach_list[x])
        
        note = st.text_input("備註 (例如：場地 A, 基礎訓練)")
        
        if st.button("確認扣課 (消耗 1 堂)", type="primary"):
            # 檢查餘額
            current_balance = students[students['id'] == selected_student_id]['balance'].values[0]
            if current_balance > 0:
                update_balance(selected_student_id, -1, note, coach_id=selected_coach_id)
                st.success(f"已完成！學生餘額剩餘 {current_balance - 1} 堂")
            else:
                st.error("❌ 該學生餘額不足，請先儲值！")
    else:
        st.warning("請先至「學生管理」與「教練管理」建立資料。")

# --- 功能 B: 學生管理 (儲值) ---
elif choice == "學生管理 (儲值)":
    st.subheader("👥 學生列表與儲值")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### 新增學生")
        new_name = st.text_input("學生姓名")
        new_phone = st.text_input("電話")
        if st.button("新增學生"):
            add_student(new_name, new_phone)
            st.success(f"已新增 {new_name}")
            st.rerun()
            
        st.markdown("---")
        st.markdown("#### 課程儲值")
        students = get_data('students')
        if not students.empty:
            student_list = dict(zip(students['id'], students['name']))
            topup_id = st.selectbox("選擇儲值學生", options=list(student_list.keys()), format_func=lambda x: student_list[x])
            amount = st.number_input("購買堂數", min_value=1, value=10)
            if st.button("確認儲值"):
                update_balance(topup_id, amount, "學生購買課程")
                st.success("儲值成功！")
                st.rerun()

    with col2:
        st.markdown("#### 目前學生清單")
        st.dataframe(get_data('students'), use_container_width=True)

# --- 功能 C: 教練管理 ---
elif choice == "教練管理":
    st.subheader("🧢 教練團隊")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        c_name = st.text_input("教練姓名")
        c_spec = st.text_input("專長 (例如：雙打戰術)")
        if st.button("新增教練"):
            add_coach(c_name, c_spec)
            st.success("教練已新增")
            st.rerun()
            
    with col2:
        st.dataframe(get_data('coaches'), use_container_width=True)

# --- 功能 D: 歷史紀錄 ---
elif choice == "歷史紀錄":
    st.subheader("📜 所有的上課與交易紀錄")
    
    # 這裡做一個 SQL Join 讓表格顯示名字而不是 ID
    conn = sqlite3.connect(DB_FILE)
    query = """
        SELECT logs.timestamp, students.name as 學生, coaches.name as 教練, logs.change_amount as 異動, logs.note as 備註
        FROM logs
        LEFT JOIN students ON logs.student_id = students.id
        LEFT JOIN coaches ON logs.coach_id = coaches.id
        ORDER BY logs.timestamp DESC
    """
    df_logs = pd.read_sql_query(query, conn)
    conn.close()
    
    st.dataframe(df_logs, use_container_width=True)