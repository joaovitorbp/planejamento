import streamlit as st
import plotly.express as px
import pandas as pd
import conexao

def app():
    st.header("📅 Visualização do Planejamento")

    # Carregar Dados
    with st.spinner("Carregando dados..."):
        df_agenda, df_frota, df_obras = conexao.carregar_dados()

    if df_agenda.empty:
        st.warning("A agenda está vazia ou não foi carregada corretamente.")
        # Cria um dataframe vazio com as colunas certas para não dar erro no merge
        df_agenda = pd.DataFrame(columns=['cod_orcamento', 'veiculo', 'data_inicio', 'data_fim', 'status'])

    # Merge: Cruzar Agenda com Obras para pegar detalhes
    if not df_obras.empty and 'cod_orcamento' in df_agenda.columns and 'cod_orcamento' in df_obras.columns:
        # Garante que as chaves de merge sejam do mesmo tipo (string)
        df_agenda['cod_orcamento'] = df_agenda['cod_orcamento'].astype(str)
        df_obras['cod_orcamento'] = df_obras['cod_orcamento'].astype(str)
        
        try:
            df_completo = pd.merge(df_agenda, df_obras, on='cod_orcamento', how='left')
        except Exception as e:
            st.error(f"Erro ao cruzar tabelas: {e}")
            df_completo = df_agenda
    else:
        df_completo = df_agenda

    # Filtros de Data
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data Início", value=pd.to_datetime("today"))
    with col2:
        data_fim = st.date_input("Data Fim", value=pd.to_datetime("today") + pd.Timedelta(days=30))

    # Se a tabela estiver vazia, para por aqui
    if df_completo.empty:
        st.info("Sem dados para exibir.")
        return

    # Tratamento de datas para o gráfico
    try:
        # Converte colunas de data
        df_completo['data_inicio'] = pd.to_datetime(df_completo['data_inicio'], errors='coerce')
        df_completo['data_fim'] = pd.to_datetime(df_completo['data_fim'], errors='coerce')
        
        # Remove linhas com datas inválidas (NaT) que quebrariam o gráfico
        df_completo = df_completo.dropna(subset=['data_inicio', 'data_fim'])

        # Filtrar pelo período selecionado
        mask = (df_completo['data_inicio'] >= pd.to_datetime(data_inicio)) & (df_completo['data_fim'] <= pd.to_datetime(data_fim))
        df_filtrado = df_completo.loc[mask]

        # Gráfico de Gantt
        st.subheader("Gráfico de Gantt")
        if not df_filtrado.empty:
            fig = px.timeline(
                df_filtrado, 
                x_start="data_inicio", 
                x_end="data_fim", 
                y="veiculo", 
                color="status" if "status" in df_filtrado.columns else None,
                # hover_data só se as colunas existirem
                hover_data=["cod_orcamento"] if "cod_orcamento" in df_filtrado.columns else None,
                title="Alocação por Veículo"
            )
            fig.update_yaxes(autorange="reversed") 
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            st.subheader("Detalhamento")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.info("Nenhum agendamento encontrado para este período.")
            
    except Exception as e:
        st.error(f"Erro ao gerar gráfico: {e}")
