import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# --- CONFIGURAÇÕES DE NOMES ---
# 1. Nome EXATO da sua Planilha Google (que tem as abas Agenda, Frota, Time)
SHEET_NAME = "Agenda_dados_planejamento"

# 2. Nome EXATO do seu arquivo Excel (que tem os orçamentos)
EXCEL_FILE_NAME = "dados_dashboard_obras.xlsx"

# Escopos de permissão
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def conectar_apis():
    """
    Cria e cacheia a conexão com as APIs do Google.
    Retorna o cliente gspread e o serviço do Drive.
    """
    # Carrega as credenciais do secrets.toml
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    
    # Conexão gspread (Planilhas)
    gc = gspread.authorize(creds)
    
    # Conexão Drive API (Arquivos)
    drive_service = build('drive', 'v3', credentials=creds)
    
    return gc, drive_service

def buscar_id_por_nome(drive_service, filename):
    """
    Busca o ID de um arquivo no Drive pelo nome.
    Retorna o ID do primeiro arquivo encontrado.
    """
    query = f"name = '{filename}' and trashed = false"
    
    # Busca apenas arquivos ativos com esse nome
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        st.error(f"ERRO CRÍTICO: Não encontrei nenhum arquivo chamado '{filename}' no Google Drive. Verifique se o nome está exato e se você compartilhou com o email do robô.")
        st.stop()
    
    # Retorna o ID do primeiro arquivo encontrado
    return items[0]['id']

@st.cache_data(ttl=600)  # Cache de 10 minutos
def carregar_dados():
    """
    Carrega os dados da Planilha Google e do Excel.
    """
    gc, drive_service = conectar_apis()
    
    # --- 1. Carregar Google Sheets (Agenda, Frota) ---
    try:
        sh = gc.open(SHEET_NAME) 
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"ERRO: Não encontrei a planilha '{SHEET_NAME}'. Verifique se o nome está correto e se o robô tem acesso.")
        st.stop()
    
    try:
        # Tenta carregar as abas específicas
        ws_agenda = sh.worksheet("Agenda")
        ws_frota = sh.worksheet("Frota")
        # ws_time = sh.worksheet("Time") # Se precisar no futuro
        
        df_agenda = pd.DataFrame(ws_agenda.get_all_records())
        df_frota = pd.DataFrame(ws_frota.get_all_records())
        
    except gspread.exceptions.WorksheetNotFound as e:
        st.error(f"ERRO: Aba não encontrada na planilha '{SHEET_NAME}'. Verifique se as abas 'Agenda' e 'Frota' existem. Detalhe: {e}")
        st.stop()

    # --- 2. Carregar Excel do Drive (Obras) ---
    # Busca o ID automaticamente pelo nome
    excel_id = buscar_id_por_nome(drive_service, EXCEL_FILE_NAME)
    
    # Baixa o arquivo usando o ID encontrado
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
        st.error(f"Erro ao baixar ou ler o Excel '{EXCEL_FILE_NAME}': {e}")
        st.stop()
    
    return df_agenda, df_frota, df_obras

def salvar_no_sheets(df_novo):
    """
    Salva o DataFrame atualizado na aba 'Agenda'.
    """
    gc, _ = conectar_apis()
    try:
        sh = gc.open(SHEET_NAME)
        ws = sh.worksheet("Agenda")
        
        ws.clear()
        # Atualiza com cabeçalhos e dados
        ws.update([df_novo.columns.values.tolist()] + df_novo.values.tolist())
        
        # Limpa o cache para forçar recarregamento na próxima vez
        st.cache_data.clear()
        
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")
        raise e
