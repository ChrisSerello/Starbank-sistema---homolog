import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
from datetime import date, timedelta

#Config. da pagina
st.set_page_config(
    page_title="Starbank Vendas",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

#css cyber
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Inter:wght@300;400;600&display=swap');
        
        .stAppDeployButton { display: none; }
        
        header[data-testid="stHeader"] {
            background-color: transparent !important;
        }

        button[kind="header"] { color: #00d4ff !important; }
        [data-testid="collapsedControl"] { color: #00d4ff !important; }

        html, body, [class*="css"] { font-family: 'Rajdhani', sans-serif; }
        
        /* --- TICKER --- */
        .ticker-wrap {
            width: 100%; overflow: hidden; background-color: rgba(0, 0, 0, 0.6);
            border-bottom: 1px solid #00d4ff; border-top: 1px solid #00d4ff;
            padding: 10px 0; white-space: nowrap; box-sizing: border-box; margin-bottom: 20px;
        }
        .ticker { display: inline-block; padding-left: 100%; animation: ticker-anim 20s linear infinite; } 
        .ticker__item {
            display: inline-block; padding: 0 2rem; font-size: 1.2rem;
            color: #FFFFFF; font-weight: bold; text-shadow: 0 0 5px #00ff41;
        }
        @keyframes ticker-anim { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

        /* --- ANIMAÇÕES --- */
        @keyframes slideInUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .cyber-banner { animation: slideInUp 0.6s ease-out both; }
        .stProgress { animation: slideInUp 0.6s ease-out 0.2s both; }
        div[data-testid="stMetric"] { animation: slideInUp 0.6s ease-out 0.4s both; }
        .stChart, .stDataFrame { animation: slideInUp 0.8s ease-out 0.6s both; }

        /*BACKGROUND*/
        .stApp {
            background: linear-gradient(to bottom, #02010a, #090a1f);
            background-size: 200% 200%; animation: darkPulse 10s ease infinite;
        }
        @keyframes darkPulse { 0% {background-position: 0% 0%;} 50% {background-position: 0% 100%;} 100% {background-position: 0% 0%;} }
        
        [data-testid="stSidebar"] {
            background-color: rgba(10, 10, 20, 0.95);
            border-right: 1px solid rgba(0, 212, 255, 0.1);
            backdrop-filter: blur(10px);
        }

        /* --- CARDS 3D --- */
        div[data-testid="stMetric"] {
            background: rgba(5, 15, 30, 0.7);
            border: 1px solid rgba(0, 212, 255, 0.2);
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.05);
            backdrop-filter: blur(15px); border-radius: 12px; padding: 20px;
            transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.4s ease, border-color 0.4s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-5px);
            border-color: #00d4ff;
            box-shadow: 0 10px 25px rgba(0, 212, 255, 0.2);
            background: rgba(5, 15, 30, 0.9);
        }
        div[data-testid="stMetricLabel"] { color: #00d4ff !important; font-weight: 600; letter-spacing: 1px; }
        div[data-testid="stMetricValue"] { font-family: 'Rajdhani', sans-serif; font-weight: 700; color: white; text-shadow: 0 0 10px rgba(255,255,255,0.3); }
        
        .cyber-banner {
            padding: 20px; border-radius: 12px; background: rgba(10, 10, 30, 0.8);
            border: 1px solid; position: relative; overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        
        .stButton > button {
            background: transparent; border: 1px solid #00d4ff; color: #00d4ff;
            font-family: 'Rajdhani'; text-transform: uppercase; letter-spacing: 2px; transition: all 0.3s;
        }
        .stButton > button:hover {
            background: rgba(0, 212, 255, 0.2); box-shadow: 0 0 20px rgba(0, 212, 255, 0.4); transform: scale(1.02);
        }
    </style>
""", unsafe_allow_html=True)

#banco de dados
def init_connection():
    return sqlite3.connect('vendas.db', check_same_thread=False)

def run_query(query, params=None):
    conn = init_connection()
    with conn:
        if params:
            res = conn.execute(query, params)
        else:
            res = conn.execute(query)
        
        if query.strip().upper().startswith("SELECT"):
            return res.fetchall()
        return None

def init_db():
    conn = init_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    data TEXT,
                    cliente TEXT,
                    convenio TEXT,
                    produto TEXT,
                    valor REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY, 
                    password TEXT)''')
    try:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT")
        c.execute("UPDATE users SET role = 'operador' WHERE role IS NULL")
        conn.commit()
    except sqlite3.OperationalError: pass

    supervisores = ["Maicon Nascimento", "Brunno Leonard", "Fernanda Gomes", "Nair Oliveira"]
    senha_padrao = hashlib.sha256(str.encode("123456")).hexdigest()
    for chefe in supervisores:
        try:
            c.execute('INSERT OR IGNORE INTO users(username, password, role) VALUES (?,?,?)', 
                      (chefe, senha_padrao, 'admin'))
            c.execute('UPDATE users SET role = ? WHERE username = ?', ('admin', chefe))
        except Exception: pass
    conn.commit()
    conn.close()

#segurança
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generate_session_token(username):
    secret = "STARBANK_FIXED_UI_2026"
    return hashlib.sha256(str.encode(username + secret)).hexdigest()

def update_password(username, new_password):
    run_query("UPDATE users SET password = ? WHERE username = ?", (make_hashes(new_password), username))

# logica de metas e comissões
def calcular_comissao_tier(total):
    # A partir de 150k -> 1.50%
    if total >= 150000: return total * 0.0150 
    # A partir de 101k -> 1.25%
    elif total >= 101000: return total * 0.0125 
    # A partir de 80k -> 1.00%
    elif total >= 80000: return total * 0.0100 
    # A partir de 50k -> 0.50%
    elif total >= 50000: return total * 0.0050 
    else: return 0.0

def definir_meta_atual(total):
    #definhe qual barra o operador esta 
    if total < 50000: return 50000.00
    elif total < 80000: return 80000.00
    elif total < 101000: return 101000.00
    elif total < 150000: return 150000.00
    else: return 200000.00 # Meta simbólica "Sem Limites" para o gráfico não quebrar

def get_motivational_data(total):
    # de acordo com a tabela de comissão
    if total >= 150000: return "DIAMANTE (MAX)", "#b9f2ff", "LENDÁRIO! COMISSÃO MÁXIMA DE 1.5%", "💎"
    elif total >= 101000: return "PLATINA", "#E5E4E2", "EXCELENTE! COMISSÃO DE 1.25%", "💠"
    elif total >= 80000: return "OURO", "#FFD700", "MUITO BEM! COMISSÃO DE 1.00%", "🥇"
    elif total >= 50000: return "PRATA", "#C0C0C0", "COMISSÃO ATIVADA (0.50%)!", "⛓️"
    else: return "BRONZE", "#cd7f32", "Acelere para ativar a comissão nos 50k!", "🥉"

def get_streak(username):
    res = run_query("SELECT DISTINCT data FROM vendas WHERE username = ? ORDER BY data DESC", (username,))
    if not res: return 0
    return len(res)

def get_total_sales_count():
    res = run_query("SELECT COUNT(*) FROM vendas")
    return res[0][0] if res else 0

def get_global_ticker_data():
    res = run_query("SELECT username, valor, produto FROM vendas ORDER BY id DESC LIMIT 5")
    if not res: return ["💎 Sistema Starbank Online"]
    msgs = []
    for row in res:
        user_short = row[0].split()[0]
        msgs.append(f"⚡ LIVE: {user_short.upper()} VENDEU R$ {row[1]:,.2f} ({row[2]})")
    msgs.append("🚀 FOCO NA PRÓXIMA META!")
    return msgs

def login_user(username, password):
    return run_query("SELECT * FROM users WHERE username = ? AND password = ?", (username, make_hashes(password)))

def create_user(username, password, role='operador'):
    run_query("INSERT INTO users(username, password, role) VALUES (?, ?, ?)", (username, make_hashes(password), role))

def add_venda(username, data, cliente, convenio, produto, valor):
    run_query("INSERT INTO vendas(username, data, cliente, convenio, produto, valor) VALUES (?, ?, ?, ?, ?, ?)", 
              (username, str(data), cliente, convenio, produto, valor))

def delete_venda(venda_id):
    run_query("DELETE FROM vendas WHERE id = ?", (venda_id,))

def get_all_users():
    res = run_query("SELECT username FROM users")
    return [r[0] for r in res] if res else []

def get_vendas_df(target_user=None):
    conn = init_connection()
    query = "SELECT id, username, data, cliente, convenio, produto, valor FROM vendas"
    if target_user and target_user != "Todos":
        df = pd.read_sql(query + " WHERE username = ?", conn, params=(target_user,))
    else:
        df = pd.read_sql(query, conn)
    conn.close()
    return df

#iniciando login 
init_db()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

qp = st.query_params
if not st.session_state['logged_in'] and "user" in qp and "token" in qp:
    if qp["token"] == generate_session_token(qp["user"]):
        res = run_query("SELECT role FROM users WHERE username = ?", (qp["user"],))
        role = res[0][0] if res else 'operador'
        st.session_state['logged_in'] = True
        st.session_state['username'] = qp["user"]
        st.session_state['role'] = role

# --- TELA DE LOGIN ---
if not st.session_state['logged_in']:
    st.markdown("""
        <style>
            .stApp { background: linear-gradient(-45deg, #020024, #090979, #00d4ff, #7b1fa2); background-size: 400% 400%; animation: gradientBG 15s ease infinite; }
            @keyframes gradientBG { 0% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} 100% {background-position: 0% 50%;} }
            .holo-container {
                background: rgba(255, 255, 255, 0.05); border-radius: 20px; padding: 50px;
                backdrop-filter: blur(20px); border: 2px solid rgba(0, 212, 255, 0.3); box-shadow: 0 0 80px rgba(0, 212, 255, 0.2);
                text-align: center; position: relative; overflow: hidden;
            }
            .holo-container::before {
                content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
                background: linear-gradient(to bottom, transparent, rgba(0, 212, 255, 0.4), transparent);
                transform: rotate(45deg); animation: scanner 6s linear infinite; pointer-events: none;
            }
            @keyframes scanner { 0% {top: -200%;} 100% {top: 200%;} }
            div[data-testid="stTextInput"] input {
                background: transparent !important; border: none !important; border-bottom: 2px solid rgba(255,255,255,0.2) !important; color: white !important;
            }
            div[data-testid="stTextInput"] input:focus { border-bottom-color: #00d4ff !important; }
        </style>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="holo-container">', unsafe_allow_html=True)
        st.markdown('<h1 style="color:white; font-family: Rajdhani; letter-spacing: 3px;">STARBANK</h1>', unsafe_allow_html=True)
        st.markdown('<p style="color:#00d4ff;">/// Acesso Seguro v10.0 ///</p>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["ENTRAR", "REGISTRAR"])
        with tab1:
            u = st.text_input("ID OPERADOR", key="l_u")
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
                else: st.error("Acesso Negado")
        with tab2:
            nu = st.text_input("Novo Usuário", key="n_u")
            np = st.text_input("Nova Senha", type="password", key="n_p")
            if st.button("CRIAR"):
                try: create_user(nu, np); st.success("Criado! Faça login.")
                except: st.error("Usuário já existe")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # --- DASHBOARD LOGADO ---
    user = st.session_state['username']
    role = st.session_state['role']

    # TICKER (MODO SEMPRE VISÍVEL)
    # Removemos a verificação "if current > last". Agora ele carrega sempre.
    ticker_msgs = get_global_ticker_data()
    
    # Se a lista vier vazia (banco zerado), garante uma mensagem padrão
    if not ticker_msgs: ticker_msgs = ["💎 Sistema Starbank Online - Homologação"]
    
    ticker_html = f"""<div class="ticker-wrap"><div class="ticker">{' &nbsp;&nbsp;&nbsp;&nbsp; /// &nbsp;&nbsp;&nbsp;&nbsp; '.join([f'<div class="ticker__item">{m}</div>' for m in ticker_msgs])}</div></div>"""
    st.markdown(ticker_html, unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"<h2 style='color: #00d4ff;'>👤 {user.upper()}</h2>", unsafe_allow_html=True)
        st.caption(f"PERFIL: {role.upper()}")
        menu = st.radio("NAVEGAÇÃO", ["Painel de Controle", "Segurança / Senha"])
        st.divider()
        streak_count = get_streak(user)
        fire_color = "#FF4500" if streak_count > 0 else "#555"
        st.markdown(f"""<div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; border: 1px solid {fire_color}; margin-bottom: 20px;"><h3 style="margin:0; color: {fire_color}; text-align: center;">🔥 DIAS ATIVOS: {streak_count}</h3></div>""", unsafe_allow_html=True)
        if st.button("DESCONECTAR [X]"):
            st.session_state['logged_in'] = False
            st.query_params.clear()
            st.rerun()

    # --- MENU: SEGURANÇA ---
    if menu == "Segurança / Senha":
        st.title("🔐 Atualização de Credenciais")
        with st.form("senha_form"):
            s1 = st.text_input("Nova Senha", type="password")
            s2 = st.text_input("Confirmar Senha", type="password")
            if st.form_submit_button("Atualizar Chave"):
                if s1 == s2 and s1 != "":
                    update_password(user, s1)
                    st.success("Senha atualizada!")
                else: st.error("Senhas não coincidem.")

    # --- MENU: PAINEL DE CONTROLE ---
    elif menu == "Painel de Controle":
        with st.sidebar:
            st.divider()
            st.markdown("### 💠 NOVA TRANSAÇÃO")
            with st.form("venda"):
                d = st.date_input("DATA", date.today())
                c = st.text_input("CLIENTE")
                co = st.text_input("CONVÊNIO")
                p = st.selectbox("PRODUTO", ["EMPRÉSTIMO", "CARTÃO RMC", "BENEFICIO"])
                v = st.number_input("VALOR (R$)", min_value=0.0)
                if st.form_submit_button("PROCESSAR DADOS 🚀"):
                    add_venda(user, d, c, co, p, v)
                    st.toast("Salvo!", icon="💾")
                    time.sleep(0.5)
                    st.rerun()

        filtro = user
        if role == 'admin':
            col_admin, _ = st.columns([1, 3])
            with col_admin:
                op = ["Todos"] + get_all_users()
                sel = st.selectbox("VISÃO SUPERVISOR (ADMIN):", op)
                filtro = "Todos" if sel == "Todos" else sel

        df = get_vendas_df(filtro)
        
        # --- CÁLCULOS DINÂMICOS ---
        total = df['valor'].sum() if not df.empty else 0.0
        
        # Define a META VISUAL baseado no total vendido (Gamification)
        META_ATUAL = definir_meta_atual(total)
        
        comissao = calcular_comissao_tier(total)
        nivel, cor_nivel, msg, icone = get_motivational_data(total)

        # Banner
        st.markdown(f"""
            <div class="cyber-banner" style="border-color: {cor_nivel}; box-shadow: 0 0 20px {cor_nivel}40;">
                <h2 style="margin:0; color: white; letter-spacing: 2px;">{icone} STATUS: {filtro.upper()}</h2>
                <p style="margin:10px 0 0 0; color: {cor_nivel}; font-size: 1.3em; font-weight: bold; text-shadow: 0 0 10px {cor_nivel};">
                    NÍVEL: {nivel}
                </p>
                <p style="margin:0; color: #a0a0a0; font-style: italic;">/// {msg} ///</p>
            </div>
        """, unsafe_allow_html=True)

        #barra de progresso de acordo com a meta
        col_prog, col_meta = st.columns([3, 1])
        with col_prog:
            progresso_pct = min(total / META_ATUAL, 1.0)
            st.markdown(f"<br>Please **PRÓXIMO ALVO: R$ {META_ATUAL:,.2f} ({progresso_pct*100:.1f}%)**", unsafe_allow_html=True)
            st.progress(progresso_pct)
        with col_meta:
            st.markdown("<br>", unsafe_allow_html=True)
            if total >= 150000: st.markdown("🏆 **LENDÁRIO!**")
            elif total >= META_ATUAL: st.markdown("🚀 **SUBIU DE NÍVEL!**")

        if total >= META_ATUAL and filtro == user and total < 200000: st.balloons()

        st.markdown("<br>", unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("VOLUME TOTAL", f"R$ {total:,.2f}", delta="Processado")
        
        perc_atual = (comissao/total*100) if total > 0 else 0
        k2.metric("COMISSÃO APLICADA", f"R$ {comissao:,.2f}", delta=f"{perc_atual:.2f}%")
        
        # Mostra quanto falta para a PRÓXIMA meta da escada
        k3.metric("FALTA P/ PRÓX. NÍVEL", f"R$ {max(META_ATUAL-total, 0):,.2f}", delta="Pendente", delta_color="inverse")
        k4.metric("META ATUAL", f"R$ {META_ATUAL:,.2f}", delta="Alvo Dinâmico")

        st.divider()

        if not df.empty:
            c_chart, c_table = st.columns([1.5, 1])
            with c_chart:
                st.markdown("#### 📈 FLUXO TEMPORAL")
                df['data'] = pd.to_datetime(df['data'])
                chart_data = df.groupby("data")["valor"].sum()
                st.area_chart(chart_data, color=cor_nivel)
            
            with c_table:
                if role == 'admin' and filtro == "Todos":
                    st.markdown("#### 🏆 RANKING GERAL (EQUIPE)")
                    ranking = df.groupby('username')['valor'].sum().sort_values(ascending=False).reset_index()
                    st.dataframe(ranking.style.format({"valor": "R$ {:,.2f}"}), use_container_width=True, hide_index=True)
                else:
                    st.markdown("#### ⚡ TOP 5 VENDAS")
                    st.dataframe(df[['cliente', 'produto', 'valor']].sort_values(by='valor', ascending=False).head(5).style.format({"valor": "R$ {:,.2f}"}), use_container_width=True, hide_index=True)

            with st.expander("📂 ACESSAR BANCO DE DADOS COMPLETO"):
                st.dataframe(df.style.format({"valor": "R$ {:,.2f}"}), use_container_width=True)
                col_del, _ = st.columns([1, 3])
                with col_del:
                    lista = df.apply(lambda x: f"ID {x['id']} - {x['cliente']} ({x['username']})", axis=1)
                    sel = st.selectbox("SELECIONAR REGISTRO PARA EXPURGO:", lista)
                    if st.button("🗑️ CONFIRMAR EXPURGO"):
                        id_real = int(sel.split(" - ")[0].replace("ID ", ""))
                        delete_venda(id_real)
                        st.rerun()
        else:
            st.info("NENHUM DADO REGISTRADO NO PERÍODO.")