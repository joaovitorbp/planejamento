import streamlit as st
import plotly.express as px
import pandas as pd
import conexao

def app():
    st.header("📅 Visualização do Planejamento")

    # Carregar Dados
    with st.spinner("Carregando dados do Google..."):
        df_agenda, df_frota, df_obras = conexao.carregar_dados()

    if df_agenda.empty:
        st.warning("A agenda está vazia.")
        return

    # Merge: Cruzar Agenda com Obras para pegar detalhes (Nome da Obra, Cliente, etc)
    # Assumindo que ambos tenham a coluna 'cod_orcamento'
    try:
        df_completo = pd.merge(df_agenda, df_obras, on='cod_orcamento', how='left')
    except Exception as e:
        st.error(f"Erro ao cruzar dados (verifique nomes das colunas): {e}")
        df_completo = df_agenda

    # Filtros de Data
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data Início", value=pd.to_datetime("today"))
    with col2:
        data_fim = st.date_input("Data Fim", value=pd.to_datetime("today") + pd.Timedelta(days=30))

    # Converter colunas de data para datetime
    df_completo['data_inicio'] = pd.to_datetime(df_completo['data_inicio'])
    df_completo['data_fim'] = pd.to_datetime(df_completo['data_fim'])

    # Filtrar
    mask = (df_completo['data_inicio'] >= pd.to_datetime(data_inicio)) & (df_completo['data_fim'] <= pd.to_datetime(data_fim))
    df_filtrado = df_completo.loc[mask]

    # Gráfico de Gantt
    st.subheader("Gráfico de Gantt")
    if not df_filtrado.empty:
        fig = px.timeline(
            df_filtrado, 
            x_start="data_inicio", 
            x_end="data_fim", 
            y="veiculo", # Ou 'equipe', ou 'nome_obra'
            color="status", # Assumindo que existe uma coluna status
            hover_data=["cod_orcamento", "obs"],
            title="Alocação por Veículo"
        )
        fig.update_yaxes(autorange="reversed") # Ordem correta
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        st.subheader("Detalhamento")
        st.dataframe(df_filtrado, use_container_width=True)
    else:
        st.info("Nenhum planejamento encontrado para este período.")
