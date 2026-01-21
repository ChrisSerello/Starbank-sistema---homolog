import streamlit as st
import pandas as pd
import psycopg2
import hashlib
import time
from datetime import date

# Config. da pagina
st.set_page_config(
    page_title="Starbank Vendas",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS CYBER (MANTIDO) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Inter:wght@300;400;600&display=swap');
        .stAppDeployButton { display: none; }
        header[data-testid="stHeader"] { background-color: transparent !important; }
        html, body, [class*="css"] { font-family: 'Rajdhani', sans-serif; }
        .stApp { background: linear-gradient(-45deg, #020024, #090979, #00d4ff, #7b1fa2); background-size: 400% 400%; animation: gradientBG 15s ease infinite; }
        @keyframes gradientBG { 0% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} 100% {background-position: 0% 50%;} }
        .holo-container { background: rgba(255, 255, 255, 0.05); border-radius: 20px; padding: 50px; backdrop-filter: blur(20px); border: 2px solid rgba(0, 212, 255, 0.3); box-shadow: 0 0 80px rgba(0, 212, 255, 0.2); text-align: center; margin-top: 50px; }
        div[data-testid="stTextInput"] input { background: transparent !important; border: none !important; border-bottom: 2px solid rgba(255,255,255,0.2) !important; color: white !important; }
        .ticker-wrap { width: 100%; overflow: hidden; background-color: rgba(0, 0, 0, 0.6); border-y: 1px solid #00d4ff; padding: 10px 0; margin-bottom: 20px; }
        .ticker { display: inline-block; padding-left: 100%; animation: ticker-anim 30s linear infinite; } 
        .ticker__item { display: inline-block; padding: 0 2rem; font-size: 1.2rem; color: #FFFFFF; font-weight: bold; text-shadow: 0 0 5px #00ff41; }
        @keyframes ticker-anim { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }
        .cyber-banner { padding: 20px; border-radius: 12px; background: rgba(10, 10, 30, 0.8); border: 1px solid; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        div[data-testid="stMetric"] { background: rgba(5, 15, 30, 0.7); border: 1px solid rgba(0, 212, 255, 0.2); backdrop-filter: blur(15px); border-radius: 12px; padding: 20px; }
        div[data-testid="stMetricLabel"] { color: #00d4ff !important; font-weight: 600; }
        [data-testid="stSidebar"] { background-color: rgba(10, 10, 20, 0.95); border-right: 1px solid rgba(0, 212, 255, 0.1); }
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO SQL ROBUSTA (CORREÇÃO DE ERRO) ---
@st.cache_resource
def init_connection():
    try:
        # Pega as configs do Secrets
        db_config = st.secrets["connections"]["postgresql"]
        
        # Conecta explicitamente mapeando 'username' para 'user'
        # Isso corrige o erro silencioso que estava acontecendo
        return psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["username"], 
            password=db_config["password"]
        )
    except Exception as e:
        st.error(f"⚠️ ERRO CRÍTICO DE CONEXÃO: {e}")
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
            st.error(f"Erro ao executar comando SQL: {e}")
        finally:
            conn.close()
    return None

def init_db():
    # Tenta criar as tabelas. Se falhar, o erro vai aparecer na tela.
    run_query("""
        CREATE TABLE IF NOT EXISTS vendas (
            id SERIAL PRIMARY KEY,
            username TEXT,
            data DATE,
            cliente TEXT,
            convenio TEXT,
            produto TEXT,
            valor NUMERIC(10,2)
        );
    """)
    run_query("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            password TEXT,
            role TEXT
        );
    """)

# --- SEGURANÇA ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- FUNÇÕES ---
def login_user(username, password):
    # Verifica se a tabela existe antes de tentar logar
    return run_query("SELECT * FROM users WHERE username = %s AND password = %s", (username, make_hashes(password)))

def create_user(username, password, role='operador'):
    # Verifica duplicidade
    try:
        check = run_query("SELECT * FROM users WHERE username = %s", (username,))
        if check:
            return "❌ Usuário já existe!"
        else:
            run_query("INSERT INTO users(username, password, role) VALUES (%s, %s, %s)", (username, make_hashes(password), role))
            return "✅ Criado com sucesso! Agora vá na aba ENTRAR."
    except Exception as e:
        return f"Erro ao criar: {e}"

def calcular_comissao_tier(total):
    if total >= 150000: return total * 0.0150 
    elif total >= 101000: return total * 0.0125 
    elif total >= 80000: return total * 0.0100 
    elif total >= 50000: return total * 0.0050 
    else: return 0.0

def definir_meta_atual(total):
    if total < 50000: return 50000.00
    elif total < 80000: return 80000.00
    elif total < 101000: return 101000.00
    elif total < 150000: return 150000.00
    else: return 200000.00

def get_motivational_data(total):
    if total >= 150000: return "DIAMANTE (MAX)", "#b9f2ff", "LENDÁRIO! COMISSÃO MÁXIMA DE 1.5%", "💎"
    elif total >= 101000: return "PLATINA", "#E5E4E2", "EXCELENTE! COMISSÃO DE 1.25%", "💠"
    elif total >= 80000: return "OURO", "#FFD700", "MUITO BEM! COMISSÃO DE 1.00%", "🥇"
    elif total >= 50000: return "PRATA", "#C0C0C0", "COMISSÃO ATIVADA (0.50%)!", "⛓️"
    else: return "BRONZE", "#cd7f32", "Acelere para ativar a comissão nos 50k!", "🥉"

def get_streak(username):
    res = run_query("SELECT DISTINCT data FROM vendas WHERE username = %s ORDER BY data DESC", (username,))
    if not res: return 0
    return len(res)

def get_global_ticker_data():
    res = run_query("SELECT username, SUM(valor) as total FROM vendas GROUP BY username HAVING SUM(valor) >= 50000 ORDER BY total DESC")
    if not res: return ["🚀 A CORRIDA PELOS 50K ESTÁ ON! BORA VENDER!"]
    msgs = []
    for row in res:
        user_nome = row[0].split()[0].upper()
        total_user = float(row[1]) 
        if total_user >= 150000: msgs.append(f"💎 {user_nome} BATEU A META DE 150 MIL!")
        elif total_user >= 101000: msgs.append(f"💠 {user_nome} BATEU A META DE 101 MIL!")
        elif total_user >= 80000: msgs.append(f"🥇 {user_nome} BATEU A META DE 80 MIL!")
        elif total_user >= 50000: msgs.append(f"🥈 {user_nome} BATEU A META DE 50 MIL!")
    return msgs

def add_venda(username, data, cliente, convenio, produto, valor):
    run_query("INSERT INTO vendas(username, data, cliente, convenio, produto, valor) VALUES (%s, %s, %s, %s, %s, %s)", 
              (username, str(data), cliente, convenio, produto, valor))

def delete_venda(venda_id):
    run_query("DELETE FROM vendas WHERE id = %s", (venda_id,))

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
        conn.close()
        return df
    return pd.DataFrame()

# --- INICIALIZAÇÃO ---
init_db()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

if 'ultimo_nivel_comemorado' not in st.session_state:
    st.session_state['ultimo_nivel_comemorado'] = 0

# --- TELA DE LOGIN ---
if not st.session_state['logged_in']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="holo-container">', unsafe_allow_html=True)
        st.markdown('<h1 style="color:white; font-family: Rajdhani; letter-spacing: 3px;">STARBANK</h1>', unsafe_allow_html=True)
        st.markdown('<p style="color:#00d4ff;">/// Acesso SQL v17.0 (Correção) ///</p>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["ENTRAR", "REGISTRAR"])
        
        with tab1:
            u = st.text_input("Usuário", key="l_u", placeholder="Digite seu nome de usuário")
            p = st.text_input("Senha", type="password", key="l_p")
            if st.button("CONECTAR >>>", type="primary"):
                res = login_user(u, p)
                if res:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = u
                    st.session_state['role'] = res[0][2] if res[0][2] else 'operador'
                    st.rerun()
                else: 
                    st.error("Acesso Negado: Usuário ou senha incorretos (ou a tabela 'users' ainda está vazia).")
        
        with tab2:
            st.info("Crie seu acesso. Ficará salvo na tabela 'users'.")
            nu = st.text_input("Novo Usuário", key="n_u")
            np = st.text_input("Nova Senha", type="password", key="n_p")
            if st.button("CRIAR CONTA"):
                msg = create_user(nu, np)
                if "✅" in msg: st.success(msg)
                else: st.error(msg)
        
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # --- DASHBOARD ---
    user = st.session_state['username']
    role = st.session_state['role']

    # TICKER
    ticker_msgs = get_global_ticker_data()
    st.markdown(f"""<div class="ticker-wrap"><div class="ticker">{' &nbsp;&nbsp;&nbsp;&nbsp; /// &nbsp;&nbsp;&nbsp;&nbsp; '.join([f'<div class="ticker__item">{m}</div>' for m in ticker_msgs])}</div></div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f"<h2 style='color: #00d4ff;'>👤 {user.upper()}</h2>", unsafe_allow_html=True)
        st.caption(f"PERFIL: {role.upper()}")
        streak_count = get_streak(user)
        st.markdown(f"""<div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; border: 1px solid #FF4500; margin-bottom: 20px;"><h3 style="margin:0; color: #FF4500; text-align: center;">🔥 DIAS ATIVOS: {streak_count}</h3></div>""", unsafe_allow_html=True)
        
        st.divider()
        st.markdown("### 💠 NOVA TRANSAÇÃO")
        with st.form("venda"):
            d = st.date_input("DATA", date.today())
            c = st.text_input("CLIENTE")
            co = st.text_input("CONVÊNIO")
            p = st.selectbox("PRODUTO", ["EMPRÉSTIMO", "CARTÃO RMC", "BENEFICIO"])
            v = st.number_input("VALOR (R$)", min_value=0.0, value=None, placeholder="0.00")
            
            if st.form_submit_button("PROCESSAR DADOS 🚀"):
                val_final = v if v is not None else 0.0
                if val_final > 0:
                    add_venda(user, d, c, co, p, val_final)
                    st.toast("Salvo!", icon="💾")
                    time.sleep(0.5)
                    st.rerun()
                else: st.warning("Digite um valor válido!")
        
        if st.button("SAIR"):
            st.session_state['logged_in'] = False
            st.rerun()

    filtro = user
    if role == 'admin' or user.lower() in ["maicon", "brunno", "fernanda", "nair"]:
        col_admin, _ = st.columns([1, 3])
        with col_admin:
            op = ["Todos"] + get_all_users()
            sel = st.selectbox("VISÃO SUPERVISOR:", op)
            filtro = "Todos" if sel == "Todos" else sel

    df = get_vendas_df(filtro)
    
    total = df['valor'].sum() if not df.empty else 0.0
    META_ATUAL = definir_meta_atual(total)
    comissao = calcular_comissao_tier(total)
    nivel, cor_nivel, msg, icone = get_motivational_data(total)

    st.markdown(f"""
        <div class="cyber-banner" style="border-color: {cor_nivel}; box-shadow: 0 0 20px {cor_nivel}40;">
            <h2 style="margin:0; color: white; letter-spacing: 2px;">{icone} STATUS: {filtro.upper()}</h2>
            <p style="margin:10px 0 0 0; color: {cor_nivel}; font-size: 1.3em; font-weight: bold; text-shadow: 0 0 10px {cor_nivel};">
                NÍVEL: {nivel}
            </p>
            <p style="margin:0; color: #a0a0a0; font-style: italic;">/// {msg} ///</p>
        </div>
    """, unsafe_allow_html=True)

    col_prog, col_meta = st.columns([3, 1])
    with col_prog:
        progresso_pct = min(total / META_ATUAL, 1.0)
        st.markdown(f"<br>Please **PRÓXIMO ALVO: R$ {META_ATUAL:,.2f} ({progresso_pct*100:.1f}%)**", unsafe_allow_html=True)
        st.progress(progresso_pct)

    if filtro == user:
        novo_nivel = 0
        if total >= 150000: novo_nivel = 150000
        elif total >= 101000: novo_nivel = 101000
        elif total >= 80000: novo_nivel = 80000
        elif total >= 50000: novo_nivel = 50000
        if novo_nivel > st.session_state['ultimo_nivel_comemorado']:
            st.balloons()
            st.toast(f"PARABÉNS! META DE {novo_nivel/1000:.0f}K BATIDA!", icon="🎉")
            st.session_state['ultimo_nivel_comemorado'] = novo_nivel

    st.markdown("<br>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("VOLUME TOTAL", f"R$ {total:,.2f}", delta="Processado")
    k2.metric("COMISSÃO", f"R$ {comissao:,.2f}", delta=f"{(comissao/total*100) if total>0 else 0:.2f}%")
    k3.metric("FALTA", f"R$ {max(META_ATUAL-total, 0):,.2f}", delta_color="inverse")
    k4.metric("META ATUAL", f"R$ {META_ATUAL:,.2f}")

    st.divider()

    if not df.empty:
        c_chart, c_table = st.columns([1.5, 1])
        with c_chart:
            st.markdown("#### 📈 FLUXO")
            df['data'] = pd.to_datetime(df['data'])
            st.area_chart(df.groupby("data")["valor"].sum(), color=cor_nivel)
        with c_table:
            st.markdown("#### ⚡ TOP VENDAS")
            st.dataframe(df[['cliente', 'produto', 'valor']].sort_values(by='valor', ascending=False).head(5).style.format({"valor": "R$ {:,.2f}"}), use_container_width=True, hide_index=True)

        with st.expander("📂 ACESSAR BANCO DE DADOS COMPLETO"):
            st.dataframe(df.style.format({"valor": "R$ {:,.2f}"}), use_container_width=True)
            col_del, _ = st.columns([1, 3])
            with col_del:
                lista = df.apply(lambda x: f"ID {x['id']} - {x['cliente']}", axis=1)
                sel = st.selectbox("EXCLUIR:", lista)
                if st.button("🗑️ CONFIRMAR"):
                    id_real = int(sel.split(" - ")[0].replace("ID ", ""))
                    delete_venda(id_real)
                    st.rerun()
    else:
        st.info("NENHUM DADO REGISTRADO.")