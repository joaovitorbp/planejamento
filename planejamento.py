import streamlit as st
import plotly.express as px
import pandas as pd
import conexao
from datetime import datetime

# --- Modal (Pop-up) de Agendamento ---
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

    # Autopreenchimento
    desc_auto = ""
    cliente_auto = ""
    if projeto_selecionado:
        dados = df_obras[df_obras['Projeto'] == projeto_selecionado].iloc[0]
        # Correção da coluna 'descricao' (minúscula)
        desc_auto = dados.get('descricao', "") 
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
                # Sanitização
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
    col_topo_1.header("📅 Cronograma de Obras")

    with st.spinner("Carregando dados..."):
        df_agenda, df_frota, df_time, df_obras = conexao.carregar_dados()

    with col_topo_2:
        if st.button("➕ Agendar", use_container_width=True):
            modal_agendamento(df_obras, df_frota, df_time, df_agenda)

    if df_agenda.empty:
        st.info("Agenda vazia.")
        return

    # --- 1. Processamento ---
    try:
        # Força leitura correta de dia/mês
        df_agenda['Data Início'] = pd.to_datetime(df_agenda['Data Início'], dayfirst=True, errors='coerce')
        df_agenda['Data Fim'] = pd.to_datetime(df_agenda['Data Fim'], dayfirst=True, errors='coerce')
        df_processado = df_agenda.dropna(subset=['Data Início', 'Data Fim'])
    except Exception as e:
        st.error(f"Erro nas datas: {e}")
        return

    if df_processado.empty:
        st.warning("Sem dados válidos.")
        return

    # --- 2. Filtros (Padrão: Todo o período encontrado) ---
    min_date = df_processado['Data Início'].min().date()
    max_date = df_processado['Data Fim'].max().date()
    # Adiciona uma margem de segurança visual (5 dias antes e depois)
    visual_min = min_date - pd.Timedelta(days=5)
    visual_max = max_date + pd.Timedelta(days=5)

    col1, col2 = st.columns(2)
    with col1:
        data_filtro_inicio = st.date_input("De:", value=min_date, format="DD/MM/YYYY")
    with col2:
        data_filtro_fim = st.date_input("Até:", value=max_date, format="DD/MM/YYYY")

    mask = (df_processado['Data Início'].dt.date >= data_filtro_inicio) & \
           (df_processado['Data Fim'].dt.date <= data_filtro_fim)
    df_filtrado = df_processado.loc[mask]

    # --- 3. Visualização "Estilo Gantt Nativo" ---
    if not df_filtrado.empty:
        eixo_y = "Veículo"
        if "Veículo" not in df_filtrado.columns or df_filtrado["Veículo"].astype(str).str.strip().eq("").all():
             eixo_y = "Projeto"
        
        # Ordenação
        df_filtrado = df_filtrado.sort_values(by=[eixo_y, 'Data Início'])
        
        # Cálculo de altura dinâmica (para não espremer as barras)
        altura_dinamica = 300 + (len(df_filtrado) * 40)

        # Configura o Gráfico
        fig = px.timeline(
            df_filtrado, 
            x_start="Data Início", 
            x_end="Data Fim", 
            y=eixo_y, 
            color="Status",
            text="Projeto", # <--- ISSO COLOCA O NOME DENTRO DA BARRA
            hover_data=["Cliente", "Executantes", "Descrição"],
            height=altura_dinamica
        )

        # --- A "MAQUIAGEM" PROFISSIONAL ---
        fig.update_layout(
            plot_bgcolor='white',  # Fundo branco limpo
            xaxis=dict(
                title="",
                tickformat="%d/%m",   # Data BR no eixo X
                tickmode="linear",    # Força aparecer todos os ticks se possível
                dtick=86400000.0,     # Força grade de 1 dia (em milissegundos)
                gridcolor='#eee',     # Grade cinza bem claro
                showgrid=True,
                side="top"            # Datas no topo (igual Project/Excel)
            ),
            yaxis=dict(title="", showgrid=True, gridcolor='#eee'),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        # Formatação das Barras
        fig.update_traces(
            textposition='inside', # Texto dentro da barra
            insidetextanchor='start', # Texto alinhado à esquerda
            marker_line_width=0,    # Sem borda preta grossa
            opacity=0.9
        )

        # Adiciona Linha do "HOJE"
        fig.add_vline(x=datetime.today(), line_width=2, line_dash="dash", line_color="red", annotation_text="Hoje")

        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Tabela Detalhada Limpa
        df_exibicao = df_filtrado.copy()
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
    else:
        st.warning("Nenhum planejamento encontrado.")
