import streamlit as st
import pandas as pd
import psycopg2
import hashlib
import time
import urllib.parse # Necessário para corrigir o erro da senha com @
from datetime import date, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Starbank Vendas",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS V15 RESTAURADO (FUNDO AZUL/ROXO ANIMADO) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Inter:wght@300;400;600&display=swap');
        .stAppDeployButton { display: none; }
        header[data-testid="stHeader"] { background-color: transparent !important; }
        button[kind="header"] { color: #00d4ff !important; }
        [data-testid="collapsedControl"] { color: #00d4ff !important; }
        html, body, [class*="css"] { font-family: 'Rajdhani', sans-serif; }

        /* FUNDO ANIMADO */
        .stApp {
            background: linear-gradient(-45deg, #020024, #090979, #00d4ff, #7b1fa2);
            background-size: 400% 400%;
            animation: gradientBG 15s ease infinite;
        }
        @keyframes gradientBG {
            0% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} 100% {background-position: 0% 50%;}
        }
        
        /* LOGIN HOLOGRÁFICO */
        .holo-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 50px;
            backdrop-filter: blur(20px);
            border: 2px solid rgba(0, 212, 255, 0.3);
            box-shadow: 0 0 80px rgba(0, 212, 255, 0.2);
            text-align: center;
            position: relative;
            overflow: hidden;
            margin-top: 50px;
        }
        .holo-container::before {
            content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
            background: linear-gradient(to bottom, transparent, rgba(0, 212, 255, 0.4), transparent);
            transform: rotate(45deg); animation: scanner 6s linear infinite; pointer-events: none;
        }
        @keyframes scanner { 0% {top: -200%;} 100% {top: 200%;} }

        div[data-testid="stTextInput"] input {
            background: transparent !important; border: none !important;
            border-bottom: 2px solid rgba(255,255,255,0.2) !important; color: white !important;
        }
        
        /* TICKER */
        .ticker-wrap { width: 100%; overflow: hidden; background-color: rgba(0, 0, 0, 0.6); border-y: 1px solid #00d4ff; padding: 10px 0; margin-bottom: 20px; }
        .ticker { display: inline-block; padding-left: 100%; animation: ticker-anim 30s linear infinite; } 
        .ticker__item { display: inline-block; padding: 0 2rem; font-size: 1.2rem; color: #FFFFFF; font-weight: bold; text-shadow: 0 0 5px #00ff41; }
        @keyframes ticker-anim { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

        /* CARDS */
        .cyber-banner { padding: 20px; border-radius: 12px; background: rgba(10, 10, 30, 0.8); border: 1px solid; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        div[data-testid="stMetric"] { background: rgba(5, 15, 30, 0.7); border: 1px solid rgba(0, 212, 255, 0.2); backdrop-filter: blur(15px); border-radius: 12px; padding: 20px; }
        div[data-testid="stMetricLabel"] { color: #00d4ff !important; font-weight: 600; }
        [data-testid="stSidebar"] { background-color: rgba(10, 10, 20, 0.95); border-right: 1px solid rgba(0, 212, 255, 0.1); }
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO DB (CORREÇÃO DE SENHA COM @) ---
@st.cache_resource
def init_connection():
    try:
        s = st.secrets["connections"]["postgresql"]
        
        # AQUI ESTÁ A CORREÇÃO:
        # Codificamos a senha para que o símbolo '@' não quebre o link
        password_encoded = urllib.parse.quote_plus(s['password'])
        
        # Montamos o link usando a senha codificada
        dsn = f"postgresql://{s['username']}:{password_encoded}@{s['host']}:{s['port']}/{s['database']}?sslmode=require"
        
        return psycopg2.connect(dsn)
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

def run_query(query, params=None):
    conn = init_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                if query.strip().upper().startswith("SELECT"): return cur.fetchall()
        except Exception as e:
            st.error(f"Erro SQL: {e}")
        finally:
            conn.close()
    return None

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generate_session_token(username):
    secret = "STARBANK_FIXED_UI_2026"
    return hashlib.sha256(str.encode(username + secret)).hexdigest()

# --- LÓGICA DE NEGÓCIO ---

def get_total_sales_count():
    try:
        res = run_query("SELECT COUNT(*) FROM vendas")
        return res[0][0] if res else 0
    except: return 0

def get_streak(username):
    res = run_query("SELECT DISTINCT data FROM vendas WHERE username = %s ORDER BY data DESC", (username,))
    if not res: return 0
    dates = [row[0] for row in res]
    today = date.today()
    streak = 0
    check_date = today
    if today not in dates:
        check_date = today - timedelta(days=1)
        if check_date not in dates: return 0
    while True:
        if check_date in dates:
            streak += 1
            check_date -= timedelta(days=1)
        else: break
    return streak

def get_global_ticker_data():
    try:
        res = run_query("SELECT username, valor, produto FROM vendas ORDER BY id DESC LIMIT 5")
        if not res: return ["💎 Sistema Starbank Online"]
        msgs = []
        for row in res:
            user_short = row[0].split()[0]
            val = float(row[1])
            msgs.append(f"⚡ LIVE: {user_short.upper()} VENDEU R$ {val:,.2f} ({row[2]})")
        msgs.append("🚀 FOCO NA META: R$ 50k")
        return msgs
    except: return ["🚀 INICIANDO SISTEMA..."]

# --- FUNÇÕES BÁSICAS ---
def login_user(username, password):
    return run_query("SELECT * FROM users WHERE username = %s AND password = %s", (username, make_hashes(password)))

def get_user_role(username):
    res = run_query("SELECT role FROM users WHERE username = %s", (username,))
    return res[0][0] if res else 'operador'

def create_user(username, password, role='operador'):
    check = run_query("SELECT * FROM users WHERE username = %s", (username,))
    if check:
        st.error("❌ Usuário já existe!")
    else:
        run_query("INSERT INTO users(username, password, role) VALUES (%s, %s, %s)", (username, make_hashes(password), role))
        st.success("✅ Criado com sucesso! Faça login.")

def add_venda(username, data, cliente, convenio, produto, valor):
    run_query("INSERT INTO vendas(username, data, cliente, convenio, produto, valor) VALUES (%s, %s, %s, %s, %s, %s)", (username, data, cliente, convenio, produto, valor))

def get_all_users():
    res = run_query("SELECT username FROM users")
    return [r[0] for r in res] if res else []

def get_vendas_df(target_user=None):
    conn = init_connection()
    if conn:
        query = "SELECT id, username, data, cliente, convenio, produto, valor FROM vendas"
        if target_user and target_user != "Todos":
            df = pd.read_sql(query + " WHERE username = %s", conn, params=(target_user,))
        else:
            df = pd.read_sql(query, conn)
        return df
    return pd.DataFrame()

def delete_venda(venda_id):
    run_query("DELETE FROM vendas WHERE id = %s", (venda_id,))

def get_motivational_data(total, meta):
    if meta == 0: percent = 0 
    else: percent = total / meta
    if percent < 0.2: return "BRONZE", "#cd7f32", "Início de jornada. Foco total!", "🥉"
    elif percent < 0.5: return "PRATA", "#C0C0C0", "Ritmo consistente. Continue!", "⛓️"
    elif percent < 0.8: return "OURO", "#FFD700", "Alta performance! A meta está próxima!", "🥇"
    elif percent < 1.0: return "PLATINA", "#E5E4E2", "Excelência pura! Quase lá!", "💠"
    else: return "DIAMANTE", "#b9f2ff", "LENDÁRIO! Você zerou o jogo!", "💎"

def init_db():
    try:
        run_query("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT);")
        run_query("CREATE TABLE IF NOT EXISTS vendas (id SERIAL PRIMARY KEY, username TEXT, data DATE, cliente TEXT, convenio TEXT, produto TEXT, valor NUMERIC(10,2));")
    except: pass

init_db()

# --- SESSÃO ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

qp = st.query_params
if not st.session_state['logged_in'] and "user" in qp and "token" in qp:
    if qp["token"] == generate_session_token(qp["user"]):
        st.session_state['logged_in'] = True
        st.session_state['username'] = qp["user"]
        st.session_state['role'] = get_user_role(qp["user"])

# ==================================================
# TELA DE LOGIN
# ==================================================
if not st.session_state['logged_in']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="holo-container">', unsafe_allow_html=True)
        st.markdown('<h1 style="color:white; font-family: Rajdhani; letter-spacing: 3px;">STARBANK</h1>', unsafe_allow_html=True)
        st.markdown('<p style="color:#00d4ff;">/// Acesso Seguro v19.1 ///</p>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["ENTRAR", "REGISTRAR"])
        with tab1:
            u = st.text_input("NOME DO OPERADOR", key="l_u")
            p = st.text_input("CHAVE DE ACESSO", type="password", key="l_p")
            if st.button("INICIAR CONEXÃO >>>", type="primary"):
                res = login_user(u, p)
                if res:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = u
                    st.session_state['role'] = res[0][2] if res[0][2] else 'operador'
                    st.query_params["user"] = u
                    st.query_params["token"] = generate_session_token(u)
                    st.rerun()
                else: st.error("Acesso Negado: Usuário ou Senha incorretos.")
        with tab2:
            st.info("O acesso será criado no Banco de Dados.")
            nu = st.text_input("Novo ID", key="n_u")
            np = st.text_input("Nova Senha", type="password", key="n_p")
            if st.button("CRIAR"):
                if nu and np:
                    create_user(nu, np)
                else:
                    st.warning("Preencha todos os campos")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # ==================================================
    # DASHBOARD
    # ==================================================
    user = st.session_state['username']
    role = st.session_state.get('role', 'operador')

    # TICKER FIXO
    ticker_msgs = get_global_ticker_data()
    ticker_html = f"""
    <div class="ticker-wrap">
        <div class="ticker">
            {' &nbsp;&nbsp;&nbsp;&nbsp; /// &nbsp;&nbsp;&nbsp;&nbsp; '.join([f'<div class="ticker__item">{m}</div>' for m in ticker_msgs])}
        </div>
    </div>
    """
    st.markdown(ticker_html, unsafe_allow_html=True)

    # SIDEBAR
    streak_count = get_streak(user)
    with st.sidebar:
        st.markdown(f"<h2 style='color: #00d4ff;'>👤 {user.upper()}</h2>", unsafe_allow_html=True)
        fire_color = "#FF4500" if streak_count > 0 else "#555"
        st.markdown(f"""
            <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; border: 1px solid {fire_color}; margin-bottom: 20px;">
                <h3 style="margin:0; color: {fire_color}; text-align: center;">🔥 OFENSIVA: {streak_count} DIAS</h3>
                <p style="margin:0; font-size: 0.8em; color: #aaa; text-align: center;">Mantenha a chama!</p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("DESCONECTAR [X]"):
            st.session_state['logged_in'] = False; st.query_params.clear(); st.rerun()
        st.divider()
        st.markdown("### 💠 NOVA TRANSAÇÃO")
        with st.form("venda"):
            d = st.date_input("DATA", date.today())
            c = st.text_input("CLIENTE")
            co = st.text_input("CONVÊNIO")
            p = st.selectbox("PRODUTO", ["EMPRÉSTIMO", "CARTÃO RMC", "BENEFICIO"])
            v = st.number_input("VALOR (R$)", min_value=0.0)
            if st.form_submit_button("PROCESSAR DADOS 🚀"):
                if v > 0:
                    add_venda(user, d, c, co, p, v)
                    st.toast("Transação registrada!", icon="💾")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Valor inválido")

    # ÁREA PRINCIPAL
    filtro = user
    admins = ["Maicon Nascimento", "Brunno Leonard", "Fernanda Gomes", "Christian Serello"]
    if role == 'admin' or user in admins:
        op = ["Todos"] + get_all_users()
        sel = st.selectbox("VISÃO GLOBAL (ADMIN):", op)
        filtro = "Todos" if sel == "Todos" else sel

    df = get_vendas_df(filtro)
    META = 50000.00
    total = df['valor'].sum() if not df.empty else 0.0
    nivel, cor_nivel, msg, icone = get_motivational_data(total, META)

    st.markdown(f"""
        <div class="cyber-banner" style="border-color: {cor_nivel}; box-shadow: 0 0 20px {cor_nivel}40;">
            <h2 style="margin:0; color: white; letter-spacing: 2px;">{icone} STATUS DO OPERADOR: {user.upper()}</h2>
            <p style="margin:10px 0 0 0; color: {cor_nivel}; font-size: 1.3em; font-weight: bold; text-shadow: 0 0 10px {cor_nivel};">
                NÍVEL ATUAL: {nivel}
            </p>
            <p style="margin:0; color: #a0a0a0; font-style: italic;">/// {msg} ///</p>
        </div>
    """, unsafe_allow_html=True)

    col_prog, col_meta = st.columns([3, 1])
    with col_prog:
        progresso_pct = min(total / META, 1.0)
        st.markdown(f"<br>Please **PROGRESSO DA MISSÃO ({progresso_pct*100:.1f}%)**", unsafe_allow_html=True)
        st.progress(progresso_pct)
    with col_meta:
        st.markdown("<br>", unsafe_allow_html=True)
        if total >= META: st.markdown("🏆 **OBJETIVO ALCANÇADO!**")
    if total >= META: st.balloons()

    st.markdown("<br>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("VOLUME TOTAL", f"R$ {total:,.2f}", delta="Processado")
    k2.metric("COMISSÃO ESTIMADA", f"R$ {total*0.01:,.2f}", delta="Crédito")
    k3.metric("ALVO RESTANTE", f"R$ {max(META-total, 0):,.2f}", delta="Pendente", delta_color="inverse")
    k4.metric("META MENSAL", f"R$ {META:,.2f}", delta="Fixo")

    st.divider()

    if not df.empty:
        c_chart, c_table = st.columns([1.2, 1])
        with c_chart:
            st.markdown("#### 📈 FLUXO TEMPORAL")
            df['data'] = pd.to_datetime(df['data'])
            st.area_chart(df.groupby("data")["valor"].sum(), color=cor_nivel)
        with c_table:
            st.markdown("#### 🏆 TOP OPERAÇÕES")
            st.dataframe(df[['cliente', 'produto', 'valor']].sort_values(by='valor', ascending=False).head(5), use_container_width=True, hide_index=True)

        with st.expander("📂 ACESSAR BANCO DE DADOS COMPLETO"):
            st.dataframe(df.style.format({"valor": "R$ {:,.2f}"}), use_container_width=True)
            col_del, _ = st.columns([1, 3])
            with col_del:
                lista = df.apply(lambda x: f"ID {x['id']} - {x['cliente']}", axis=1)
                sel = st.selectbox("SELECIONAR REGISTRO PARA EXPURGO:", lista)
                if st.button("🗑️ CONFIRMAR EXPURGO"):
                    id_real = int(sel.split(" - ")[0].replace("ID ", ""))
                    delete_venda(id_real)
                    st.rerun()
    else:
        st.info("NENHUM DADO REGISTRADO NO PERÍODO.")