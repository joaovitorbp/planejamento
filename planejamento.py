import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
import io

# --- CONFIGURAÇÕES (COLE SEUS LINKS AQUI) ---
# Link da Planilha do Google (Agenda/Time/Frota)
LINK_PLANILHA_GOOGLE = "COLE_AQUI_O_LINK_INTEIRO_DA_SUA_PLANILHA_DO_SHEETS"

# ID do arquivo Excel de Orçamentos (do Drive)
ID_ARQUIVO_EXCEL = "COLE_AQUI_O_ID_DO_ARQUIVO_EXCEL_ORCAMENTOS" 

def download_excel_drive(file_id):
    try:
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=creds)
        request = service.files().get_media(fileId=file_id)
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        file_io.seek(0)
        return pd.read_excel(file_io)
    except Exception as e:
        return pd.DataFrame()

def show_page():
    st.header("📅 Planejamento Geral")
    conn = st.connection("gsheets", type=GSheetsConnection)

    @st.cache_data(ttl=60)
    def load_data():
        # AQUI ESTÁ A CORREÇÃO: Passamos o link direto no código
        df_agenda = conn.read(spreadsheet=LINK_PLANILHA_GOOGLE, worksheet="Agenda", ttl=5)
        
        df_obras = download_excel_drive(ID_ARQUIVO_EXCEL)
        
        if not df_obras.empty:
            c_orc = next((c for c in df_obras.columns if "ORÇAMENTO" in c.upper()), "ORÇAMENTO")
            c_loc = next((c for c in df_obras.columns if "LOCAL" in c.upper()), "LOCAL")
            df_obras = df_obras.rename(columns={c_orc: 'Orcamento', c_loc: 'Cidade'})
            df_obras['Orcamento'] = df_obras['Orcamento'].astype(str)
            
        return df_agenda, df_obras

    try:
        df_agenda, df_obras = load_data()
        
        if not df_agenda.empty:
            df_agenda["Data_Inicio"] = pd.to_datetime(df_agenda["Data_Inicio"], dayfirst=True, errors='coerce')
            df_agenda["Data_Fim"] = pd.to_datetime(df_agenda["Data_Fim"], dayfirst=True, errors='coerce')
            df_agenda["Orcamento"] = df_agenda["Orcamento"].astype(str)

            col1, col2 = st.columns(2)
            data_filtro = col1.date_input("Filtrar a partir de:", pd.to_datetime("today") - pd.Timedelta(weeks=1))
            df_view = df_agenda[df_agenda["Data_Inicio"] >= pd.to_datetime(data_filtro)]

            st.dataframe(df_view, use_container_width=True, hide_index=True)
            
            if not df_obras.empty:
                st.subheader("Cronograma Visual")
                df_merged = df_view.merge(df_obras, on="Orcamento", how="left")
                df_merged["Rotulo"] = df_merged["Orcamento"] + " - " + df_merged["Cidade"].fillna("")
                
                fig = px.timeline(df_merged, x_start="Data_Inicio", x_end="Data_Fim", y="Rotulo", color="Veiculo")
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado encontrado.")
            
    except Exception as e:
        st.error(f"Erro: {e}")
