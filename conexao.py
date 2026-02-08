import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# Configurações Globais
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Nome da planilha no Google Sheets (Deve ser exato)
SHEET_NAME = "Nome Da Sua Planilha Google" 

# ID do arquivo Excel no Google Drive (pegue na URL do arquivo: /d/ID_AQUI/view)
EXCEL_FILE_ID = "COLOQUE_O_ID_DO_ARQUIVO_EXCEL_AQUI"

@st.cache_resource
def conectar_apis():
    """
    Cria e cacheia a conexão com as APIs do Google.
    Retorna o cliente gspread e o serviço do Drive.
    """
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    
    # Conexão gspread
    gc = gspread.authorize(creds)
    
    # Conexão Drive API
    drive_service = build('drive', 'v3', credentials=creds)
    
    return gc, drive_service

@st.cache_data(ttl=600)  # Cache de 10 minutos para leitura
def carregar_dados():
    """
    Carrega todas as fontes de dados necessárias.
    """
    gc, drive_service = conectar_apis()
    
    # --- 1. Carregar Google Sheets (Agenda, Frota, Time) ---
    sh = gc.open(SHEET_NAME)
    
    ws_agenda = sh.worksheet("Agenda")
    ws_frota = sh.worksheet("Frota")
    # ws_time = sh.worksheet("Time") # Caso precise no futuro
    
    df_agenda = pd.DataFrame(ws_agenda.get_all_records())
    df_frota = pd.DataFrame(ws_frota.get_all_records())
    
    # --- 2. Carregar Excel do Drive (Obras) ---
    request = drive_service.files().get_media(fileId=EXCEL_FILE_ID)
    file_io = io.BytesIO()
    downloader = MediaIoBaseDownload(file_io, request)
    
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        
    file_io.seek(0)
    df_obras = pd.read_excel(file_io)
    
    return df_agenda, df_frota, df_obras

def salvar_no_sheets(df_novo):
    """
    Recebe um DataFrame atualizado e salva na aba Agenda.
    Limpa o cache para garantir que a próxima leitura venha atualizada.
    """
    gc, _ = conectar_apis()
    sh = gc.open(SHEET_NAME)
    ws = sh.worksheet("Agenda")
    
    # Limpa e reescreve
    ws.clear()
    # Adiciona cabeçalho e dados
    ws.update([df_novo.columns.values.tolist()] + df_novo.values.tolist())
    
    # Limpa o cache de dados para forçar recarregamento na próxima ação
    st.cache_data.clear()
