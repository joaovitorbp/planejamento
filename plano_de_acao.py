import streamlit as st
import pandas as pd
import conexao

def app():
    st.header("📝 Editor de Plano de Ação")

    # 1. Carregar Dados
    with st.spinner("Carregando dados..."):
        df_agenda, df_frota, df_obras = conexao.carregar_dados()

    # 2. Tratamento para Tabela Vazia (O PULO DO GATO)
    # Se a agenda estiver vazia, criamos um DataFrame com as colunas certas
    # para que o editor saiba o que mostrar.
    colunas_obrigatorias = ['cod_orcamento', 'veiculo', 'data_inicio', 'data_fim', 'status']
    
    if df_agenda.empty:
        df_agenda = pd.DataFrame(columns=colunas_obrigatorias)
    else:
        # Garante que todas as colunas existam mesmo se o Excel vier incompleto
        for col in colunas_obrigatorias:
            if col not in df_agenda.columns:
                df_agenda[col] = None

    # 3. Preparar Listas para os Dropdowns
    lista_veiculos = []
    if not df_frota.empty and 'placa' in df_frota.columns:
        lista_veiculos = df_frota['placa'].dropna().unique().tolist()
    
    lista_obras = []
    if not df_obras.empty and 'cod_orcamento' in df_obras.columns:
        # Converte para string para evitar erro no dropdown
        lista_obras = df_obras['cod_orcamento'].astype(str).unique().tolist()

    # 4. O Editor de Dados
    st.info("Adicione novas linhas clicando no botão '+' abaixo da tabela.")
    
    df_editado = st.data_editor(
        df_agenda,
        num_rows="dynamic", # Permite adicionar/remover linhas
        column_config={
            "cod_orcamento": st.column_config.SelectboxColumn(
                "Obra/Orçamento",
                help="Selecione o código do orçamento",
                width="medium",
                options=lista_obras,
                required=True
            ),
            "veiculo": st.column_config.SelectboxColumn(
                "Veículo",
                help="Selecione o veículo",
                width="medium",
                options=lista_veiculos,
                required=True
            ),
            "data_inicio": st.column_config.DateColumn(
                "Início", 
                format="DD/MM/YYYY",
                width="small"
            ),
            "data_fim": st.column_config.DateColumn(
                "Fim", 
                format="DD/MM/YYYY",
                width="small"
            ),
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=["Planejado", "Confirmado", "Executado", "Cancelado"],
                width="small"
            )
        },
        use_container_width=True,
        hide_index=True,
        key="editor_agenda" # Chave única para não perder estado
    )

    # 5. Botão de Salvar
    if st.button("💾 Salvar Alterações no Google Sheets", type="primary"):
        if df_editado.empty:
            st.warning("A tabela está vazia. Nada para salvar.")
        else:
            try:
                with st.spinner("Enviando dados para o Google Sheets..."):
                    # Prepara os dados para salvar (converte datas para string para o JSON aceitar)
                    df_salvar = df_editado.copy()
                    
                    # Converte datas para string ISO (YYYY-MM-DD) para ficar padrão no Sheets
                    df_salvar['data_inicio'] = pd.to_datetime(df_salvar['data_inicio']).dt.strftime('%Y-%m-%d')
                    df_salvar['data_fim'] = pd.to_datetime(df_salvar['data_fim']).dt.strftime('%Y-%m-%d')
                    
                    # Remove linhas que possam estar totalmente vazias (sujeira)
                    df_salvar = df_salvar.dropna(how='all')
                    
                    # Chama a função de salvar do conexao.py
                    conexao.salvar_no_sheets(df_salvar)
                
                st.success("Sucesso! Dados atualizados na nuvem.")
                
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
