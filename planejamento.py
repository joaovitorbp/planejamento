import streamlit as st
import plotly.express as px
import pandas as pd
import conexao
from datetime import datetime, timedelta

# --- Função Auxiliar: Datas Padrão (Próxima Semana) ---
def get_proxima_semana():
    hoje = datetime.now().date()
    dias_para_segunda = 7 - hoje.weekday()
    proxima_segunda = hoje + timedelta(days=dias_para_segunda)
    proxima_sexta = proxima_segunda + timedelta(days=4)
    return proxima_segunda, proxima_sexta

# --- Função Auxiliar: Definir Situação e Cor ---
def calcular_situacao(row):
    hoje = datetime.now().date()
    inicio = row['Data Início'].date()
    fim = row['Data Fim'].date()

    if inicio > hoje:
        return "Não Iniciada"  # Futuro (Vermelho)
    elif fim < hoje:
        return "Concluída"     # Passado (Verde)
    else:
        return "Em Andamento"  # Presente (Amarelo)

# --- Modal (Pop-up) de Agendamento ---
@st.dialog("Agendar Nova Atividade")
def modal_agendamento(df_obras, df_frota, df_time, df_agenda_atual):
    st.write("Novo Agendamento")

    lista_projetos = df_obras['Projeto'].dropna().astype(str).unique().tolist() if 'Projeto' in df_obras.columns else []
    lista_time = df_time['Nome'].dropna().unique().tolist() if not df_time.empty and 'Nome' in df_time.columns else []
    col_veic = 'Veículo' if 'Veículo' in df_frota.columns else 'Placa'
    lista_veiculos = df_frota[col_veic].dropna().unique().tolist() if not df_frota.empty else []

    projeto_selecionado = st.selectbox("Projeto", options=lista_projetos, index=None, placeholder="Selecione...")

    desc_auto = ""
    cliente_auto = ""
    if projeto_selecionado:
        # Garante que compara string com string
        dados = df_obras[df_obras['Projeto'].astype(str) == projeto_selecionado].iloc[0]
        desc_auto = dados.get('Descricao', "") 
        cliente_auto = f"{dados.get('Cliente', '')} - {dados.get('Cidade', '')}"

    descricao = st.text_input("Descrição", value=desc_auto, disabled=True) 
    cliente = st.text_input("Cliente", value=cliente_auto, disabled=True) 

    # Datas Padrão: Próxima Seg e Sex
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
                "Projeto": str(projeto_selecionado), # Força String ao salvar
                "Descrição": descricao,
                "Cliente": cliente,
                "Data Início": data_inicio.strftime('%Y-%m-%d'),
                "Data Fim": data_fim.strftime('%Y-%m-%d'),
                "Executantes": ", ".join(executantes),
                "Veículo": veiculo if veiculo else "",
                "Status": "Planejado" # Mantemos o status original no banco, mas a cor visual será calculada
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
    col1, col2 = st.columns([3, 1])
    col1.header("📅 Cronograma")

    with st.spinner("Lendo dados..."):
        df_agenda, df_frota, df_time, df_obras = conexao.carregar_dados()

    with col2:
        if st.button("➕ Agendar", use_container_width=True):
            modal_agendamento(df_obras, df_frota, df_time, df_agenda)

    if df_agenda.empty:
        st.info("Nenhum agendamento.")
        return

    # 1. Tratamento de Dados
    try:
        df_agenda['Data Início'] = pd.to_datetime(df_agenda['Data Início'], format='mixed', dayfirst=True, errors='coerce')
        df_agenda['Data Fim'] = pd.to_datetime(df_agenda['Data Fim'], format='mixed', dayfirst=True, errors='coerce')
        
        # --- CORREÇÃO PONTO 1: Forçar String no Projeto ---
        df_agenda['Projeto'] = df_agenda['Projeto'].astype(str)
        
        df_processado = df_agenda.dropna(subset=['Data Início', 'Data Fim'])
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return

    if df_processado.empty:
        st.warning("Sem dados válidos.")
        return

    # 2. Lógica de Cores Automática (Calcula coluna 'Situacao')
    df_processado['Situacao'] = df_processado.apply(calcular_situacao, axis=1)

    # 3. Filtros (Datas e Situação)
    min_date = df_processado['Data Início'].min().date()
    max_date = df_processado['Data Fim'].max().date()
    
    # Linha de Filtros
    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        inicio = st.date_input("De:", value=min_date, format="DD/MM/YYYY")
    with f2:
        fim = st.date_input("Até:", value=max_date, format="DD/MM/YYYY")
    with f3:
        # --- CORREÇÃO PONTO 4: Filtro de Situação ---
        filtro_situacao = st.multiselect(
            "Filtrar Situação:", 
            options=["Não Iniciada", "Em Andamento", "Concluída"],
            default=["Não Iniciada", "Em Andamento", "Concluída"] # Mostra tudo por padrão
        )

    # Aplica Filtros
    mask = (df_processado['Data Início'].dt.date >= inicio) & \
           (df_processado['Data Fim'].dt.date <= fim) & \
           (df_processado['Situacao'].isin(filtro_situacao))
    
    df_filtrado = df_processado.loc[mask]

    # 4. VISUALIZAÇÃO
    if not df_filtrado.empty:
        # Ordenação
        df_filtrado = df_filtrado.sort_values(by=['Data Início', 'Projeto'], ascending=[True, True])
        
        # Altura dinâmica
        qtd_projetos_unicos = len(df_filtrado['Projeto'].unique())
        altura_grafico = max(300, qtd_projetos_unicos * 45)

        # --- CORREÇÃO PONTO 2: Cores Condicionais ---
        cores_condicionais = {
            "Não Iniciada": "#EF4444",  # Vermelho (Futuro)
            "Em Andamento": "#EAB308",  # Amarelo (Presente)
            "Concluída": "#22C55E"      # Verde (Passado)
        }

        fig = px.timeline(
            df_filtrado, 
            x_start="Data Início", 
            x_end="Data Fim", 
            y="Projeto",       
            color="Situacao",  # <--- Usa a coluna calculada, não o Status do banco
            text="Projeto",
            color_discrete_map=cores_condicionais,
            height=altura_grafico,
            hover_data={"Projeto":False, "Situacao":False}
        )

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', # Transparente
            plot_bgcolor='rgba(0,0,0,0)',
            
            font=dict(color="white", family="sans-serif"),
            
            # --- CORREÇÃO PONTO 3 (Eixo X): Dia Semana + 1 tick por dia ---
            xaxis=dict(
                title=None,
                tickformat="%a %d/%m", # Seg 02/09
                side="top",         
                showgrid=True,
                gridcolor='#333333',
                gridwidth=1,
                dtick=86400000.0, # <--- Força 1 dia exato
                tickcolor='white',
                tickfont=dict(color='#dddddd', size=11)
            ),
            
            yaxis=dict(
                title=None,
                autorange="reversed", 
                showgrid=False,
                showticklabels=False, 
                visible=True,
                type='category' # Garante formato texto
            ),
            
            margin=dict(t=50, b=10, l=0, r=0),
            showlegend=False, # Sem legenda
            bargap=0.3
        )

        # --- ESTILO DAS BARRAS (Borda Escura e Arredondada) ---
        fig.update_traces(
            textposition='inside', 
            insidetextanchor='start',
            textfont=dict(color='white', weight='bold', size=13),
            
            # --- CORREÇÃO PONTO 3 (Borda): Preto com 50% transp ---
            # Isso cria automaticamente um tom "mais escuro" da cor da barra
            marker_line_width=2,
            marker_line_color='rgba(0, 0, 0, 0.5)', 
            
            # Arredondamento
            marker=dict(cornerradius=5), 
            
            opacity=1
        )

        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        # Tabela Auxiliar
        df_exibicao = df_filtrado.copy()
        df_exibicao["Data Início"] = df_exibicao["Data Início"].dt.date
        df_exibicao["Data Fim"] = df_exibicao["Data Fim"].dt.date
        
        st.dataframe(
            df_exibicao[["Projeto", "Data Início", "Data Fim", "Situacao", "Veículo"]], 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("Nenhuma atividade encontrada com os filtros selecionados.")
