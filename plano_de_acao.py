import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ==========================================
# ⚠️ LINK DA PLANILHA DE ORÇAMENTOS
# ==========================================
URL_ORCAMENTOS = "https://docs.google.com/spreadsheets/d/1CZQCkEnWLVxnwBqAtyMrV_WsiXU5XIvn/edit?gid=1069183619#gid=1069183619"
# ==========================================

def show_page():
    st.header("📝 Editor de Plano de Ação")
    
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- CARREGA AS OPÇÕES DOS DROPDOWNS ---
    @st.cache_data(ttl=600)
    def load_options():
        # 1. Opções de Obras (Lê direto do Link fornecido)
        opcoes_obras = []
        try:
            df_obras = conn.read(spreadsheet=URL_ORCAMENTOS)
            
            c_orc = next((c for c in df_obras.columns if "ORÇAMENTO" in c.upper()), None)
            c_loc = next((c for c in df_obras.columns if "LOCAL" in c.upper()), None)
            
            if c_orc and c_loc:
                df_obras['Label'] = df_obras[c_orc].astype(str) + " - " + df_obras[c_loc].astype(str)
                opcoes_obras = sorted(df_obras['Label'].dropna().unique().tolist())
        except Exception:
            pass # Se falhar, lista fica vazia

        # 2. Opções de Frota (Lê da planilha configurada no secrets)
        opcoes_frota = []
        try:
            df_frota = conn.read(worksheet="Frota")
            if 'Modelo' in df_frota.columns and 'Placa' in df_frota.columns:
                df_frota['Label'] = df_frota['Modelo'] + " - " + df_frota['Placa']
                opcoes_frota = sorted(df_frota['Label'].dropna().unique().tolist())
        except: 
            pass
        
        return opcoes_obras, opcoes_frota

    lista_obras, lista_frota = load_options()

    # --- EDITOR ---
    try:
        # Lê a Agenda (do secrets)
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
                
                "Orcamento": st.column_config.SelectboxColumn(
                    "Obra", 
                    options=lista_obras, 
                    width="large", 
                    required=True
                ),
                
                "Equipe": st.column_config.TextColumn("Equipe", width="medium"),
                
                "Veiculo": st.column_config.SelectboxColumn(
                    "Veículo", 
                    options=lista_frota, 
                    width="medium", 
                    required=True
                ),
                
                "Data_Inicio": st.column_config.DateColumn("Início", format="DD/MM/YYYY", step=1),
                "Data_Fim": st.column_config.DateColumn("Fim", format="DD/MM/YYYY", step=1),
            }
        )

        if st.button("💾 Salvar Alterações", type="primary"):
            # Validação
            if not edited_df.empty and edited_df.duplicated(subset=['Veiculo', 'Data_Inicio']).any():
                st.warning("⚠️ Atenção: Veículos duplicados na mesma data!")
            
            # Salvar
            df_save = edited_df.copy()
            df_save["Data_Inicio"] = df_save["Data_Inicio"].dt.strftime('%Y-%m-%d')
            df_save["Data_Fim"] = df_save["Data_Fim"].dt.strftime('%Y-%m-%d')
            
            conn.update(worksheet="Agenda", data=df_save)
            st.success("✅ Salvo com sucesso!")
            
    except Exception as e:
        st.error(f"Erro no editor: {e}")
