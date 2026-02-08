import streamlit as st
import pandas as pd
import conexao
from datetime import datetime
from streamlit_timeline import timeline # <--- A NOVA BIBLIOTECA

# --- Modal (Pop-up) de Agendamento (MANTIDO IGUAL) ---
@st.dialog("Agendar Nova Atividade")
def modal_agendamento(df_obras, df_frota, df_time, df_agenda_atual):
    st.write("Preencha os dados abaixo.")

    # Listas
    lista_projetos = df_obras['Projeto'].dropna().unique().tolist() if 'Projeto' in df_obras.columns else []
    lista_time = df_time['Nome'].dropna().unique().tolist() if not df_time.empty and 'Nome' in df_time.columns else []
    col_veic = 'Veículo' if 'Veículo' in df_frota.columns else 'Placa'
    lista_veiculos = df_frota[col_veic].dropna().unique().tolist() if not df_frota.empty else []

    # Formulário
    projeto_selecionado = st.selectbox("Projeto", options=lista_projetos, index=None, placeholder="Selecione...")

    desc_auto = ""
    cliente_auto = ""
    if projeto_selecionado:
        dados = df_obras[df_obras['Projeto'] == projeto_selecionado].iloc[0]
        desc_auto = dados.get('descricao', "") 
        cliente_auto = f"{dados.get('Cliente', '')} - {dados.get('Cidade', '')}"

    descricao = st.text_input("Descrição", value=desc_auto, disabled=True) 
    cliente = st.text_input("Cliente", value=cliente_auto, disabled=True) 

    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Início", value=datetime.today(), format="DD/MM/YYYY")
    with col2:
        data_fim = st.date_input("Fim", value=datetime.today(), format="DD/MM/YYYY")

    executantes = st.multiselect("Executantes", options=lista_time)
    veiculo = st.selectbox("Veículo (Opcional)", options=lista_veiculos, index=None, placeholder="Selecione...")

    if st.button("Salvar Agendamento", type="primary"):
        if not projeto_selecionado or not executantes:
            st.error("Campos obrigatórios faltando.")
            return

        with st.spinner("Salvando..."):
            nova_linha = pd.DataFrame([{
                "Projeto": projeto_selecionado,
                "Descrição": descricao,
                "Cliente": cliente,
                "Data Início": data_inicio.strftime('%Y-%m-%d'),
                "Data Fim": data_fim.strftime('%Y-%m-%d'),
                "Executantes": ", ".join(executantes),
                "Veículo": veiculo if veiculo else "",
                "Status": "Planejado"
            }])

            if df_agenda_atual.empty:
                df_final = nova_linha
            else:
                df_final = pd.concat([df_agenda_atual, nova_linha], ignore_index=True)

            try:
                df_final['Data Início'] = pd.to_datetime(df_final['Data Início'], dayfirst=True).dt.strftime('%Y-%m-%d')
                df_final['Data Fim'] = pd.to_datetime(df_final['Data Fim'], dayfirst=True).dt.strftime('%Y-%m-%d')
                df_final = df_final.fillna("")
                conexao.salvar_no_sheets(df_final)
                st.success("Salvo!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

# --- App Principal ---
def app():
    col_topo_1, col_topo_2 = st.columns([3, 1])
    col_topo_1.header("📅 Timeline de Projetos")

    with st.spinner("Carregando dados..."):
        df_agenda, df_frota, df_time, df_obras = conexao.carregar_dados()

    with col_topo_2:
        if st.button("➕ Novo Evento", use_container_width=True):
            modal_agendamento(df_obras, df_frota, df_time, df_agenda)

    if df_agenda.empty:
        st.info("Agenda vazia.")
        return

    # Processamento de Datas
    try:
        df_agenda['Data Início'] = pd.to_datetime(df_agenda['Data Início'], dayfirst=True, errors='coerce')
        df_agenda['Data Fim'] = pd.to_datetime(df_agenda['Data Fim'], dayfirst=True, errors='coerce')
        df_processado = df_agenda.dropna(subset=['Data Início', 'Data Fim'])
    except:
        st.error("Erro nos dados.")
        return

    if df_processado.empty:
        st.warning("Sem datas válidas.")
        return

    # --- PREPARAÇÃO PARA A TIMELINE NATIVA ---
    # A biblioteca exige um JSON específico. Vamos transformar o DataFrame nele.
    items = []
    
    # Cores baseadas no Status para ficar bonito
    cores_status = {
        "Planejado": "#3498db",  # Azul
        "Confirmado": "#f1c40f", # Amarelo
        "Executado": "#2ecc71",  # Verde
        "Cancelado": "#e74c3c"   # Vermelho
    }

    for _, row in df_processado.iterrows():
        # Define a cor de fundo do slide baseada no status
        cor_fundo = cores_status.get(row.get("Status"), "#bdc3c7")
        
        item = {
            "start_date": {
                "year": row['Data Início'].year,
                "month": row['Data Início'].month,
                "day": row['Data Início'].day
            },
            "end_date": {
                "year": row['Data Fim'].year,
                "month": row['Data Fim'].month,
                "day": row['Data Fim'].day
            },
            "text": {
                "headline": f"{row['Projeto']} <br><small>({row.get('Veículo', 'Sem Veículo')})</small>",
                "text": f"<b>Cliente:</b> {row.get('Cliente', '')}<br><b>Equipe:</b> {row.get('Executantes', '')}<br><b>Status:</b> {row.get('Status', '')}"
            },
            "group": row.get('Veículo', 'Geral'), # Agrupa visualmente se quiser (opcional)
            # A biblioteca suporta customização de fundo (background)
            "background": { 
                "color": cor_fundo,
                "opacity": 0.2 
            }
        }
        items.append(item)

    # Estrutura final do JSON
    timeline_data = {
        "title": {
            "media": {
              "url": "",
              "caption": "",
              "credit": ""
            },
            "text": {
              "headline": "Planejamento de Obras",
              "text": "Cronograma interativo de execução e frotas."
            }
        },
        "events": items
    }

    # --- RENDERIZAÇÃO DA TIMELINE ---
    # height ajusta a altura da caixa interativa
    timeline(timeline_data, height=600)
    
    st.divider()
    
    # Tabela de Apoio (Mantida simples)
    st.subheader("Dados em Tabela")
    df_exibicao = df_processado.copy()
    df_exibicao["Data Início"] = df_exibicao["Data Início"].dt.date
    df_exibicao["Data Fim"] = df_exibicao["Data Fim"].dt.date
    
    st.dataframe(
        df_exibicao,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Data Início": st.column_config.DateColumn("Início", format="DD/MM/YYYY"),
            "Data Fim": st.column_config.DateColumn("Fim", format="DD/MM/YYYY")
        }
    )
