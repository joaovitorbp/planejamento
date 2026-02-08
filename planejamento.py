import streamlit as st
import plotly.express as px
import pandas as pd
import conexao
from datetime import datetime, timedelta
import calendar

# --- Inicialização do Estado (Para Botões de Período) ---
if 'filtro_data_inicio' not in st.session_state:
    st.session_state['filtro_data_inicio'] = datetime.today().date() - timedelta(days=5)
if 'filtro_data_fim' not in st.session_state:
    st.session_state['filtro_data_fim'] = datetime.today().date() + timedelta(days=35)

# --- Funções Auxiliares ---
def set_periodo(tipo):
    hoje = datetime.today().date()
    if tipo == "mes_atual":
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        st.session_state['filtro_data_inicio'] = hoje.replace(day=1)
        st.session_state['filtro_data_fim'] = hoje.replace(day=ultimo_dia)
    elif tipo == "prox_mes":
        mes_que_vem = (hoje.replace(day=1) + timedelta(days=32)).replace(day=1)
        ultimo_dia = calendar.monthrange(mes_que_vem.year, mes_que_vem.month)[1]
        st.session_state['filtro_data_inicio'] = mes_que_vem
        st.session_state['filtro_data_fim'] = mes_que_vem.replace(day=ultimo_dia)
    elif tipo == "3_meses":
        st.session_state['filtro_data_inicio'] = hoje
        st.session_state['filtro_data_fim'] = hoje + timedelta(days=90)

def get_proxima_semana():
    hoje = datetime.now().date()
    dias_para_segunda = 7 - hoje.weekday()
    proxima_segunda = hoje + timedelta(days=dias_para_segunda)
    proxima_sexta = proxima_segunda + timedelta(days=4)
    return proxima_segunda, proxima_sexta

def calcular_situacao_e_cores(row):
    hoje = datetime.now().date()
    inicio = pd.to_datetime(row['Data Início']).date()
    fim = pd.to_datetime(row['Data Fim']).date()
    
    if inicio > hoje:
        situacao = "Não Iniciada"
        cor_fill = "#EF4444"  # Vermelho
        cor_line = "#7F1D1D"  # Vermelho Escuro
    elif fim < hoje:
        situacao = "Concluída"
        cor_fill = "#10B981"  # Verde
        cor_line = "#064E3B"  # Verde Escuro
    else:
        situacao = "Em Andamento"
        cor_fill = "#F59E0B"  # Amarelo
        cor_line = "#78350F"  # Marrom
        
    return pd.Series([situacao, cor_fill, cor_line])

