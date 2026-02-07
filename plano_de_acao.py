import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

def show_page():
    st.header("📝 Plano de Ação (Editor)")
    st.markdown("Defina a programação para a próxima semana.")

    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- CARREGAR OPÇÕES (DROPDOWNS) ---
    @st.cache_data(ttl=600)
    def load_options():
        # 1. ORÇAMENTOS (do Excel Local: dados_dashboard_obras.xlsx)
        opcoes_obras = []
        try:
            df_excel = pd.read_excel("dados_dashboard_obras.xlsx")
            # Procura colunas dinamicamente
            c_orc = next((c for c in df_excel.columns if "ORÇAMENTO" in c.upper()), None)
            c_loc = next((c for c in df_excel.columns if "LOCAL" in c.upper()), None)
            
            if c_orc and c_loc:
                df_excel['Label'] = df_excel[c_orc].astype(str) + " - " + df_excel[c_loc].astype(str)
                opcoes_obras = sorted(df_excel['Label'].dropna().unique().tolist())
        except:
            pass # Lista fica vazia se der erro

        # 2. FROTA (do Google Sheets - Aba: Frota)
        opcoes_frota = []
        try:
            df_frota = conn.read(worksheet="Frota")
            # Assume colunas Modelo e Placa
            if 'Modelo' in df_frota.columns and 'Placa' in df_frota.columns:
                df_frota['Label'] = df_frota['Modelo'] + " - " + df_frota['Placa']
                opcoes_frota = sorted(df_frota['Label'].dropna().unique().tolist())
        except: pass
        
        # 3. TIME (do Google Sheets - Aba: Time) - Opcional, se quiser lista de nomes
        # Apenas para referência, já que no editor será texto livre ou multiselect simulado
        
        return opcoes_obras, opcoes_frota

    lista_obras, lista_frota = load_options()

    # --- EDITOR DE DADOS ---
    try:
        # Lê a Agenda atual
        df_agenda = conn.read(worksheet="Agenda")
        
        # Garante formatação
        if not df_agenda.empty:
            df_agenda["Data_Inicio"] = pd.to_datetime(df_agenda["Data_Inicio"], errors='coerce')
            df_agenda["Data_Fim"] = pd.to_datetime(df_agenda["Data_Fim"], errors='coerce')
            df_agenda["Orcamento"] = df_agenda["Orcamento"].astype(str)

        # Mostra o Editor
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
                
                "Equipe": st.column_config.TextColumn(
                    "Equipe", 
                    width="medium", 
                    help="Nomes separados por vírgula"
                ),
                
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

        # --- BOTÃO SALVAR ---
        if st.button("💾 Salvar Alterações no Drive", type="primary"):
            # Validação simples de conflito
            if not edited_df.empty and edited_df.duplicated(subset=['Veiculo', 'Data_Inicio']).any():
                st.warning("⚠️ Atenção: Existem veículos alocados 2x na mesma data!")
            
            # Prepara dados para salvar (Converte datas para string YYYY-MM-DD)
            df_save = edited_df.copy()
            df_save["Data_Inicio"] = df_save["Data_Inicio"].dt.strftime('%Y-%m-%d')
            df_save["Data_Fim"] = df_save["Data_Fim"].dt.strftime('%Y-%m-%d')
            
            # Limpeza opcional: Salvar só o código do orçamento, tirando o nome da cidade
            # def limpar_cod(valor): return valor.split(" - ")[0] if " - " in str(valor) else valor
            # df_save["Orcamento"] = df_save["Orcamento"].apply(limpar_cod)

            conn.update(worksheet="Agenda", data=df_save)
            st.success("✅ Atualizado com sucesso!")
            
    except Exception as e:
        st.error(f"Erro ao carregar o editor: {e}")
