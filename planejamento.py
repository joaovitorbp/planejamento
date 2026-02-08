import streamlit as st
import plotly.express as px
import pandas as pd
import conexao
from datetime import datetime

# --- Modal (Pop-up) de Agendamento ---
@st.dialog("Agendar Nova Atividade")
def modal_agendamento(df_obras, df_frota, df_time, df_agenda_atual):
    st.write("Preencha os dados abaixo.")

    # Preparar listas para os Dropdowns
    lista_projetos = df_obras['Projeto'].dropna().unique().tolist() if 'Projeto' in df_obras.columns else []
    lista_time = df_time['Nome'].dropna().unique().tolist() if not df_time.empty and 'Nome' in df_time.columns else []
    
    # Busca coluna de veículo (pode ser 'Veículo' ou 'Placa')
    col_veic = 'Veículo' if 'Veículo' in df_frota.columns else 'Placa'
    lista_veiculos = df_frota[col_veic].dropna().unique().tolist() if not df_frota.empty else []

    # Formulário
    projeto_selecionado = st.selectbox("Projeto", options=lista_projetos, index=None, placeholder="Selecione...")

    # Autopreenchimento de Descrição e Cliente
    desc_auto = ""
    cliente_auto = ""
    if projeto_selecionado:
        # Pega a primeira linha que corresponde ao projeto
        dados = df_obras[df_obras['Projeto'] == projeto_selecionado].iloc[0]
        desc_auto = dados.get('Descrição', "")
        # Junta Cliente + Cidade
        cliente_auto = f"{dados.get('Cliente', '')} - {dados.get('Cidade', '')}"

    descricao = st.text_input("Descrição", value=desc_auto, disabled=True) 
    cliente = st.text_input("Cliente", value=cliente_auto, disabled=True) 

    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data de Início", value=datetime.today())
    with col2:
        data_fim = st.date_input("Data de Término", value=datetime.today())

    executantes = st.multiselect("Executantes", options=lista_time)
    veiculo = st.selectbox("Veículo (Opcional)", options=lista_veiculos, index=None, placeholder="Selecione...")

    # Botão de Salvar
    if st.button("Salvar Agendamento", type="primary"):
        if not projeto_selecionado or not executantes:
            st.error("Projeto e Executantes são obrigatórios.")
            return

        with st.spinner("Salvando..."):
            # Cria nova linha
            nova_linha = pd.DataFrame([{
                "Projeto": projeto_selecionado,
                "Descrição": descricao,
                "Cliente": cliente,
                "Data Início": data_inicio.strftime('%Y-%m-%d'), # Já cria como String
                "Data Fim": data_fim.strftime('%Y-%m-%d'),       # Já cria como String
                "Executantes": ", ".join(executantes),
                "Veículo": veiculo if veiculo else "",
                "Status": "Planejado"
            }])

            # Concatena com o que já existe
            if df_agenda_atual.empty:
                df_final = nova_linha
            else:
                # Garante que df_agenda_atual tenha as colunas certas antes de concatenar
                # para evitar desalinhamento
                df_final = pd.concat([df_agenda_atual, nova_linha], ignore_index=True)

            # --- CORREÇÃO DO ERRO JSON ---
            # O Pandas pode ter convertido colunas antigas para Timestamp durante a visualização.
            # Aqui forçamos TUDO de volta para String (Texto) antes de enviar para o Google.
            try:
                # Converte para datetime primeiro para garantir, depois formata para String YYYY-MM-DD
                df_final['Data Início'] = pd.to_datetime(df_final['Data Início']).dt.strftime('%Y-%m-%d')
                df_final['Data Fim'] = pd.to_datetime(df_final['Data Fim']).dt.strftime('%Y-%m-%d')
                
                # Preenche valores vazios (NaN) com string vazia para não quebrar o JSON
                df_final = df_final.fillna("")
                
                # Salva
                conexao.salvar_no_sheets(df_final)
                st.success("Salvo com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

# --- Página Principal ---
def app():
    col_topo_1, col_topo_2 = st.columns([3, 1])
    col_topo_1.header("📅 Visualização do Planejamento")

    with st.spinner("Carregando dados..."):
        df_agenda, df_frota, df_time, df_obras = conexao.carregar_dados()

    # Botão que abre o Modal
    with col_topo_2:
        if st.button("➕ Agendar Atividade", use_container_width=True):
            modal_agendamento(df_obras, df_frota, df_time, df_agenda)

    if df_agenda.empty:
        st.info("Agenda vazia. Adicione o primeiro item.")
        return

    # Normalização de datas para o gráfico (Aqui transformamos em Timestamp para o Plotly usar)
    try:
        df_agenda['Data Início'] = pd.to_datetime(df_agenda['Data Início'], errors='coerce')
        df_agenda['Data Fim'] = pd.to_datetime(df_agenda['Data Fim'], errors='coerce')
        
        # Remove linhas com datas inválidas da visualização
        df_agenda_visualizacao = df_agenda.dropna(subset=['Data Início', 'Data Fim'])
    except Exception as e:
        st.error(f"Erro ao processar datas para o gráfico: {e}")
        st.dataframe(df_agenda) # Mostra a tabela crua se der erro
        return

    # Filtros de Data
    col1, col2 = st.columns(2)
    with col1:
        data_filtro_inicio = st.date_input("Filtrar de:", value=datetime.today())
    with col2:
        data_filtro_fim = st.date_input("Até:", value=datetime.today() + pd.Timedelta(days=30))

    # Aplica Filtro
    mask = (df_agenda_visualizacao['Data Início'] >= pd.to_datetime(data_filtro_inicio)) & \
           (df_agenda_visualizacao['Data Fim'] <= pd.to_datetime(data_filtro_fim))
    df_filtrado = df_agenda_visualizacao.loc[mask]

    # Gráfico de Gantt
    st.subheader("Cronograma")
    if not df_filtrado.empty:
        # Define Eixo Y (Veículo ou Projeto se Veículo for vazio)
        eixo_y = "Veículo"
        # Se a coluna Veículo estiver vazia ou não existir, usa Projeto
        if "Veículo" in df_filtrado.columns and df_filtrado["Veículo"].astype(str).str.strip().eq("").all():
            eixo_y = "Projeto"
        elif "Veículo" not in df_filtrado.columns:
             eixo_y = "Projeto"

        fig = px.timeline(
            df_filtrado, 
            x_start="Data Início", 
            x_end="Data Fim", 
            y=eixo_y, 
            color="Status" if "Status" in df_filtrado.columns else None,
            hover_data=["Projeto", "Cliente", "Executantes"],
            title=f"Cronograma por {eixo_y}"
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        st.subheader("Lista Detalhada")
        st.dataframe(df_filtrado, use_container_width=True)
    else:
        st.warning("Nenhuma atividade encontrada neste período.")