# --- Modal (Pop-up) ---
@st.dialog("Agendar Nova Atividade")
def modal_agendamento(df_obras, df_frota, df_time, df_agenda_atual):
    st.write("Novo Agendamento")

    lista_projetos = df_obras['Projeto'].astype(str).dropna().unique().tolist() if 'Projeto' in df_obras.columns else []
    lista_time = df_time['Nome'].dropna().unique().tolist() if not df_time.empty and 'Nome' in df_time.columns else []
    col_veic = 'Veículo' if 'Veículo' in df_frota.columns else 'Placa'
    lista_veiculos = df_frota[col_veic].dropna().unique().tolist() if not df_frota.empty else []

    projeto_selecionado = st.selectbox("Projeto", options=lista_projetos, index=None, placeholder="Selecione...")

    desc_auto = ""
    cliente_auto = ""
    if projeto_selecionado:
        df_obras['Projeto'] = df_obras['Projeto'].astype(str)
        dados = df_obras[df_obras['Projeto'] == str(projeto_selecionado)].iloc[0]
        if 'Descricao' in dados: desc_auto = dados['Descricao']
        elif 'Descrição' in dados: desc_auto = dados['Descrição']
        cliente_auto = f"{dados.get('Cliente', '')} - {dados.get('Cidade', '')}"

    descricao = st.text_input("Descrição", value=desc_auto, disabled=True) 
    cliente = st.text_input("Cliente", value=cliente_auto, disabled=True) 

    padrao_inicio, padrao_fim = get_proxima_semana()

    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Início", value=padrao_inicio, format="DD/MM/YYYY")
    with col2:
        data_fim = st.date_input("Fim", value=padrao_fim, format="DD/MM/YYYY")

    executantes = st.multiselect("Executantes", options=lista_time)
    veiculo = st.selectbox("Veículo (Opcional)", options=lista_veiculos, index=None, placeholder="Selecione...")

    if st.button("Salvar", type="primary"):
        if not projeto_selecionado:
            st.error("Selecione um projeto.")
            return

        with st.spinner("Salvando..."):
            nova_linha = pd.DataFrame([{
                "Projeto": str(projeto_selecionado),
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
                st.cache_data.clear()
                st.success("Salvo!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

# --- App Principal ---
def app():
    col1, col2 = st.columns([3, 1])
    col1.header("📅 Cronograma")

    df_raw, df_frota, df_time, df_obras_raw = conexao.carregar_dados()
    df_agenda = df_raw.copy()
    df_obras = df_obras_raw.copy()

    with col2:
        if st.button("➕ Agendar", use_container_width=True):
            modal_agendamento(df_obras, df_frota, df_time, df_agenda)

    if df_agenda.empty:
        st.info("Nenhum agendamento.")
        return

    # Tratamento de Dados
    try:
        df_agenda['Data Início'] = pd.to_datetime(df_agenda['Data Início'], format='mixed', dayfirst=True, errors='coerce')
        df_agenda['Data Fim'] = pd.to_datetime(df_agenda['Data Fim'], format='mixed', dayfirst=True, errors='coerce')
        df_agenda['Projeto'] = df_agenda['Projeto'].astype(str).apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
        df_processado = df_agenda.dropna(subset=['Data Início', 'Data Fim'])
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return

    if df_processado.empty:
        st.warning("Sem dados válidos.")
        return

    # Aplica Cores
    df_processado[['Situacao', 'CorFill', 'CorLine']] = df_processado.apply(calcular_situacao_e_cores, axis=1)

    # Controles de Tempo
    st.markdown("### Seleção de Período")
    b1, b2, b3, space = st.columns([1, 1, 1, 3])
    if b1.button("Mês Atual", use_container_width=True):
        set_periodo("mes_atual")
        st.rerun()
    if b2.button("Próximo Mês", use_container_width=True):
        set_periodo("prox_mes")
        st.rerun()
    if b3.button("Próx. 3 Meses", use_container_width=True):
        set_periodo("3_meses")
        st.rerun()

    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        inicio = st.date_input("De:", value=st.session_state['filtro_data_inicio'], format="DD/MM/YYYY", key="d_ini")
    with f2:
        fim = st.date_input("Até:", value=st.session_state['filtro_data_fim'], format="DD/MM/YYYY", key="d_fim")
    with f3:
        situacoes_padrao = ["Não Iniciada", "Em Andamento", "Concluída"]
        filtro_situacao = st.multiselect("Filtrar Situação:", situacoes_padrao, default=situacoes_padrao)

    st.session_state['filtro_data_inicio'] = inicio
    st.session_state['filtro_data_fim'] = fim

    mask = (df_processado['Data Início'].dt.date >= inicio) & \
           (df_processado['Data Fim'].dt.date <= fim) & \
           (df_processado['Situacao'].isin(filtro_situacao))
    
    df_filtrado = df_processado.loc[mask]

    # GRÁFICO
    if not df_filtrado.empty:
        df_filtrado = df_filtrado.sort_values(by=['Data Início', 'Projeto'])
        
        # --- CÁLCULO DE ALTURA INFINITA ---
        # 60 pixels por projeto. Se tiver 100 projetos = 6000px de altura.
        qtd_projetos_unicos = len(df_filtrado['Projeto'].unique())
        # Mínimo de 400px, sem limite máximo.
        altura_dinamica = max(400, qtd_projetos_unicos * 60) + 100

        # Cria HTML para o Hover (Card)
        df_filtrado['Hover_HTML'] = df_filtrado.apply(lambda x: (
            f"<b>{x['Projeto']}</b><br>"
            f"<i>{x['Descrição']}</i><br><br>"
            f"👤 <b>Cliente:</b> {x['Cliente']}<br>"
            f"👷 <b>Equipe:</b> {x['Executantes']}<br>"
            f"📅 <b>Período:</b> {pd.to_datetime(x['Data Início']).strftime('%d/%m')} a {pd.to_datetime(x['Data Fim']).strftime('%d/%m')}<br>"
            f"🚦 <b>Status:</b> {x['Situacao']}"
        ), axis=1)

        fig = px.timeline(
            df_filtrado, 
            x_start="Data Início", 
            x_end="Data Fim", 
            y="Projeto",
            text="Projeto",
            height=altura_dinamica, # Altura aplicada aqui
            custom_data=["Hover_HTML"]
        )

        fig.update_traces(
            marker=dict(
                color=df_filtrado['CorFill'],
                line=dict(color=df_filtrado['CorLine'], width=1),
                cornerradius=5
            ),
            textposition='inside', 
            insidetextanchor='start',
            textfont=dict(color='white', weight='bold', size=13),
            hovertemplate="%{customdata[0]}<extra></extra>"
        )

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white", family="sans-serif"),
            
            xaxis=dict(
                title=None,
                tickformat="%d/%m<br>%a", # 02/09 (enter) Seg
                side="top",         
                showgrid=True,
                gridcolor='#333333',
                dtick=86400000.0, # 1 dia exato
                range=[inicio - timedelta(days=1), fim + timedelta(days=1)],
                tickcolor='white',
                tickfont=dict(color='#cccccc', size=12)
            ),
            
            yaxis=dict(
                title=None,
                autorange="reversed", 
                showgrid=False,
                showticklabels=False, 
                visible=True,
                type='category'
            ),
            
            margin=dict(t=60, b=10, l=0, r=0),
            showlegend=False,
            bargap=0.3
        )

        # Linha de Hoje
        fig.add_vline(x=datetime.today(), line_width=2, line_color="#FF4500", opacity=0.8)
        fig.add_annotation(
            x=datetime.today(), y=0, text="HOJE", 
            showarrow=False, yref="paper", yshift=-20,
            font=dict(color="#FF4500", weight="bold")
        )

        # Finais de Semana (Fundo)
        curr_date = inicio
        while curr_date <= fim:
            if curr_date.weekday() in [5, 6]:
                fig.add_vrect(
                    x0=curr_date, 
                    x1=curr_date + timedelta(days=1), 
                    fillcolor="black", 
                    opacity=0.3, 
                    layer="below", 
                    line_width=0
                )
            curr_date += timedelta(days=1)

        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        st.subheader("📋 Detalhamento")
        
        cols_tabela = ["Projeto", "Descrição", "Cliente", "Data Início", "Data Fim", "Executantes", "Situacao"]
        cols_finais = [c for c in cols_tabela if c in df_filtrado.columns]
        df_tabela = df_filtrado[cols_finais].copy()
        
        df_tabela["Data Início"] = pd.to_datetime(df_tabela["Data Início"]).dt.date
        df_tabela["Data Fim"] = pd.to_datetime(df_tabela["Data Fim"]).dt.date

        st.dataframe(
            df_tabela,
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Data Início": st.column_config.DateColumn("Início", format="DD/MM/YYYY"),
                "Data Fim": st.column_config.DateColumn("Fim", format="DD/MM/YYYY"),
            }
        )
    else:
        st.info("Nenhuma atividade encontrada com os filtros selecionados.")
