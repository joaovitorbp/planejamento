import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# ==========================================
# ⚠️ LINK DA PLANILHA DE ORÇAMENTOS (Antigo Excel)
# ==========================================
URL_ORCAMENTOS = "https://docs.google.com/spreadsheets/d/1CZQCkEnWLVxnwBqAtyMrV_WsiXU5XIvn/edit?gid=1069183619#gid=1069183619"
# ==========================================

def show_page():
    st.header("📅 Planejamento Geral")
    
    # Conexão (Usa o secrets para a Agenda)
    conn = st.connection("gsheets", type=GSheetsConnection)

    @st.cache_data(ttl=60)
    def load_data():
        # 1. Lê a Agenda (Do arquivo configurado no secrets.toml)
        df_agenda = conn.read(worksheet="Agenda", ttl=5)
        
        # 2. Lê a Planilha de Orçamentos (Pelo Link direto)
        # Como é Google Sheets, lemos direto. Se a aba não for a primeira, precisaremos ajustar.
        try:
            df_obras = conn.read(spreadsheet=URL_ORCAMENTOS, ttl=600)
            
            # Tratamento de Colunas (Procura por ORÇAMENTO e LOCAL)
            c_orc = next((c for c in df_obras.columns if "ORÇAMENTO" in c.upper()), "ORÇAMENTO")
            c_loc = next((c for c in df_obras.columns if "LOCAL" in c.upper()), "LOCAL")
            
            df_obras = df_obras.rename(columns={c_orc: 'Orcamento', c_loc: 'Cidade'})
            df_obras['Orcamento'] = df_obras['Orcamento'].astype(str)
        except Exception as e:
            st.warning(f"Não foi possível ler a lista de orçamentos: {e}")
            df_obras = pd.DataFrame()
            
        return df_agenda, df_obras

    try:
        df_agenda, df_obras = load_data()

        if not df_agenda.empty:
            # Tratamento de Tipos
            df_agenda["Data_Inicio"] = pd.to_datetime(df_agenda["Data_Inicio"], dayfirst=True, errors='coerce')
            df_agenda["Data_Fim"] = pd.to_datetime(df_agenda["Data_Fim"], dayfirst=True, errors='coerce')
            df_agenda["Orcamento"] = df_agenda["Orcamento"].astype(str)

            # Filtro de Datas
            col1, col2 = st.columns(2)
            data_filtro = col1.date_input("Visualizar a partir de:", pd.to_datetime("today") - pd.Timedelta(weeks=1))
            
            df_view = df_agenda[df_agenda["Data_Inicio"] >= pd.to_datetime(data_filtro)].copy()

            # Tabela
            st.dataframe(
                df_view, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Data_Inicio": st.column_config.DateColumn("Início", format="DD/MM/YYYY"),
                    "Data_Fim": st.column_config.DateColumn("Fim", format="DD/MM/YYYY")
                }
            )
            
            # Gráfico de Gantt
            if not df_obras.empty and not df_view.empty:
                st.subheader("Cronograma Visual")
                # Cruza dados da agenda com o nome da cidade
                df_merged = df_view.merge(df_obras, on="Orcamento", how="left")
                df_merged["Rotulo"] = df_merged["Orcamento"] + " - " + df_merged["Cidade"].fillna("")
                
                fig = px.timeline(
                    df_merged, 
                    x_start="Data_Inicio", x_end="Data_Fim", 
                    y="Rotulo", 
                    color="Veiculo",
                    title="Cronograma de Obras"
                )
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum agendamento encontrado na base de dados.")
            
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
