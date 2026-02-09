import streamlit as st
import plotly.express as px
import pandas as pd
import conexao
from datetime import datetime, timedelta
import calendar
import pytz 

# --- CONFIGURAÇÃO DE FUSO HORÁRIO ---
FUSO_BR = pytz.timezone('America/Sao_Paulo')

def get_hoje():
    return datetime.now(FUSO_BR).date()

# --- Função Auxiliar: Datas Padrão ---
def get_proxima_semana():
    hoje = get_hoje()
    dias_para_segunda = 7 - hoje.weekday()
    proxima_segunda = hoje + timedelta(days=dias_para_segunda)
    proxima_sexta = proxima_segunda + timedelta(days=4)
    return proxima_segunda, proxima_sexta

# --- Função Auxiliar: Situação e Cores ---
def calcular_situacao_e_cores(row):
    hoje = get_hoje()
    try:
        inicio = pd.to_datetime(row['Data Início']).date()
        fim = pd.to_datetime(row['Data Fim']).date()
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
        erros = []
        if not projeto_selecionado: erros.append("Projeto")
        if not executantes: erros.append("Executantes")
        if not data_inicio: erros.append("Data Início")
        if not data_fim: erros.append("Data Fim")

        if erros:
            st.error(f"Campos obrigatórios: {', '.join(erros)}")
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
    col_titulo, col_btn = st.columns([4, 1])
    col_titulo.header("📅 Cronograma")
    
    df_raw, df_frota, df_time, df_obras_raw = conexao.carregar_dados()
    df_agenda = df_raw.copy()
    df_obras = df_obras_raw.copy()

    with col_btn:
        if st.button("➕ Novo Agendamento", type="primary", use_container_width=True):
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
        st.error(f"Erro ao processar dados: {e}")
        return

    if df_processado.empty:
        st.warning("Sem dados válidos.")
        return

    df_processado[['Situacao', 'CorFill', 'CorLine']] = df_processado.apply(calcular_situacao_e_cores, axis=1)

    # --- BARRA DE VISUALIZAÇÃO ---
    st.divider()
    c_periodo, c_status = st.columns([2, 1])
    
    with c_periodo:
        periodo_opcao = st.radio(
            "Período de Visualização (Zoom):", # Alterei o nome para ficar claro
            ["30 Dias", "Mês Atual", "3 Meses", "Personalizado"],
            index=0,
            horizontal=True
        )
    
    with c_status:
        situacoes = ["Não Iniciada", "Em Andamento", "Concluída"]
        filtro_situacao = st.multiselect("Filtrar Status:", situacoes, default=situacoes)

    # --- CÁLCULO DAS DATAS DE ZOOM (APENAS PARA A CÂMERA DO GRÁFICO) ---
    hoje = get_hoje()
    
    if periodo_opcao == "30 Dias":
        zoom_inicio = hoje
        zoom_fim = hoje + timedelta(days=30)
    elif periodo_opcao == "Mês Atual":
        zoom_inicio = hoje.replace(day=1)
        _, last = calendar.monthrange(hoje.year, hoje.month)
        zoom_fim = hoje.replace(day=last)
    elif periodo_opcao == "3 Meses":
        zoom_inicio = hoje
        zoom_fim = hoje + timedelta(days=90)
    else:
        c1, c2 = st.columns(2)
        with c1:
            zoom_inicio = st.date_input("De:", value=hoje, format="DD/MM/YYYY")
        with c2:
            max_data = df_processado['Data Fim'].max().date()
            zoom_fim = st.date_input("Até:", value=max(hoje + timedelta(days=30), max_data), format="DD/MM/YYYY")

    # --- MUDANÇA CRÍTICA: FILTRO APENAS POR STATUS ---
    # Agora trazemos TUDO que tem o status selecionado, independente da data
    mask = df_processado['Situacao'].isin(filtro_situacao)
    df_filtrado = df_processado.loc[mask]

    if not df_filtrado.empty:
        # Ordenação
        mapa_ordem = {"Em Andamento": 1, "Não Iniciada": 2, "Concluída": 3}
        df_filtrado['Ordem'] = df_filtrado['Situacao'].map(mapa_ordem)
        df_filtrado = df_filtrado.sort_values(by=['Ordem', 'Data Início'])
        
        qtd_projetos = len(df_filtrado['Projeto'].unique())
        altura = max(300, qtd_projetos * 50)

        fig = px.timeline(
            df_filtrado, 
            x_start="Data Início", 
            x_end="Data Fim", 
            y="Projeto",
            text="Projeto", 
            height=altura,
            hover_data={
                "Projeto": True, "Descrição": True, "Cliente": True,
                "Executantes": True, "Situacao": True, "CorFill": False, "CorLine": False, "Ordem": False
            }
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
                
                # --- AQUI ESTÁ O "ZOOM" ---
                # Definimos o range inicial, mas os dados estão lá se arrastar
                range=[zoom_inicio, zoom_fim], 
                
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
            bargap=0.3
        )

        # Destaque HOJE
        fig.add_vrect(
            x0=hoje,
            x1=hoje + timedelta(days=1),
            fillcolor="#00FFFF", 
            opacity=0.15,        
            layer="below",       
            line_width=0
        )
        fig.add_vline(x=hoje, line_width=1, line_color="#00FFFF", line_dash="solid")
        
        fig.add_annotation(
            x=hoje, y=1, 
            yref="paper", text="HOJE", 
            showarrow=False, 
            font=dict(color="#00FFFF", weight="bold"),
            yshift=10,
            xshift=20 
        )

        # --- LOOP VISUAL (Background) ---
        # Agora precisamos garantir que o fundo seja desenhado para TODA a extensão dos dados
        # e não apenas para o zoom atual, senão ao arrastar, o fundo some.
        min_dados = df_filtrado['Data Início'].min().date()
        max_dados = df_filtrado['Data Fim'].max().date()
        
        # Margem generosa de 6 meses para trás e para frente do TODO
        visual_inicio = min(zoom_inicio, min_dados) - timedelta(days=180)
        visual_fim = max(zoom_fim, max_dados) + timedelta(days=180)
        
        curr_date = visual_inicio 
        
        while curr_date <= visual_fim: 
            if curr_date.weekday() in [5, 6]: 
                fig.add_vrect(
                    x0=curr_date, 
                    x1=curr_date + timedelta(days=1), 
                    fillcolor="white", 
                    opacity=0.08, 
                    layer="below", 
                    line_width=0
                )
            
            if curr_date.day == 1:
                fig.add_vline(
                    x=curr_date, 
                    line_width=3,         
                    line_color="#FFFFFF", 
                    opacity=0.8           
                )
                fig.add_annotation(
                    x=curr_date, y=0, yref="paper",
                    text=f"{curr_date.strftime('%b').upper()}", 
                    showarrow=False,
                    font=dict(color="#FFFFFF", size=14, weight="bold"), 
                    yshift=-30
                )

            curr_date += timedelta(days=1)

        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        st.subheader("Detalhamento")
        
        cols_tabela = ["Projeto", "Descrição", "Cliente", "Data Início", "Data Fim", "Executantes"]
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
        st.info("Nenhuma atividade encontrada neste período.")
