import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
import io

# ID do arquivo Excel (O MESMO DO OUTRO ARQUIVO)
ID_ARQUIVO_EXCEL = "COLE_O_ID_DO_EXCEL_AQUI"

def download_excel_drive(file_id):
    """Função auxiliar para baixar do Drive"""
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
    except:
        return pd.DataFrame()

def show_page():
    st.header("📝 Editor de Plano de Ação")
    conn = st.connection("gsheets", type=GSheetsConnection)

    @st.cache_data(ttl=600)
    def load_options():
        # 1. ORÇAMENTOS (Direto do Drive)
        opcoes_obras = []
        df_excel = download_excel_drive(ID_ARQUIVO_EXCEL)
        
        if not df_excel.empty:
            c_orc = next((c for c in df_excel.columns if "ORÇAMENTO" in c.upper()), None)
            c_loc = next((c for c in df_excel.columns if "LOCAL" in c.upper()), None)
            if c_orc and c_loc:
                df_excel['Label'] = df_excel[c_orc].astype(str) + " - " + df_excel[c_loc].astype(str)
                opcoes_obras = sorted(df_excel['Label'].dropna().unique().tolist())

        # 2. FROTA (Google Sheets)
        opcoes_frota = []
        try:
            df_frota = conn.read(worksheet="Frota")
            if 'Modelo' in df_frota.columns and 'Placa' in df_frota.columns:
                df_frota['Label'] = df_frota['Modelo'] + " - " + df_frota['Placa']
                opcoes_frota = sorted(df_frota['Label'].dropna().unique().tolist())
        except: pass
        
        return opcoes_obras, opcoes_frota

    lista_obras, lista_frota = load_options()

    try:
        df_agenda = conn.read(worksheet="Agenda")
        if not df_agenda.empty:
            df_agenda["Data_Inicio"] = pd.to_datetime(df_agenda["Data_Inicio"], errors='coerce')
            df_agenda["Data_Fim"] = pd.to_datetime(df_agenda["Data_Fim"], errors='coerce')
            df_agenda["Orcamento"] = df_agenda["Orcamento"].astype(str)

        edited_df = st.data_editor(
            df_agenda,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.TextColumn("ID", disabled=True),
                "Orcamento": st.column_config.SelectboxColumn("Obra", options=lista_obras, width="large", required=True),
                "Equipe": st.column_config.TextColumn("Equipe", width="medium"),
                "Veiculo": st.column_config.SelectboxColumn("Veículo", options=lista_frota, width="medium", required=True),
                "Data_Inicio": st.column_config.DateColumn("Início", format="DD/MM/YYYY", step=1),
                "Data_Fim": st.column_config.DateColumn("Fim", format="DD/MM/YYYY", step=1),
            }
        )

        if st.button("💾 Salvar Alterações", type="primary"):
            if not edited_df.empty and edited_df.duplicated(subset=['Veiculo', 'Data_Inicio']).any():
                st.warning("⚠️ Veículos duplicados na mesma data!")
            
            df_save = edited_df.copy()
            df_save["Data_Inicio"] = df_save["Data_Inicio"].dt.strftime('%Y-%m-%d')
            df_save["Data_Fim"] = df_save["Data_Fim"].dt.strftime('%Y-%m-%d')
            conn.update(worksheet="Agenda", data=df_save)
            st.success("✅ Salvo no Google Drive!")
            
    except Exception as e:
        st.error(f"Erro: {e}")
