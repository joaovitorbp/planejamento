import streamlit as st
import plotly.express as px
import pandas as pd
import conexao
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# --- Mapeamento de Meses ---
MAPA_MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# --- Funções Auxiliares ---
def get_proxima_semana():
    hoje = datetime.now().date()
    dias_para_segunda = 7 - hoje.weekday()
    proxima_segunda = hoje + timedelta(days=dias_para_segunda)
    proxima_sexta = proxima_segunda + timedelta(days=4)
    return proxima_segunda, proxima_sexta

def calcular_situacao_e_cores(row):
    hoje = datetime.now().date()
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
        # Validação Obrigatória
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

    df_processado[['Situacao', 'CorFill', 'CorLine']] = df_processado.apply(calcular_situacao_e_cores, axis=1)

    # Filtros Padrão
    padrao_inicio = datetime.today().date()
    max_data = df_processado['Data Fim'].max().date()
    padrao_fim = max(padrao_inicio + timedelta(days=30), max_data)

    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        inicio = st.date_input("De:", value=padrao_inicio, format="DD/MM/YYYY")
    with f2:
        fim = st.date_input("Até:", value=padrao_fim, format="DD/MM/YYYY")
    with f3:
        situacoes = ["Não Iniciada", "Em Andamento", "Concluída"]
        filtro_situacao = st.multiselect("Filtrar Situação:", situacoes, default=situacoes)

    mask = (df_processado['Data Início'].dt.date >= inicio) & \
           (df_processado['Data Fim'].dt.date <= fim) & \
           (df_processado['Situacao'].isin(filtro_situacao))
    
    df_filtrado = df_processado.loc[mask]

    if not df_filtrado.empty:
        df_filtrado = df_filtrado.sort_values(by=['Data Início', 'Projeto'])
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
                "Executantes": True, "Situacao": True, "CorFill": False, "CorLine": False
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
            constraintext='none'
        )

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white", family="sans-serif"),
            
            # --- EIXO X (DIAS) ---
            xaxis=dict(
                title=None,
                tickformat="%d",     # Apenas 01, 02...
                side="top",         
                showgrid=True,
                gridcolor='#333333',
                dtick=86400000.0,    # 1 dia
                range=[inicio, fim],
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
                type='category'
            ),
            
            # --- MARGEM SUPERIOR GIGANTE (Para caber os meses sem sobrepor) ---
            margin=dict(t=140, b=10, l=0, r=0),
            showlegend=False,
            bargap=0.3
        )

        # --- ANOTAÇÕES DE MESES (Com Y ajustado para cima) ---
        # Lógica: Desenha o texto do mês manualmente acima do eixo de dias
        
        curr_mes = inicio.replace(day=1)
        # Margem de segurança para o loop
        loop_limit = fim + relativedelta(months=1)

        while curr_mes <= loop_limit:
            # Define o intervalo do mês corrente
            inicio_mes = curr_mes
            fim_mes = curr_mes + relativedelta(months=1) - timedelta(days=1)

            # Intersecção: O que deste mês está visível na tela?
            visivel_inicio = max(inicio, inicio_mes)
            visivel_fim = min(fim, fim_mes)

            # Se houver intersecção válida
            if visivel_inicio <= visivel_fim:
                # Calcula o ponto médio VISÍVEL (em datas)
                # Convertendo para timestamp para média aritmética precisa
                ts_inicio = visivel_inicio.toordinal()
                ts_fim = visivel_fim.toordinal()
                ts_meio = (ts_inicio + ts_fim) / 2
                centro_visivel = datetime.fromordinal(int(ts_meio))
                
                # Nome do mês
                nome_mes = f"{MAPA_MESES[curr_mes.month]} {curr_mes.year}".upper()

                # Adiciona o texto BEM ACIMA do gráfico
                # y=1.15 em relação ao topo da área de plotagem
                fig.add_annotation(
                    x=centro_visivel,
                    y=1.20, # <--- ALTURA AJUSTADA PARA NÃO SOBREPOR
                    yref="paper",
                    text=nome_mes,
                    showarrow=False,
                    font=dict(color="white", size=14, weight="bold")
                )
                
                # Opcional: Linha vertical sutil separando os meses
                if visivel_inicio == inicio_mes and visivel_inicio > inicio:
                     fig.add_vline(x=visivel_inicio, line_width=1, line_color="#444", line_dash="solid")

            # Vai para o próximo mês
            curr_mes += relativedelta(months=1)

        # Finais de Semana
        curr_date = inicio
        while curr_date <= fim:
            if curr_date.weekday() in [5, 6]:
                fig.add_vrect(
                    x0=curr_date, 
                    x1=curr_date + timedelta(days=1), 
                    fillcolor="white", 
                    opacity=0.08, 
                    layer="below", 
                    line_width=0
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
        st.info("Nenhuma atividade encontrada com os filtros selecionados.")
