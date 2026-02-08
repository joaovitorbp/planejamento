import streamlit as st
import pandas as pd
import conexao

def app():
    st.header("📝 Editor de Agenda (Tabela)")

    # Ajustado para receber 4 valores (incluindo df_time)
    df_agenda, df_frota, df_time, df_obras = conexao.carregar_dados()

    # Define colunas novas
    colunas_novas = ['Projeto', 'Descrição', 'Cliente', 'Data Início', 'Data Fim', 'Executantes', 'Veículo', 'Status']
    
    if df_agenda.empty:
        df_agenda = pd.DataFrame(columns=colunas_novas)

    # Editor
    df_editado = st.data_editor(
        df_agenda,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="editor_full"
    )

    if st.button("💾 Salvar Tudo"):
        # Tratamento simples de datas antes de salvar
        df_salvar = df_editado.copy()
        df_salvar['Data Início'] = pd.to_datetime(df_salvar['Data Início']).dt.strftime('%Y-%m-%d')
        df_salvar['Data Fim'] = pd.to_datetime(df_salvar['Data Fim']).dt.strftime('%Y-%m-%d')
        
        conexao.salvar_no_sheets(df_salvar)
        st.success("Salvo!")
