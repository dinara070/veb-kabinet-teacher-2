import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
import io
import altair as alt
import re

# --- КОНФІГУРАЦІЯ СТОРІНКИ ---
st.set_page_config(page_title="Veb kabinet", layout="wide", page_icon="🎓")

# --- ЛОГІКА ПЕРЕМИКАННЯ ТЕМИ ---
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

def toggle_theme():
    st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'

# --- CSS СТИЛІ ---
dark_css = """
<style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #262730; }
    h1, h2, h3, h4, h5, h6, p, li, span, label, .stMarkdown { color: #FFFFFF !important; }
    .stTextInput > div > div, .stSelectbox > div > div, .stTextArea > div > div, .stDateInput > div > div, .stNumberInput > div > div {
        background-color: #41444C !important; color: #FFFFFF !important;
    }
    input, textarea { color: #FFFFFF !important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] { color: #FFFFFF !important; }
    .streamlit-expanderHeader { background-color: #262730 !important; color: #FFFFFF !important; }
    button { color: #FFFFFF !important; }
</style>
"""

light_css = """
<style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    [data-testid="stSidebar"] { background-color: #F0F2F6; }
    h1, h2, h3, h4, h5, h6, p, li, span, label, .stMarkdown { color: #000000 !important; }
    .stTextInput > div > div, .stSelectbox > div > div, .stTextArea > div > div, .stDateInput > div > div, .stNumberInput > div > div {
        background-color: #FFFFFF !important; color: #000000 !important; border: 1px solid #D3D3D3;
    }
    input, textarea { color: #000000 !important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] { color: #000000 !important; }
    .streamlit-expanderHeader { background-color: #F0F2F6 !important; color: #000000 !important; }
    button { color: #000000 !important; }
</style>
"""

if st.session_state.theme == 'dark':
    st.markdown(dark_css, unsafe_allow_html=True)
else:
    st.markdown(light_css, unsafe_allow_html=True)

# --- КОНСТАНТИ ---
SUBJECTS_LIST = ["Філософія", "Математичний аналіз", "Програмування", "Фізика", "Алгебра і теорія чисел"]
GROUPS_DATA = {"1СОМ": ["Алексєєнко Анна Олександрівна"], "1СОІ": ["Лисенко Тимофій Сергійович"]}
TEACHER_LEVEL = ['teacher', 'admin']

# --- BACKEND ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_connection():
    return sqlite3.connect('university_v22.db', check_same_thread=False)

def init_db():
    conn = create_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT, role TEXT, full_name TEXT, group_link TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, group_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS grades(id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, group_name TEXT, subject TEXT, type_of_work TEXT, grade INTEGER, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS exam_sheets(id INTEGER PRIMARY KEY AUTOINCREMENT, sheet_number TEXT, group_name TEXT, subject TEXT, control_type TEXT, exam_date TEXT, examiner TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS retakes(id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, group_name TEXT, subject TEXT, reason TEXT, added_by TEXT, date_added TEXT)''')
    
    # Створення адміна за замовчуванням
    c.execute('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)', ('admin', make_hashes('admin'), 'admin', 'Адміністратор', 'Staff'))
    conn.commit()
    return conn

# --- ФУНКЦІЇ СТОРІНОК (VIEWS) ---

def login_register_page():
    st.header("🔐 Вхід до системи")
    username = st.text_input("Логін")
    password = st.text_input("Пароль", type='password')
    
    if st.button("Увійти"):
        conn = create_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, make_hashes(password)))
        user = c.fetchone()
        if user:
            st.session_state['logged_in'] = True
            st.session_state['username'] = user[0]
            st.session_state['role'] = user[2]
            st.session_state['full_name'] = user[3]
            st.success(f"Вітаємо, {user[3]}!")
            st.rerun()
        else:
            st.error("Невірний логін або пароль")

def retakes_management_view():
    st.subheader("🔄 Керування відомостями на перездачу")
    conn = create_connection()
    col1, col2 = st.columns(2)
    with col1:
        group_sel = st.selectbox("Оберіть групу", list(GROUPS_DATA.keys()), key="ret_g")
    with col2:
        subject_sel = st.selectbox("Оберіть предмет", SUBJECTS_LIST, key="ret_s")

    sheet = pd.read_sql_query(f"SELECT * FROM exam_sheets WHERE group_name='{group_sel}' AND subject='{subject_sel}'", conn)

    if sheet.empty:
        st.warning(f"⚠️ Відомість на перездачу для групи {group_sel} з предмета '{subject_sel}' ще не відкрита адміністрацією.")
    else:
        st.success(f"✅ Відомість №{sheet.iloc[0]['sheet_number']} активна.")
        with st.expander("➕ Відправити студента на перездачу"):
            st_df = pd.read_sql(f"SELECT full_name FROM students WHERE group_name='{group_sel}'", conn)
            sel_st = st.selectbox("Оберіть студента", st_df['full_name'].tolist() if not st_df.empty else [])
            reason = st.text_input("Причина (напр. 'незадовільно')")
            if st.button("Підтвердити"):
                conn.execute("INSERT INTO retakes (student_name, group_name, subject, reason, added_by, date_added) VALUES (?,?,?,?,?,?)",
                             (sel_st, group_sel, subject_sel, reason, st.session_state['full_name'], str(datetime.now().date())))
                conn.commit()
                st.success("Додано!")
                st.rerun()

    st.divider()
    ret_list = pd.read_sql(f"SELECT id, student_name, reason FROM retakes WHERE group_name='{group_sel}' AND subject='{subject_sel}'", conn)
    if not ret_list.empty:
        for i, row in ret_list.iterrows():
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.write(f"👤 {row['student_name']}")
            c2.write(f"📝 {row['reason']}")
            if c3.button("Видалити 🗑️", key=f"del_{row['id']}"):
                conn.execute(f"DELETE FROM retakes WHERE id={row['id']}")
                conn.commit()
                st.rerun()

def reports_view():
    st.title("📊 Звіти та Пошук")
    t1, t2, t3, t4 = st.tabs(["📋 Відомість", "🎓 Картка Студента", "📈 Зведена", "🔄 Перездачі (Сесія)"])
    conn = create_connection()
    with t1:
        grp = st.selectbox("Група", list(GROUPS_DATA.keys()), key="r_g")
        subj = st.selectbox("Предмет", SUBJECTS_LIST, key="r_s")
        raw = pd.read_sql(f"SELECT student_name, type_of_work, grade FROM grades WHERE group_name='{grp}' AND subject='{subj}'", conn)
        if not raw.empty:
            st.dataframe(raw.pivot_table(index='student_name', columns='type_of_work', values='grade').fillna(0))
    with t4:
        retakes_management_view()

# --- ГОЛОВНА ЛОГІКА ---

def main():
    init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_register_page()
    else:
        st.sidebar.title(f"👤 {st.session_state.get('full_name', 'Користувач')}")
        if st.sidebar.button("Тема 🌓"):
            toggle_theme()
            st.rerun()

        menu = {
            "🏠 Головна панель": lambda: st.write("Вітаємо в системі!"),
            "📊 Звіти та Пошук": reports_view,
            "📅 Розклад занять": lambda: st.info("Розділ у розробці"),
        }
        
        selection = st.sidebar.radio("Навігація", list(menu.keys()))
        menu[selection]()

        st.sidebar.divider()
        if st.sidebar.button("Вийти 🚪"):
            st.session_state['logged_in'] = False
            st.rerun()

if __name__ == '__main__':
    main()
