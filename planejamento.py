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

# --- Função Auxiliar: Definir Situação e Cores (Preenchimento e Borda) ---
def calcular_situacao_e_cores(row):
    hoje = datetime.now().date()
    # Garante conversão segura para date
    inicio = pd.to_datetime(row['Data Início']).date()
    fim = pd.to_datetime(row['Data Fim']).date()

    # Lógica pedida:
    # Inicio > Hoje (Futuro) -> Vermelho
    # Termino < Hoje (Passado) -> Verde
    # Inicio <= Hoje <= Termino (Presente) -> Amarelo
    
    if inicio > hoje:
        situacao = "Não Iniciada"
        cor_fill = "#EF4444"  # Vermelho Fosco
        cor_line = "#7F1D1D"  # Vermelho Escuro (Borda)
    elif fim < hoje:
        situacao = "Concluída"
        cor_fill = "#10B981"  # Verde Esmeralda
        cor_line = "#064E3B"  # Verde Escuro (Borda)
    else:
        situacao = "Em Andamento"
        cor_fill = "#F59E0B"  # Amarelo/Laranja
        cor_line = "#78350F"  # Marrom/Laranja Escuro (Borda)
        
    return pd.Series([situacao, cor_fill, cor_line])

# --- Modal (Pop-up) ---
@st.dialog("Agendar Nova Atividade")
def modal_agendamento(df_obras, df_frota, df_time, df_agenda_atual):
    st.write("Novo Agendamento")

    # Listas
    lista_projetos = df_obras['Projeto'].astype(str).dropna().unique().tolist() if 'Projeto' in df_obras.columns else []
    lista_time = df_time['Nome'].dropna().unique().tolist() if not df_time.empty and 'Nome' in df_time.columns else []
    col_veic = 'Veículo' if 'Veículo' in df_frota.columns else 'Placa'
    lista_veiculos = df_frota[col_veic].dropna().unique().tolist() if not df_frota.empty else []

    projeto_selecionado = st.selectbox("Projeto", options=lista_projetos, index=None, placeholder="Selecione...")

    desc_auto = ""
    cliente_auto = ""
    if projeto_selecionado:
        # Filtra como string para evitar erro
        df_obras['Projeto'] = df_obras['Projeto'].astype(str)
        dados = df_obras[df_obras['Projeto'] == str(projeto_selecionado)].iloc[0]
        desc_auto = dados.get('Descricao', "") 
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
                "Projeto": str(projeto_selecionado), # Força String
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
                st.cache_data.clear() # Limpa cache para forçar atualização
                st.success("Salvo!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

# --- App Principal ---
def app():
    col1, col2 = st.columns([3, 1])
    col1.header("📅 Cronograma")

    # Carrega dados e CRIA CÓPIA para evitar problema de cache
    df_raw, df_frota, df_time, df_obras_raw = conexao.carregar_dados()
    df_agenda = df_raw.copy()
    df_obras = df_obras_raw.copy()

    with col2:
        if st.button("➕ Agendar", use_container_width=True):
            modal_agendamento(df_obras, df_frota, df_time, df_agenda)

    if df_agenda.empty:
        st.info("Nenhum agendamento.")
        return

    # 1. Tratamento de Dados (Forçar Tipos)
    try:
        df_agenda['Data Início'] = pd.to_datetime(df_agenda['Data Início'], format='mixed', dayfirst=True, errors='coerce')
        df_agenda['Data Fim'] = pd.to_datetime(df_agenda['Data Fim'], format='mixed', dayfirst=True, errors='coerce')
        
        # Converte Projeto para String (Remove .0 se vier do Excel como float)
        # Ex: 1001.0 -> "1001" | "1001.2002" -> "1001.2002"
        df_agenda['Projeto'] = df_agenda['Projeto'].astype(str).str.replace(r'\.0$', '', regex=True)
        
        df_processado = df_agenda.dropna(subset=['Data Início', 'Data Fim'])
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return

    if df_processado.empty:
        st.warning("Sem dados válidos.")
        return

    # 2. Aplica a Lógica de Cores e Situação
    # Cria 3 colunas novas: Situacao, CorFill, CorLine
    df_processado[['Situacao', 'CorFill', 'CorLine']] = df_processado.apply(calcular_situacao_e_cores, axis=1)

    # 3. Filtros
    min_date = df_processado['Data Início'].min().date()
    max_date = df_processado['Data Fim'].max().date()
    
    c_ini, c_fim, c_filtro = st.columns([1, 1, 2])
    with c_ini:
        inicio = st.date_input("De:", value=min_date, format="DD/MM/YYYY")
    with c_fim:
        fim = st.date_input("Até:", value=max_date, format="DD/MM/YYYY")
    with c_filtro:
        situacoes_disponiveis = ["Não Iniciada", "Em Andamento", "Concluída"]
        filtro_situacao = st.multiselect("Filtrar Situação:", situacoes_disponiveis, default=situacoes_disponiveis)

    # Aplica Filtros
    mask = (df_processado['Data Início'].dt.date >= inicio) & \
           (df_processado['Data Fim'].dt.date <= fim) & \
           (df_processado['Situacao'].isin(filtro_situacao))
    
    df_filtrado = df_processado.loc[mask]

    # 4. GRÁFICO FINAL
    if not df_filtrado.empty:
        # Ordenação
        df_filtrado = df_filtrado.sort_values(by=['Data Início', 'Projeto'])
        
        qtd_projetos = len(df_filtrado['Projeto'].unique())
        altura = max(300, qtd_projetos * 45)

        # Como queremos cores específicas por LINHA (baseado na data) e não por categoria fixa,
        # O jeito mais robusto no Plotly é passar a coluna de cor diretamente.
        
        fig = px.timeline(
            df_filtrado, 
            x_start="Data Início", 
            x_end="Data Fim", 
            y="Projeto",
            text="Projeto",
            height=altura,
            hover_data={"Projeto": False, "Situacao": True, "CorFill": False}
        )

        # APLICANDO AS CORES MANUALMENTE
        # O Plotly Express as vezes briga com cores por linha, então atualizamos o trace direto.
        fig.update_traces(
            marker=dict(
                color=df_filtrado['CorFill'], # Cor do preenchimento calculada
                line=dict(
                    color=df_filtrado['CorLine'], # Cor da borda calculada (mais escura)
                    width=3 # Borda grossa para destaque
                ),
                cornerradius=5 # Arredondamento
            ),
            textposition='inside', 
            insidetextanchor='start',
            textfont=dict(color='white', weight='bold', size=14)
        )

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white", family="sans-serif"),
            
            xaxis=dict(
                title=None,
                tickformat="%a %d/%m", # Seg 02/09
                side="top",         
                showgrid=True,
                gridcolor='#333333',
                dtick=86400000.0, # 1 dia exato
                tickcolor='white',
                tickfont=dict(color='#cccccc')
            ),
            
            yaxis=dict(
                title=None,
                autorange="reversed", 
                showgrid=False,
                showticklabels=False, 
                visible=True,
                type='category'
            ),
            
            margin=dict(t=40, b=10, l=0, r=0),
            showlegend=False,
            bargap=0.3
        )

        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        st.dataframe(
            df_filtrado[["Projeto", "Data Início", "Data Fim", "Situacao", "Veículo"]], 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("Nenhuma atividade encontrada com os filtros selecionados.")
