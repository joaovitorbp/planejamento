import streamlit as st
import plotly.express as px
import pandas as pd
import conexao
from datetime import datetime, date

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
        
        # --- CORREÇÃO SOLICITADA: Coluna 'descricao' (sem acento) ---
        desc_auto = dados.get('descricao', "") 
        
        # Junta Cliente + Cidade
        cliente_auto = f"{dados.get('Cliente', '')} - {dados.get('Cidade', '')}"

    descricao = st.text_input("Descrição", value=desc_auto, disabled=True) 
    cliente = st.text_input("Cliente", value=cliente_auto, disabled=True) 

    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data de Início", value=datetime.today(), format="DD/MM/YYYY")
    with col2:
        data_fim = st.date_input("Data de Término", value=datetime.today(), format="DD/MM/YYYY")

    executantes = st.multiselect("Executantes", options=lista_time)
    veiculo = st.selectbox("Veículo (Opcional)", options=lista_veiculos, index=None, placeholder="Selecione...")

    if st.button("Salvar Agendamento", type="primary"):
        if not projeto_selecionado or not executantes:
            st.error("Projeto e Executantes são obrigatórios.")
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
                # Sanitização para o Google Sheets (Garante YYYY-MM-DD)
                df_final['Data Início'] = pd.to_datetime(df_final['Data Início'], dayfirst=True).dt.strftime('%Y-%m-%d')
                df_final['Data Fim'] = pd.to_datetime(df_final['Data Fim'], dayfirst=True).dt.strftime('%Y-%m-%d')
                df_final = df_final.fillna("")
                
                conexao.salvar_no_sheets(df_final)
                st.success("Salvo com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

# --- App Principal ---
def app():
    col_topo_1, col_topo_2 = st.columns([3, 1])
    col_topo_1.header("📅 Visualização do Planejamento")

    with st.spinner("Carregando dados..."):
        df_agenda, df_frota, df_time, df_obras = conexao.carregar_dados()

    with col_topo_2:
        if st.button("➕ Agendar Atividade", use_container_width=True):
            modal_agendamento(df_obras, df_frota, df_time, df_agenda)

    if df_agenda.empty:
        st.info("Agenda vazia.")
        return

    # --- 1. Processamento ROBUSTO de Datas (Para corrigir o problema de sumir atividades) ---
    try:
        # dayfirst=True ajuda o pandas a entender que 07/02 é 7 de Fev, não 2 de Julho (se vier do sheets em BR)
        df_agenda['Data Início'] = pd.to_datetime(df_agenda['Data Início'], dayfirst=True, errors='coerce')
        df_agenda['Data Fim'] = pd.to_datetime(df_agenda['Data Fim'], dayfirst=True, errors='coerce')
        
        # Remove apenas linhas onde REALMENTE não tem data válida
        df_processado = df_agenda.dropna(subset=['Data Início', 'Data Fim'])
    except Exception as e:
        st.error(f"Erro ao ler datas: {e}")
        st.dataframe(df_agenda)
        return

    if df_processado.empty:
        st.warning("Não há atividades com datas válidas para exibir.")
        return

    # --- 2. Filtros Inteligentes (Para mostrar TUDO por padrão) ---
    # Pega a menor e a maior data da planilha para definir o padrão do filtro
    min_date = df_processado['Data Início'].min().date()
    max_date = df_processado['Data Fim'].max().date()

    col1, col2 = st.columns(2)
    with col1:
        data_filtro_inicio = st.date_input("Filtrar de:", value=min_date, format="DD/MM/YYYY")
    with col2:
        # Adicionei um buffer de +30 dias no fim só por segurança, mas o padrão cobre tudo
        data_filtro_fim = st.date_input("Até:", value=max_date, format="DD/MM/YYYY")

    # Aplica Filtro
    mask = (df_processado['Data Início'].dt.date >= data_filtro_inicio) & \
           (df_processado['Data Fim'].dt.date <= data_filtro_fim)
    df_filtrado = df_processado.loc[mask]

    # --- 3. Visualização MELHORADA ---
    if not df_filtrado.empty:
        # Define Eixo Y
        eixo_y = "Veículo"
        if "Veículo" not in df_filtrado.columns or df_filtrado["Veículo"].astype(str).str.strip().eq("").all():
             eixo_y = "Projeto"

        # Ordena para o gráfico ficar bonito (agrupa os veículos)
        df_filtrado = df_filtrado.sort_values(by=[eixo_y, 'Data Início'])

        # Altura dinâmica: Se tiver muitas atividades, o gráfico cresce para não ficar espremido
        altura_grafico = 400 + (len(df_filtrado) * 30)

        # Mapa de Cores para o Status (pode ajustar as cores hexadecimais)
        mapa_cores = {
            "Planejado": "#3498db",  # Azul
            "Confirmado": "#f1c40f", # Amarelo
            "Executado": "#2ecc71",  # Verde
            "Cancelado": "#e74c3c"   # Vermelho
        }

        fig = px.timeline(
            df_filtrado, 
            x_start="Data Início", 
            x_end="Data Fim", 
            y=eixo_y, 
            color="Status" if "Status" in df_filtrado.columns else None,
            color_discrete_map=mapa_cores, # Aplica cores fixas
            hover_data={
                "Projeto": True, 
                "Cliente": True, 
                "Executantes": True,
                "Status": False, # Já está na cor
                "Data Início": "|%d/%m/%Y", # Formata data no hover
                "Data Fim": "|%d/%m/%Y"
            },
            title=f"Cronograma por {eixo_y}",
            height=altura_grafico
        )

        # Melhora o Layout do Gráfico
        fig.update_layout(
            xaxis_title="Linha do Tempo",
            yaxis_title=eixo_y,
            showlegend=True,
            xaxis=dict(
                tickformat="%d/%m", # Mostra Dia/Mês no eixo X
                gridcolor='lightgray',
                dtick="D7" # Marcação a cada 7 dias (semanal)
            ),
            bargap=0.2 # Espaço entre as barras
        )
        
        # Deixa as barras com borda arredondada e opacidade (visual moderno)
        fig.update_traces(marker_line_color='rgb(8,48,107)', marker_line_width=1.5, opacity=0.9)
        fig.update_yaxes(autorange="reversed") # Ordem correta (topo para baixo)
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        st.subheader("Lista Detalhada")
        
        # Tabela Formatada
        df_exibicao = df_filtrado.copy()
        df_exibicao["Data Início"] = df_exibicao["Data Início"].dt.date
        df_exibicao["Data Fim"] = df_exibicao["Data Fim"].dt.date
        
        st.dataframe(
            df_exibicao, 
            use_container_width=True,
            hide_index=True,
            column_config={
                "Data Início": st.column_config.DateColumn("Início", format="DD/MM/YYYY"),
                "Data Fim": st.column_config.DateColumn("Fim", format="DD/MM/YYYY"),
                "Status": st.column_config.Column(
                    "Status",
                    width="small",
                    help="Status atual da atividade"
                )
            }
        )
    else:
        st.warning(f"Nenhuma atividade encontrada entre {data_filtro_inicio.strftime('%d/%m/%Y')} e {data_filtro_fim.strftime('%d/%m/%Y')}.")
