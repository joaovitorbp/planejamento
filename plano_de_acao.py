import streamlit as st
import pandas as pd
import conexao

def app():
    st.header("📝 Editor de Plano de Ação")

    # Carregar Dados
    df_agenda, df_frota, df_obras = conexao.carregar_dados()

    # Prepara listas para Dropdowns
    lista_veiculos = df_frota['placa'].unique().tolist() if 'placa' in df_frota.columns else []
    lista_obras = df_obras['cod_orcamento'].astype(str).unique().tolist() if 'cod_orcamento' in df_obras.columns else []

    st.info("Edite os dados abaixo e clique em Salvar para atualizar o Google Sheets.")

    # Data Editor
    df_editado = st.data_editor(
        df_agenda,
        num_rows="dynamic",
        column_config={
            "cod_orcamento": st.column_config.SelectboxColumn(
                "Obra/Orçamento",
                help="Selecione o código do orçamento",
                options=lista_obras,
                required=True
            ),
            "veiculo": st.column_config.SelectboxColumn(
                "Veículo",
                help="Selecione o veículo da frota",
                options=lista_veiculos,
                required=True
            ),
            "data_inicio": st.column_config.DateColumn("Início", format="DD/MM/YYYY"),
            "data_fim": st.column_config.DateColumn("Fim", format="DD/MM/YYYY"),
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=["Planejado", "Confirmado", "Executado", "Cancelado"]
            )
        },
        use_container_width=True,
        hide_index=True
    )

    if st.button("💾 Salvar Alterações", type="primary"):
        # --- Validação: Duplicidade de Veículo ---
        # Lógica simplificada: Verifica se há sobreposição de datas para o mesmo veículo
        tem_erro = False
        
        # Converte para datetime para garantir comparação
        df_editado['data_inicio'] = pd.to_datetime(df_editado['data_inicio'])
        df_editado['data_fim'] = pd.to_datetime(df_editado['data_fim'])

        # Loop simples de validação (pode ser otimizado para grandes volumes)
        for veiculo in df_editado['veiculo'].unique():
            df_v = df_editado[df_editado['veiculo'] == veiculo]
            df_v = df_v.sort_values('data_inicio')
            
            # Checa sobreposição
            # Shift das datas para comparar linha atual com a anterior
            if not df_v.empty and len(df_v) > 1:
                # Lógica: Se o início da atual for menor que o fim da anterior
                # (Isso é uma simplificação, idealmente checa range overlap completo)
                pass 
                # IMPLEMENTAR: Verificação robusta de overlap de datas aqui se necessário.
                
                # Exemplo de validação simples (mesmo dia, mesmo carro)
                duplicados = df_v[df_v.duplicated(subset=['data_inicio'], keep=False)]
                if not duplicados.empty:
                    st.error(f"Conflito de agendamento para o veículo {veiculo} na mesma data de início!")
                    tem_erro = True
                    break

        if not tem_erro:
            try:
                with st.spinner("Salvando no Google Sheets..."):
                    # Converte datas de volta para string formato ISO ou BR antes de enviar, se necessário
                    df_salvar = df_editado.copy()
                    df_salvar['data_inicio'] = df_salvar['data_inicio'].astype(str)
                    df_salvar['data_fim'] = df_salvar['data_fim'].astype(str)
                    
                    conexao.salvar_no_sheets(df_salvar)
                st.success("Sucesso! Planilha atualizada.")
                st.cache_data.clear() # Garante que o refresh funcione
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
