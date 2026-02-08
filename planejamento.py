import streamlit as st
import plotly.express as px
import pandas as pd
import conexao
from datetime import datetime

# --- Modal (Pop-up) de Agendamento ---
@st.dialog("Agendar Nova Atividade")
def modal_agendamento(df_obras, df_frota, df_time, df_agenda_atual):
    st.write("Preencha os dados abaixo.")

    # Preparar listas
    lista_projetos = df_obras['Projeto'].dropna().unique().tolist() if 'Projeto' in df_obras.columns else []
    lista_time = df_time['Nome'].dropna().unique().tolist() if not df_time.empty and 'Nome' in df_time.columns else []
    
    col_veic = 'Veículo' if 'Veículo' in df_frota.columns else 'Placa'
    lista_veiculos = df_frota[col_veic].dropna().unique().tolist() if not df_frota.empty else []

    # Formulário
    projeto_selecionado = st.selectbox("Projeto", options=lista_projetos, index=None, placeholder="Selecione...")

    # Autopreenchimento
    desc_auto = ""
    cliente_auto = ""
    if projeto_selecionado:
        # Pega a primeira linha que corresponde ao projeto
        dados = df_obras[df_obras['Projeto'] == projeto_selecionado].iloc[0]
        desc_auto = dados.get('Descrição', "")
        # Junta Cliente + Cidade
        cliente_auto = f"{dados.get('Cliente', '')} - {dados.get('Cidade', '')}"

    descricao = st.text_input("Descrição", value=desc_auto, disabled=True) # Read-only
    cliente = st.text_input("Cliente", value=cliente_auto, disabled=True) # Read-only

    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data de Início", value=datetime.today())
    with col2:
        data_fim = st.date_input("Data de Término", value=datetime.today())

    executantes = st.multiselect("Executantes", options=lista_time)
    veiculo = st.selectbox("Veículo (Opcional)", options=lista_veiculos, index=None, placeholder="Selecione...")

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
                "Data Início": data_inicio.strftime('%Y-%m-%d'),
                "Data Fim": data_fim.strftime('%Y-%m-%d'),
                "Executantes": ", ".join(executantes), # Converte lista para texto
                "Veículo": veiculo if veiculo else "",
                "Status": "Planejado"
            }])

            # Concatena com o que já existe
            if df_agenda_atual.empty:
                df_final = nova_linha
            else:
                df_final = pd.concat([df_agenda_atual, nova_linha], ignore_index=True)

            try:
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

    # Normalização de datas para o gráfico
    try:
        df_agenda['Data Início'] = pd.to_datetime(df_agenda['Data Início'], errors='coerce')
        df_agenda['Data Fim'] = pd.to_datetime(df_agenda['Data Fim'], errors='coerce')
        df_agenda = df_agenda.dropna(subset=['Data Início', 'Data Fim'])
    except:
        st.dataframe(df_agenda) # Mostra a tabela crua se der erro
        return

    # Gráfico
    if not df_agenda.empty:
        # Usa Veículo no eixo Y, se não tiver, usa Projeto
        y_axis = "Veículo"
        if df_agenda["Veículo"].astype(str).str.strip().eq("").all():
            y_axis = "Projeto"

        fig = px.timeline(
            df_agenda, 
            x_start="Data Início", 
            x_end="Data Fim", 
            y=y_axis, 
            color="Status",
            hover_data=["Projeto", "Cliente", "Executantes"],
            title=f"Cronograma por {y_axis}"
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        st.dataframe(df_agenda, use_container_width=True)
