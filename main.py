import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO GERAL E SIDEBAR ---
st.set_page_config(
    page_title="Termo Eletro App",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PLACEHOLDER DE LOGIN (Futuramente você ativa isso) ---
# if 'logado' not in st.session_state:
#     st.session_state['logado'] = False
#
# if not st.session_state['logado']:
#     st.title("🔒 Acesso Restrito")
#     senha = st.text_input("Digite a senha de acesso:", type="password")
#     if st.button("Entrar"):
#         if senha == "termo123": # Senha Exemplo
#             st.session_state['logado'] = True
#             st.rerun()
#     st.stop() # Para a execução aqui se não estiver logado

# --- 2. CARREGAMENTO DE DADOS (DASHBOARD) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_dashboard_data():
    # Lê Agenda do Google
    df_agenda = conn.read(worksheet="Agenda", ttl=5)
    
    # Lê Orçamentos do Excel (Local)
    try:
        df_obras = pd.read_excel("orcamentos.xlsx")
        # Padronização de colunas (Ajuste conforme seu Excel real)
        # O sistema espera colunas: ORÇAMENTO | DESCRIÇÃO | LOCAL | CLIENTE
        cols_map = {
            'ORÇAMENTO': 'Orcamento', 
            'DESCRIÇÃO': 'Descricao', 
            'LOCAL': 'Cidade', 
            'CLIENTE': 'Cliente'
        }
        # Filtra e renomeia
        df_obras = df_obras.rename(columns=cols_map)
        df_obras['Orcamento'] = df_obras['Orcamento'].astype(str)
    except:
        df_obras = pd.DataFrame() # Retorna vazio se der erro no Excel

    return df_agenda, df_obras

# --- 3. LÓGICA DO DASHBOARD ---
st.title("⚡ Painel de Controle (Visão Geral)")

try:
    df_agenda, df_obras = load_dashboard_data()
    
    # Converte datas
    if not df_agenda.empty:
        df_agenda["Data_Inicio"] = pd.to_datetime(df_agenda["Data_Inicio"], dayfirst=True, errors='coerce')
        df_agenda["Data_Fim"] = pd.to_datetime(df_agenda["Data_Fim"], dayfirst=True, errors='coerce')
        df_agenda["Orcamento"] = df_agenda["Orcamento"].astype(str)

    # --- Filtros de Data ---
    st.sidebar.divider()
    st.sidebar.header("📅 Período de Análise")
    hoje = datetime.today()
    inicio_padrao = hoje - timedelta(days=hoje.weekday())
    
    data_inicio = st.sidebar.date_input("Início", inicio_padrao)
    data_fim = st.sidebar.date_input("Fim", data_inicio + timedelta(days=6))

    # Filtra os dados
    if not df_agenda.empty:
        mask = (df_agenda["Data_Inicio"] <= pd.to_datetime(data_fim)) & (df_agenda["Data_Fim"] >= pd.to_datetime(data_inicio))
        df_semana = df_agenda.loc[mask]
    else:
        df_semana = pd.DataFrame()

    # --- KPIs ---
    col1, col2, col3 = st.columns(3)
    qtd_obras = df_semana["Orcamento"].nunique() if not df_semana.empty else 0
    qtd_carros = df_semana["Veiculo"].nunique() if not df_semana.empty else 0
    
    col1.metric("Obras na Semana", qtd_obras)
    col2.metric("Veículos Alocados", qtd_carros)
    
    # KPI de Pessoas (Conta única de nomes na lista)
    total_pessoas = 0
    if not df_semana.empty:
        lista_geral = df_semana["Equipe"].dropna().astype(str).tolist()
        nomes_unicos = set()
        for linha in lista_geral:
            # Separa por vírgula e remove espaços
            nomes = [n.strip() for n in linha.split(",")]
            nomes_unicos.update(nomes)
        total_pessoas = len(nomes_unicos)
    
    col3.metric("Técnicos em Campo", total_pessoas)

    # --- Gráfico de Gantt ---
    st.divider()
    st.subheader("Cronograma Visual")
    
    if not df_semana.empty and not df_obras.empty:
        # Cruza Agenda com Obras para pegar o nome da Cidade
        df_viz = df_semana.merge(df_obras, on="Orcamento", how="left")
        df_viz["Rotulo"] = df_viz["Orcamento"] + " - " + df_viz["Cidade"].fillna("N/D")
        
        fig = px.timeline(
            df_viz, 
            x_start="Data_Inicio", 
            x_end="Data_Fim", 
            y="Rotulo",
            color="Veiculo", # Cores por Carro
            hover_data=["Equipe", "Cliente"],
            title=f"Programação: {data_inicio.strftime('%d/%m')} a {data_fim.strftime('%d/%m')}"
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
        
        # --- Alerta de Conflitos (Duplicidade de Veículos) ---
        duplicados = df_semana[df_semana.duplicated(subset=['Veiculo', 'Data_Inicio'], keep=False)]
        if not duplicados.empty:
            st.error("🚨 CONFLITO DETECTADO: Veículos duplicados na mesma data!")
            st.dataframe(duplicados[['Data_Inicio', 'Veiculo', 'Orcamento']], hide_index=True)
    
    elif df_agenda.empty:
        st.info("A agenda está vazia. Vá em 'Programação' para adicionar obras.")
    else:
        st.warning("Sem dados para o período selecionado.")

except Exception as e:
    st.error(f"Erro ao carregar dashboard: {e}")
    st.info("Verifique se a planilha Google e o arquivo orcamentos.xlsx estão configurados.")
