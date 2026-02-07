import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

def show_page():
    st.header("📅 Planejamento (Todos os Agendamentos)")
    
    # Conexão com Google Sheets
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- CARREGAR DADOS ---
    @st.cache_data(ttl=60)
    def load_data():
        # 1. Lê a AGENDA (Base de Dados Principal)
        df_agenda = conn.read(worksheet="Agenda", ttl=5)
        
        # 2. Lê os ORÇAMENTOS (Arquivo Excel Local)
        # Nome do arquivo conforme você especificou: dados_dashboard_obras.xlsx
        try:
            df_obras = pd.read_excel("dados_dashboard_obras.xlsx")
            # Padroniza nomes de colunas (Ajuste conforme seu Excel real)
            # Tenta achar colunas que contenham "ORÇAMENTO" e "LOCAL"
            col_orc = next((c for c in df_obras.columns if "ORÇAMENTO" in c.upper()), "ORÇAMENTO")
            col_loc = next((c for c in df_obras.columns if "LOCAL" in c.upper()), "LOCAL")
            
            # Renomeia para facilitar
            df_obras = df_obras.rename(columns={col_orc: 'Orcamento', col_loc: 'Cidade'})
            df_obras['Orcamento'] = df_obras['Orcamento'].astype(str)
        except Exception as e:
            st.error(f"Erro ao ler arquivo de orçamentos: {e}")
            df_obras = pd.DataFrame()
            
        return df_agenda, df_obras

    df_agenda, df_obras = load_data()

    # --- VISUALIZAÇÃO ---
    if not df_agenda.empty:
        # Tratamento de tipos
        df_agenda["Data_Inicio"] = pd.to_datetime(df_agenda["Data_Inicio"], dayfirst=True, errors='coerce')
        df_agenda["Data_Fim"] = pd.to_datetime(df_agenda["Data_Fim"], dayfirst=True, errors='coerce')
        df_agenda["Orcamento"] = df_agenda["Orcamento"].astype(str)

        # Filtro de Data na Tela (Opcional, para não carregar anos de dados)
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Filtrar visualização por data de início:")
            data_filtro = st.date_input("A partir de:", value=pd.to_datetime("today") - pd.Timedelta(weeks=1))

        # Aplica filtro
        df_view = df_agenda[df_agenda["Data_Inicio"] >= pd.to_datetime(data_filtro)]

        # Tabela Geral
        st.dataframe(
            df_view, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Data_Inicio": st.column_config.DateColumn("Início", format="DD/MM/YYYY"),
                "Data_Fim": st.column_config.DateColumn("Fim", format="DD/MM/YYYY")
            }
        )
        
        # Gráfico de Gantt (Se houver orçamentos para cruzar)
        if not df_obras.empty:
            st.subheader("Linha do Tempo")
            df_merged = df_view.merge(df_obras, on="Orcamento", how="left")
            df_merged["Rotulo"] = df_merged["Orcamento"] + " - " + df_merged["Cidade"].fillna("")
            
            fig = px.timeline(
                df_merged, 
                x_start="Data_Inicio", x_end="Data_Fim", 
                y="Rotulo", 
                color="Veiculo",
                title="Cronograma Geral"
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum agendamento encontrado na base de dados.")
