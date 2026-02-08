import streamlit as st
import plotly.express as px
import pandas as pd
import conexao
from datetime import datetime

# --- Modal (Pop-up) de Agendamento ---
@st.dialog("Agendar Nova Atividade")
def modal_agendamento(df_obras, df_frota, df_time, df_agenda_atual):
    st.write("Novo Agendamento")

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
        # Filtra e pega a primeira linha
        dados = df_obras[df_obras['Projeto'] == projeto_selecionado].iloc[0]
        
        # --- CORREÇÃO 1: Coluna "Descricao" (Exata) ---
        desc_auto = dados.get('Descricao', "") 
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

    if st.button("Salvar", type="primary"):
        if not projeto_selecionado:
            st.error("Selecione um projeto.")
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
                # Sanitização de Datas
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
    col1.header("📅 Gráfico de Gantt")

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
        # Datas
        df_agenda['Data Início'] = pd.to_datetime(df_agenda['Data Início'], dayfirst=True, errors='coerce')
        df_agenda['Data Fim'] = pd.to_datetime(df_agenda['Data Fim'], dayfirst=True, errors='coerce')
        
        # --- CORREÇÃO 2: Forçar Projeto como TEXTO (String) ---
        # Isso impede que o Plotly ache que é número e corte o eixo
        df_agenda['Projeto'] = df_agenda['Projeto'].astype(str)
        
        df_processado = df_agenda.dropna(subset=['Data Início', 'Data Fim'])
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return

    if df_processado.empty:
        st.warning("Sem dados válidos.")
        return

    # 2. Filtros (Padrão: Pega TUDO, do mais antigo ao mais novo)
    min_date = df_processado['Data Início'].min().date()
    max_date = df_processado['Data Fim'].max().date()
    
    c1, c2 = st.columns(2)
    with c1:
        inicio = st.date_input("De:", value=min_date, format="DD/MM/YYYY")
    with c2:
        fim = st.date_input("Até:", value=max_date, format="DD/MM/YYYY")

    mask = (df_processado['Data Início'].dt.date >= inicio) & (df_processado['Data Fim'].dt.date <= fim)
    df_filtrado = df_processado.loc[mask]

    # 3. O GRÁFICO GANTT
    if not df_filtrado.empty:
        # Ordena: Primeiro pelo Projeto (alfabético), depois pela Data
        df_filtrado = df_filtrado.sort_values(by=['Projeto', 'Data Início'], ascending=[True, True])
        
        # Cálculo de Altura: Conta Projetos ÚNICOS para dar espaço vertical
        qtd_projetos_unicos = len(df_filtrado['Projeto'].unique())
        altura_grafico = max(400, qtd_projetos_unicos * 50) # Mínimo 400px, aumenta 50px por projeto

        fig = px.timeline(
            df_filtrado, 
            x_start="Data Início", 
            x_end="Data Fim", 
            y="Projeto",       
            color="Status",    
            text="Projeto",    
            height=altura_grafico,
            hover_data=["Cliente", "Veículo", "Executantes"]
        )

        fig.update_layout(
            xaxis=dict(
                title="",
                tickformat="%d/%m", 
                side="top",         
                gridcolor='#e0e0e0',
                showgrid=True
            ),
            yaxis=dict(
                title=None,           # --- CORREÇÃO 3: Remove legenda do eixo Y ("Projeto")
                autorange="reversed", # Ordem correta (A-Z de cima para baixo)
                showgrid=True,
                gridcolor='#e0e0e0',
                automargin=True,      # Garante espaço para ler o nome do projeto
                type='category'       # --- CORREÇÃO 4: Força Eixo Categórico (Mostra TODOS os itens)
            ),
            plot_bgcolor='white',
            margin=dict(t=40, b=20, l=10, r=10),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            bargap=0.2 
        )

        fig.update_traces(
            textposition='inside', 
            insidetextanchor='start', 
            marker_line_width=1,      
            marker_line_color='white',
            opacity=0.9
        )

        st.plotly_chart(fig, use_container_width=True)

        st.divider()
        
        # Tabela
        df_exibicao = df_filtrado.copy()
        df_exibicao["Data Início"] = df_exibicao["Data Início"].dt.date
        df_exibicao["Data Fim"] = df_exibicao["Data Fim"].dt.date
        
        st.dataframe(
            df_exibicao[["Projeto", "Data Início", "Data Fim", "Veículo", "Status"]], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Data Início": st.column_config.DateColumn("Início", format="DD/MM/YYYY"),
                "Data Fim": st.column_config.DateColumn("Fim", format="DD/MM/YYYY")
            }
        )
    else:
        st.warning("Nada encontrado neste período.")
