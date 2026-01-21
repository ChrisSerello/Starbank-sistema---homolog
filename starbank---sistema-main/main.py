import streamlit as st
import pandas as pd
import psycopg2
import time
from datetime import date
from supabase import create_client

# ================= CONFIG PAGE =================
st.set_page_config(
    page_title="Starbank Vendas",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= SUPABASE =================
@st.cache_resource
def init_supabase():
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"]
    )

supabase = init_supabase()

# ================= DATABASE =================
def init_connection():
    try:
        return psycopg2.connect(**st.secrets["connections"]["postgresql"])
    except Exception as e:
        st.error(f"Erro conexão DB: {e}")
        return None

def run_query(query, params=None, fetch=False):
    conn = init_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            conn.commit()
    except Exception as e:
        st.error(f"Erro SQL: {e}")
    finally:
        conn.close()

def init_db():
    run_query("""
        CREATE TABLE IF NOT EXISTS vendas (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            data DATE NOT NULL,
            cliente TEXT,
            convenio TEXT,
            produto TEXT,
            valor NUMERIC(10,2)
        )
    """)

# ================= AUTH =================
def formatar_login(user):
    user = user.strip().lower()
    if "@" in user:
        return user if "@starbank" in user else None
    return f"{user.replace(' ', '.')}@starbank.com.br"

def login_supabase(email_input, password):
    email = formatar_login(email_input)
    if not email:
        return None, "Use email @starbank ou apenas seu nome"

    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return res.user, None
    except:
        return None, "Usuário ou senha inválidos"

def create_user_supabase(email_input, password):
    email = formatar_login(email_input)
    if not email:
        return "Apenas equipe Starbank"
    try:
        supabase.auth.sign_up({"email": email, "password": password})
        return "Usuário criado com sucesso"
    except:
        return "Usuário já existe ou senha inválida"

# ================= BUSINESS RULES =================
def calcular_comissao(total):
    if total >= 150000: return total * 0.015
    if total >= 101000: return total * 0.0125
    if total >= 80000:  return total * 0.01
    if total >= 50000:  return total * 0.005
    return 0.0

def definir_meta(total):
    for meta in [50000, 80000, 101000, 150000]:
        if total < meta:
            return meta
    return 200000

def nivel_usuario(total):
    if total >= 150000: return "DIAMANTE", "💎"
    if total >= 101000: return "PLATINA", "💠"
    if total >= 80000:  return "OURO", "🥇"
    if total >= 50000:  return "PRATA", "⛓️"
    return "BRONZE", "🥉"

# ================= DATA =================
def add_venda(username, data, cliente, convenio, produto, valor):
    nome = username.split("@")[0].replace(".", " ").title()
    run_query(
        """INSERT INTO vendas (username,data,cliente,convenio,produto,valor)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (nome, data, cliente, convenio, produto, valor)
    )

def delete_venda(venda_id):
    run_query("DELETE FROM vendas WHERE id=%s", (venda_id,))

def get_vendas_df(user=None):
    conn = init_connection()
    if not conn:
        return pd.DataFrame()

    if user and user != "Todos":
        nome = user.split("@")[0].replace(".", " ")
        query = "SELECT * FROM vendas WHERE username ILIKE %s"
        df = pd.read_sql(query, conn, params=(f"%{nome}%",))
    else:
        df = pd.read_sql("SELECT * FROM vendas", conn)

    conn.close()
    return df

def get_users():
    res = run_query("SELECT DISTINCT username FROM vendas", fetch=True)
    return [r[0] for r in res] if res else []

# ================= INIT =================
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ================= LOGIN =================
if not st.session_state.logged_in:
    st.title("STARBANK")
    tab1, tab2 = st.tabs(["Login", "Registrar"])

    with tab1:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            user, err = login_supabase(u, p)
            if user:
                st.session_state.logged_in = True
                st.session_state.email = user.email
                st.rerun()
            else:
                st.error(err)

    with tab2:
        nu = st.text_input("Nome")
        np = st.text_input("Senha", type="password")
        if st.button("Criar"):
            st.success(create_user_supabase(nu, np))

# ================= DASHBOARD =================
else:
    email = st.session_state.email
    nome = email.split("@")[0].replace(".", " ").title()

    st.sidebar.title(nome)

    with st.sidebar.form("nova_venda"):
        d = st.date_input("Data", date.today())
        c = st.text_input("Cliente")
        co = st.text_input("Convênio")
        p = st.selectbox("Produto", ["EMPRÉSTIMO", "CARTÃO", "BENEFÍCIO"])
        v = st.number_input("Valor", min_value=0.0)
        if st.form_submit_button("Salvar") and v > 0:
            add_venda(email, d, c, co, p, v)
            st.success("Venda salva")
            time.sleep(0.5)
            st.rerun()

    admins = ["christian", "maicon", "brunno", "fernanda", "nair"]
    filtro = email

    if any(a in email for a in admins):
        filtro = st.selectbox("Visão", ["Todos"] + get_users())

    df = get_vendas_df(filtro)
    total = df["valor"].sum() if not df.empty else 0

    meta = definir_meta(total)
    comissao = calcular_comissao(total)
    nivel, icone = nivel_usuario(total)

    st.metric("TOTAL", f"R$ {total:,.2f}")
    st.metric("COMISSÃO", f"R$ {comissao:,.2f}")
    st.metric("META", f"R$ {meta:,.2f}")

    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
        st.area_chart(df.groupby("data")["valor"].sum())
        st.dataframe(df, use_container_width=True)

        with st.expander("Excluir"):
            ids = df["id"].tolist()
            del_id = st.selectbox("ID", ids)
            if st.button("Excluir"):
                delete_venda(del_id)
                st.rerun()
