import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
import io

# ID do Excel (Orçamentos) - Esse precisa ficar aqui pois é arquivo solto no Drive
ID_ARQUIVO_EXCEL = "dados_dashboard_obras.xlsx" 

def download_excel_drive(file_id):
    try:
        # Pega as credenciais do TOML para acessar o Drive
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
    except:
        return pd.DataFrame()

def show_page():
    st.header("📅 Planejamento Geral")
    
    # CONEXÃO INTELIGENTE: Lê o link direto do secrets.toml
    conn = st.connection("gsheets", type=GSheetsConnection)

    @st.cache_data(ttl=60)
    def load_data():
        # Lê a aba Agenda (O link já está no secrets, não precisa por aqui)
        df_agenda = conn.read(worksheet="Agenda", ttl=5)
        
        # Lê o Excel do Drive
        df_obras = download_excel_drive(ID_ARQUIVO_EXCEL)
        
        # Tratamento do Excel
        if not df_obras.empty:
            c_orc = next((c for c in df_obras.columns if "ORÇAMENTO" in c.upper()), "ORÇAMENTO")
            c_loc = next((c for c in df_obras.columns if "LOCAL" in c.upper()), "LOCAL")
            df_obras = df_obras.rename(columns={c_orc: 'Orcamento', c_loc: 'Cidade'})
            df_obras['Orcamento'] = df_obras['Orcamento'].astype(str)
            
        return df_agenda, df_obras

    df_agenda, df_obras = load_data()

    if not df_agenda.empty:
        # Tratamento de dados
        df_agenda["Data_Inicio"] = pd.to_datetime(df_agenda["Data_Inicio"], dayfirst=True, errors='coerce')
        df_agenda["Data_Fim"] = pd.to_datetime(df_agenda["Data_Fim"], dayfirst=True, errors='coerce')
        df_agenda["Orcamento"] = df_agenda["Orcamento"].astype(str)

        st.dataframe(df_agenda, use_container_width=True, hide_index=True)
        
        if not df_obras.empty:
            st.subheader("Cronograma")
            df_merged = df_agenda.merge(df_obras, on="Orcamento", how="left")
            df_merged["Rotulo"] = df_merged["Orcamento"] + " - " + df_merged["Cidade"].fillna("")
            
            fig = px.timeline(df_merged, x_start="Data_Inicio", x_end="Data_Fim", y="Rotulo", color="Veiculo")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado encontrado.")
