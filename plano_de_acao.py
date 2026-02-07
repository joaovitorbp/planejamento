import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Editor de Programação", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

st.title("✏️ Editor de Programação Semanal")
st.markdown("Adicione as obras, defina a equipe e selecione o veículo na tabela abaixo.")

# --- 1. CARREGAR OPÇÕES (Listas Suspensas) ---
@st.cache_data(ttl=600)
def load_options():
    # A) Orçamentos (do Excel Local)
    opcoes_obras = []
    try:
        df_excel = pd.read_excel("orcamentos.xlsx")
        # Cria rótulo: "CODIGO - LOCAL"
        # Ajuste os nomes das colunas conforme seu Excel
        if 'ORÇAMENTO' in df_excel.columns and 'LOCAL' in df_excel.columns:
            df_excel['Label'] = df_excel['ORÇAMENTO'].astype(str) + " - " + df_excel['LOCAL'].astype(str)
            opcoes_obras = df_excel['Label'].dropna().unique().tolist()
    except:
        pass # Se der erro, a lista fica vazia

    # B) Frota e Time (do Google Sheets)
    try:
        df_frota = conn.read(worksheet="Frota")
        df_time = conn.read(worksheet="Time")
        
        # Frota: "MODELO - PLACA"
        opcoes_frota = []
        if 'Modelo' in df_frota.columns and 'Placa' in df_frota.columns:
            df_frota['Label'] = df_frota['Modelo'] + " - " + df_frota['Placa']
            opcoes_frota = df_frota['Label'].dropna().unique().tolist()
            
        # Time (Apenas lista de nomes para referência)
        opcoes_time = []
        if 'Nome' in df_time.columns:
            opcoes_time = df_time['Nome'].dropna().unique().tolist()
            
    except:
        opcoes_frota = []
        opcoes_time = []

    return opcoes_obras, opcoes_frota, opcoes_time

# Carrega as listas
lista_obras, lista_frota, lista_time = load_options()

# --- 2. EDITOR DE DADOS ---
try:
    df_agenda = conn.read(worksheet="Agenda")
    
    # Tratamento inicial para o Editor não quebrar
    if not df_agenda.empty:
        df_agenda["Data_Inicio"] = pd.to_datetime(df_agenda["Data_Inicio"])
        df_agenda["Data_Fim"] = pd.to_datetime(df_agenda["Data_Fim"])
        df_agenda["Orcamento"] = df_agenda["Orcamento"].astype(str)

    # Exibe a tabela editável
    edited_df = st.data_editor(
        df_agenda,
        num_rows="dynamic", # Permite clicar no botão "+"
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn("ID (Auto)", disabled=True),
            
            "Orcamento": st.column_config.SelectboxColumn(
                "Selecione a Obra",
                options=lista_obras,
                width="large",
                required=True,
                help="Lista carregada do Excel de Orçamentos"
            ),
            
            "Equipe": st.column_config.TextColumn(
                "Equipe Técnica",
                width="medium",
                help="Digite os nomes separados por vírgula (Ex: Tiago, Willity)"
            ),
            
            "Veiculo": st.column_config.SelectboxColumn(
                "Veículo da Frota",
                options=lista_frota,
                width="medium",
                required=True,
                help="Selecione qual carro levará a equipe"
            ),
            
            "Data_Inicio": st.column_config.DateColumn("Início", format="DD/MM/YYYY", step=1),
            "Data_Fim": st.column_config.DateColumn("Fim", format="DD/MM/YYYY", step=1),
        }
    )

    # --- 3. VALIDAÇÃO E SALVAMENTO ---
    st.caption("Dica: Para adicionar uma nova obra, clique no botão '+' na última linha da tabela.")
    
    if st.button("💾 Salvar Alterações no Drive", type="primary"):
        salvar = True
        
        # Validação 1: Conflito de Veículos
        # Verifica se tem o mesmo carro iniciando na mesma data em linhas diferentes
        if edited_df.duplicated(subset=['Veiculo', 'Data_Inicio']).any():
            st.warning("⚠️ ALERTA DE LOGÍSTICA: Você alocou o mesmo veículo para obras diferentes na mesma data!")
            # Não impedimos de salvar, apenas avisamos (decisão do usuário)
        
        # Validação 2: Limpeza do Código do Orçamento
        # O usuário vê "2025 1891 - Cerradão", mas queremos salvar só "2025 1891"
        df_to_save = edited_df.copy()
        
        # Função para limpar o texto do orçamento (pega tudo antes do primeiro " - ")
        def limpar_orcamento(valor):
            if isinstance(valor, str) and " - " in valor:
                return valor.split(" - ")[0]
            return valor
            
        df_to_save['Orcamento'] = df_to_save['Orcamento'].apply(limpar_orcamento)
        
        if salvar:
            try:
                conn.update(worksheet="Agenda", data=df_to_save)
                st.success("✅ Programação salva com sucesso no Google Drive!")
                st.balloons()
                
                # Recarrega a página para atualizar visualmente (opcional)
                # st.rerun() 
            except Exception as e:
                st.error(f"Erro técnico ao salvar: {e}")

except Exception as e:
    st.error(f"Erro ao carregar a Agenda. Verifique se a planilha Google tem a aba 'Agenda'. Detalhe: {e}")
