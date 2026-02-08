import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# --- CONFIGURAÇÕES DE NOMES ---
SHEET_NAME = "Agenda_dados_planejamento"
EXCEL_FILE_NAME = "dados_dashboard_obras.xlsx"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def conectar_apis():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    gc = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return gc, drive_service

def buscar_id_por_nome(drive_service, filename):
    query = f"name = '{filename}' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        st.error(f"ERRO: Arquivo '{filename}' não encontrado no Drive.")
        st.stop()
    return items[0]['id']

@st.cache_data(ttl=600)
def carregar_dados():
    gc, drive_service = conectar_apis()
    
    # 1. Carregar Google Sheets
    try:
        sh = gc.open(SHEET_NAME) 
        ws_agenda = sh.worksheet("Agenda")
        ws_frota = sh.worksheet("Frota")
        ws_time = sh.worksheet("Time") # <--- NOVO: Carrega aba Time
        
        df_agenda = pd.DataFrame(ws_agenda.get_all_records())
        df_frota = pd.DataFrame(ws_frota.get_all_records())
        df_time = pd.DataFrame(ws_time.get_all_records()) # <--- NOVO
        
    except Exception as e:
        st.error(f"Erro ao carregar Planilha Google: {e}")
        st.stop()

    # 2. Carregar Excel do Drive
    excel_id = buscar_id_por_nome(drive_service, EXCEL_FILE_NAME)
    try:
        request = drive_service.files().get_media(fileId=excel_id)
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        file_io.seek(0)
        df_obras = pd.read_excel(file_io)
    except Exception as e:
        st.error(f"Erro ao baixar Excel: {e}")
        st.stop()
    
    return df_agenda, df_frota, df_time, df_obras # <--- Retorna 4 itens agora
    
def salvar_no_sheets(df_novo):
    gc, _ = conectar_apis()
    sh = gc.open(SHEET_NAME)
    ws = sh.worksheet("Agenda")
    ws.clear()
    ws.update([df_novo.columns.values.tolist()] + df_novo.values.tolist())
    st.cache_data.clear()
