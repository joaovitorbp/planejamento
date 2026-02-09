import streamlit as st
import plotly.express as px
import pandas as pd
import conexao
from datetime import datetime, timedelta
import calendar
import pytz 

# --- CONFIGURAÇÃO DE ESTILO (CSS REFINADO) ---
def aplicar_estilo():
    st.markdown("""
        <style>
        /* 1. Botões Primários (Azul Escuro) */
        div.stButton > button[kind="primary"] {
            background-color: #002B5B !important;
            border-color: #002B5B !important;
            color: white !important;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #004080 !important;
            border-color: #004080 !important;
        }
        
        /* 2. Tags do MultiSelect (Azul Escuro) */
        span[data-baseweb="tag"] {
            background-color: #002B5B !important;
            color: white !important;
        }
        
        /* 3. Botão de Edição (Estilo Texto/Link Minimalista) */
        div.stButton > button[kind="secondary"] {
            border: 1px solid #444;
            color: #ddd;
            background-color: transparent;
            height: auto;
            padding: 2px 8px; /* Compacto */
            font-size: 14px;
        }
        div.stButton > button[kind="secondary"]:hover {
            border-color: #002B5B;
            color: white;
            background-color: #002B5B;
        }
        
        /* 4. COMPACTAÇÃO EXTREMA DA TABELA */
        /* Remove margens extras dos textos dentro das colunas */
        div[data-testid="stMarkdownContainer"] p {
            font-size: 14px;
            margin-bottom: 0px !important;
        }
        
        /* Linha divisória fina e sem margem */
        hr {
            margin: 2px 0px !important; /* Margem quase zero */
            border-color: #333;
        }
        
        /* Ajuste do container da linha para reduzir gap vertical */
        div[data-testid="column"] {
            padding-bottom: 0px !important;
        }
        </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÃO DE FUSO E DATAS ---
FUSO_BR = pytz.timezone('America/Sao_Paulo')

def get_hoje():
    return datetime.now(FUSO_BR).date()

def get_proxima_semana():
    hoje = get_hoje()
    dias_para_segunda = 7 - hoje.weekday()
    proxima_segunda = hoje + timedelta(days=dias_para_segunda)
    proxima_sexta = proxima_segunda + timedelta(days=4)
    return proxima_segunda, proxima_sexta

def calcular_situacao_e_cores(row):
    hoje = get_hoje()
    try:
        inicio = pd.to_datetime(row['Data Início'], dayfirst=True).date()
        fim = pd.to_datetime(row['Data Fim'], dayfirst=True).date()
    except:
        return pd.Series(["Erro", "#000", "#000"])
    
    if inicio > hoje:
        situacao = "Não Iniciada"
        cor_fill = "#EF4444"
        cor_line = "#7F1D1D"
    elif fim < hoje:
        situacao = "Concluída"
        cor_fill = "#10B981"
        cor_line = "#064E3B"
    else:
        situacao = "Em Andamento"
        cor_fill = "#F59E0B"
        cor_line = "#78350F"
        
    return pd.Series([situacao, cor_fill, cor_line])

# --- DIALOGS ---

@st.dialog("Selecionar Período")
def modal_datas_personalizadas():
    st.write("Defina o período:")
    padrao_ini = st.session_state.get('zoom_ini', get_hoje())
    padrao_fim = st.session_state.get('zoom_fim', get_hoje() + timedelta(days=30))
    c1, c2 = st.columns(2)
    with c1: ini = st.date_input("De", value=padrao_ini, format="DD/MM/YYYY")
    with c2: fim = st.date_input("Até", value=padrao_fim, format="DD/MM/YYYY")
    if st.button("Aplicar Filtro", type="primary", use_container_width=True):
        st.session_state['zoom_ini'] = ini
        st.session_state['zoom_fim'] = fim
        st.session_state['view_mode'] = 'custom'
        st.rerun()

# --- MODAL DE EDIÇÃO ---
@st.dialog("Editar Atividade")
def modal_editar_atividade(index_original, df_full, lista_time):
    st.subheader("Alterar Dados")
    try:
        dados_atuais = df_full.loc[index_original]
    except KeyError:
        st.error("Atividade não encontrada.")
        return

    st.caption(f"Projeto: {dados_atuais['Projeto']} | Cliente: {dados_atuais['Cliente']}")
    st.text_input("Descrição", value=dados_atuais['Descrição'], disabled=True)

    try:
        dt_ini_atual = pd.to_datetime(dados_atuais['Data Início'], dayfirst=True).date()
        dt_fim_atual = pd.to_datetime(dados_atuais['Data Fim'], dayfirst=True).date()
    except:
        dt_ini_atual = get_hoje()
        dt_fim_atual = get_hoje()

    c1, c2 = st.columns(2)
    with c1: nova_data_ini = st.date_input("Início", value=dt_ini_atual, format="DD/MM/YYYY")
    with c2: nova_data_fim = st.date_input("Fim", value=dt_fim_atual, format="DD/MM/YYYY")

    equipe_atual = []
    if isinstance(dados_atuais['Executantes'], str):
        equipe_atual = [x.strip() for x in dados_atuais['Executantes'].split(',')]
    equipe_validada = [x for x in equipe_atual if x in lista_time]
    
    novos_executantes = st.multiselect("Executantes", options=lista_time, default=equipe_validada)

    if st.button("Salvar Alterações", type="primary"):
        if nova_data_fim < nova_data_ini:
            st.error("A data de término não pode ser antes do início.")
            return

        with st.spinner("Salvando..."):
            df_full.at[index_original, 'Data Início'] = nova_data_ini.strftime('%d/%m/%Y')
            df_full.at[index_original, 'Data Fim'] = nova_data_fim.strftime('%d/%m/%Y')
            df_full.at[index_original, 'Executantes'] = ", ".join(novos_executantes)
            
            df_full['Data Início'] = pd.to_datetime(df_full['Data Início'], dayfirst=True).dt.strftime('%d/%m/%Y')
            df_full['Data Fim'] = pd.to_datetime(df_full['Data Fim'], dayfirst=True).dt.strftime('%d/%m/%Y')
            df_full = df_full.fillna("")
            
            try:
                conexao.salvar_no_sheets(df_full)
                st.cache_data.clear()
                st.success("Salvo!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

@st.dialog("Novo Agendamento")
def modal_agendamento(df_obras, df_frota, df_time, df_agenda_atual):
    st.write("Preencha os dados abaixo:")
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
    with col1: data_inicio = st.date_input("Início", value=padrao_inicio, format="DD/MM/YYYY")
    with col2: data_fim = st.date_input("Fim", value=padrao_fim, format="DD/MM/YYYY")

    executantes = st.multiselect("Executantes", options=lista_time)
    veiculo = st.selectbox("Veículo (Opcional)", options=lista_veiculos, index=None, placeholder="Selecione...")

    if st.button("Salvar Agendamento", type="primary"):
        erros = []
        if not projeto_selecionado: erros.append("Selecione um Projeto")
        if not executantes: erros.append("Defina os Executantes")
        if not data_inicio: erros.append("Data de Início")
        if not data_fim: erros.append("Data de Fim")
        
        if data_inicio and data_fim and data_fim < data_inicio:
            erros.append("A data de término não pode ser antes do início.")

        if erros:
            st.error(f"Atenção: {', '.join(erros)}")
            return
        
        with st.spinner("Registrando..."):
            nova_linha = pd.DataFrame([{
                "Projeto": str(projeto_selecionado),
                "Descrição": descricao,
                "Cliente": cliente,
                "Data Início": data_inicio.strftime('%d/%m/%Y'),
                "Data Fim": data_fim.strftime('%d/%m/%Y'),
                "Executantes": ", ".join(executantes),
                "Veículo": veiculo if veiculo else "",
                "Status": "Planejado" 
            }])
            if df_agenda_atual.empty: df_final = nova_linha
            else: df_final = pd.concat([df_agenda_atual, nova_linha], ignore_index=True)
            try:
                df_final['Data Início'] = pd.to_datetime(df_final['Data Início'], dayfirst=True).dt.strftime('%d/%m/%Y')
                df_final['Data Fim'] = pd.to_datetime(df_final['Data Fim'], dayfirst=True).dt.strftime('%d/%m/%Y')
                df_final = df_final.fillna("")
                conexao.salvar_no_sheets(df_final)
                st.cache_data.clear()
                st.success("Agendamento realizado com sucesso!")
                st.rerun()
            except Exception as e: st.error(f"Houve um problema ao salvar: {e}")

# --- APP PRINCIPAL ---
def app():
    aplicar_estilo()
    
    col_titulo, col_btn = st.columns([4, 1])
    col_titulo.header("Cronograma")
    
    df_raw, df_frota, df_time, df_obras_raw = conexao.carregar_dados()
    df_agenda = df_raw.copy()
    df_obras = df_obras_raw.copy()
    
    lista_time_completa = df_time['Nome'].dropna().unique().tolist() if not df_time.empty and 'Nome' in df_time.columns else []

    with col_btn:
        if st.button("Novo Agendamento", type="primary", use_container_width=True):
            modal_agendamento(df_obras, df_frota, df_time, df_agenda)

    if df_agenda.empty:
        st.info("Nenhum agendamento.")
        return

    try:
        df_agenda['Data Início'] = pd.to_datetime(df_agenda['Data Início'], format='mixed', dayfirst=True, errors='coerce')
        df_agenda['Data Fim'] = pd.to_datetime(df_agenda['Data Fim'], format='mixed', dayfirst=True, errors='coerce')
        df_agenda['Projeto'] = df_agenda['Projeto'].astype(str).str.replace(r'\.0$', '', regex=True)
        df_processado = df_agenda.dropna(subset=['Data Início', 'Data Fim'])
    except Exception as e:
        st.error(f"Erro: {e}")
        return

    if df_processado.empty:
        st.warning("Sem dados válidos.")
        return
    
    df_processado['Fim_Visual'] = df_processado['Data Fim'] + timedelta(days=1)
    df_processado['Inicio_Fmt'] = df_processado['Data Início'].dt.strftime('%d/%m/%Y')
    df_processado['Fim_Fmt'] = df_processado['Data Fim'].dt.strftime('%d/%m/%Y')

    df_processado[['Situacao', 'CorFill', 'CorLine']] = df_processado.apply(calcular_situacao_e_cores, axis=1)

    hoje = get_hoje()
    if 'view_mode' not in st.session_state: st.session_state['view_mode'] = '30d'
    if 'zoom_ini' not in st.session_state: st.session_state['zoom_ini'] = hoje
    if 'zoom_fim' not in st.session_state: st.session_state['zoom_fim'] = hoje + timedelta(days=30)

    st.divider()
    c_botoes, c_status = st.columns([2, 1])
    
    with c_botoes:
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("30 Dias", use_container_width=True, type="primary" if st.session_state['view_mode']=='30d' else "secondary"):
            st.session_state['zoom_ini'] = hoje
            st.session_state['zoom_fim'] = hoje + timedelta(days=30)
            st.session_state['view_mode'] = '30d'
            st.rerun()
        if b2.button("Mês Atual", use_container_width=True, type="primary" if st.session_state['view_mode']=='mes' else "secondary"):
            st.session_state['zoom_ini'] = hoje.replace(day=1)
            _, last = calendar.monthrange(hoje.year, hoje.month)
            st.session_state['zoom_fim'] = hoje.replace(day=last)
            st.session_state['view_mode'] = 'mes'
            st.rerun()
        if b3.button("3 Meses", use_container_width=True, type="primary" if st.session_state['view_mode']=='3m' else "secondary"):
            st.session_state['zoom_ini'] = hoje
            st.session_state['zoom_fim'] = hoje + timedelta(days=90)
            st.session_state['view_mode'] = '3m'
            st.rerun()
        if b4.button("Personalizado", use_container_width=True, type="primary" if st.session_state['view_mode']=='custom' else "secondary"):
            modal_datas_personalizadas()

    with c_status:
        situacoes = ["Não Iniciada", "Em Andamento", "Concluída"]
        filtro_situacao = st.multiselect("Filtrar Status", situacoes, default=situacoes, label_visibility="collapsed", placeholder="Filtrar Status")

    mask = df_processado['Situacao'].isin(filtro_situacao)
    df_filtrado = df_processado.loc[mask]

    if not df_filtrado.empty:
        mapa_ordem = {"Em Andamento": 1, "Não Iniciada": 2, "Concluída": 3}
        df_filtrado['Ordem'] = df_filtrado['Situacao'].map(mapa_ordem)
        df_filtrado = df_filtrado.sort_values(by=['Ordem', 'Data Início'])

        qtd_projetos = len(df_filtrado['Projeto'].unique())
        altura_final = 100 + (qtd_projetos * 50)

        fig = px.timeline(
            df_filtrado, 
            x_start="Data Início", 
            x_end="Fim_Visual",
            y="Projeto",
            text="Projeto",
            height=altura_final,
            custom_data=['Inicio_Fmt', 'Fim_Fmt', 'Cliente', 'Descrição', 'Executantes']
        )
        
        fig.update_layout(
            hoverlabel=dict(bgcolor="#333333", font_color="white", font_size=12, font_family="sans-serif", bordercolor="#333333")
        )
        
        fig.update_traces(
            hovertemplate="<b>%{y}</b><br><br>" +
                          "Início: %{customdata[0]}<br>" +
                          "Término: %{customdata[1]}<br>" +
                          "Cliente: %{customdata[2]}<br>" +
                          "Descrição: %{customdata[3]}<br>" +
                          "Equipe: %{customdata[4]}<extra></extra>",
            customdata=df_filtrado[['Inicio_Fmt', 'Fim_Fmt', 'Cliente', 'Descrição', 'Executantes']],
            marker=dict(
                color=df_filtrado['CorFill'],
                line=dict(color=df_filtrado['CorLine'], width=1),
                cornerradius=10 
            ),
            textposition='inside', 
            insidetextanchor='start',
            textfont=dict(color='white', weight='bold', size=13),
            constraintext='none', 
            cliponaxis=False 
        )

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white", family="sans-serif"),
            dragmode="pan", 
            xaxis=dict(
                title=None,
                tickformat="%d/%m", 
                side="top",         
                showgrid=True,
                gridcolor='#333333',
                dtick=86400000.0,    
                range=[st.session_state['zoom_ini'], st.session_state['zoom_fim']], 
                ticklabelmode="period", 
                tickcolor='white',
                tickfont=dict(color='#cccccc', size=12)
            ),
            yaxis=dict(
                title=None,
                autorange="reversed", 
                showgrid=False,
                showticklabels=False, 
                visible=True,
                type='category',
                fixedrange=True
            ),
            margin=dict(t=50, b=10, l=0, r=0),
            showlegend=False,
            bargap=0.2 
        )

        # HOJE: COLADO NA BORDA INFERIOR
        fig.add_vrect(x0=hoje, x1=hoje + timedelta(days=1), fillcolor="#00FFFF", opacity=0.15, layer="below", line_width=0)
        fig.add_annotation(
            x=hoje, 
            y=0, # Base
            yref="paper", 
            yanchor="bottom", # Ancora pela base para colar na linha
            text="HOJE", 
            showarrow=False, 
            font=dict(color="#00FFFF", weight="bold"), 
            yshift=0, # Zero deslocamento
            xshift=20
        )

        min_dados = df_filtrado['Data Início'].min().date()
        max_dados = df_filtrado['Data Fim'].max().date()
        visual_inicio = min(st.session_state['zoom_ini'], min_dados) - timedelta(days=180)
        visual_fim = max(st.session_state['zoom_fim'], max_dados) + timedelta(days=180)
        
        curr_date = visual_inicio 
        while curr_date <= visual_fim: 
            if curr_date.weekday() in [5, 6]: 
                fig.add_vrect(x0=curr_date, x1=curr_date + timedelta(days=1), fillcolor="white", opacity=0.08, layer="below", line_width=0)
            if curr_date.day == 1:
                fig.add_vline(x=curr_date, line_width=3, line_color="#FFFFFF", opacity=0.8)
                fig.add_annotation(x=curr_date, y=0, yref="paper", text=f"{curr_date.strftime('%b').upper()}", showarrow=False, font=dict(color="#FFFFFF", size=14, weight="bold"), yshift=-30)
            curr_date += timedelta(days=1)

        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        st.subheader("Detalhamento das Atividades")
        
        # --- TABELA COMPACTA, ALINHADA E UNIFORME ---
        # Cabeçalho
        c_proj, c_desc, c_cli, c_ini, c_fim, c_equipe, c_acao = st.columns([2, 3, 2, 1.2, 1.2, 2, 0.8], vertical_alignment="center")
        c_proj.markdown("**Projeto**")
        c_desc.markdown("**Descrição**")
        c_cli.markdown("**Cliente**")
        c_ini.markdown("**Início**")
        c_fim.markdown("**Fim**")
        c_equipe.markdown("**Equipe**")
        c_acao.markdown("**Editar**")
        
        st.markdown("<hr>", unsafe_allow_html=True) 

        for idx, row in df_filtrado.iterrows():
            with st.container():
                # vertical_alignment="center" garante que tudo fique centralizado no eixo Y
                c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 3, 2, 1.2, 1.2, 2, 0.8], vertical_alignment="center")
                
                # Texto uniforme: Todos usam st.write para manter a mesma fonte/cor
                c1.write(f"{row['Projeto']}")
                
                # Truncar descrição apenas visualmente
                desc_curta = f"{row['Descrição'][:40]}..." if len(row['Descrição']) > 40 else row['Descrição']
                c2.write(desc_curta, help=row['Descrição']) # help mostra o tooltip nativo se precisar
                
                c3.write(row['Cliente'])
                c4.write(row['Inicio_Fmt'])
                c5.write(row['Fim_Fmt'])
                c6.write(row['Executantes'])
                
                # Ícone "Sem Cor" (Texto Unicode)
                if c7.button("✎", key=f"btn_edit_{idx}", type="secondary", use_container_width=True):
                    modal_editar_atividade(idx, df_agenda, lista_time_completa)
                
                st.markdown("<hr>", unsafe_allow_html=True) 

    else:
        st.info("Nenhuma atividade encontrada.")
