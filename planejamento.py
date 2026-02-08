import streamlit as st
import plotly.express as px
import pandas as pd
import conexao
from datetime import datetime

# --- Modal (Pop-up) de Agendamento ---
# (Mantido igual - Lógica funcional)
@st.dialog("Agendar Nova Atividade")
def modal_agendamento(df_obras, df_frota, df_time, df_agenda_atual):
    st.write("Novo Agendamento")

    lista_projetos = df_obras['Projeto'].dropna().unique().tolist() if 'Projeto' in df_obras.columns else []
    lista_time = df_time['Nome'].dropna().unique().tolist() if not df_time.empty and 'Nome' in df_time.columns else []
    col_veic = 'Veículo' if 'Veículo' in df_frota.columns else 'Placa'
    lista_veiculos = df_frota[col_veic].dropna().unique().tolist() if not df_frota.empty else []

    projeto_selecionado = st.selectbox("Projeto", options=lista_projetos, index=None, placeholder="Selecione...")

    desc_auto = ""
    cliente_auto = ""
    if projeto_selecionado:
        dados = df_obras[df_obras['Projeto'] == projeto_selecionado].iloc[0]
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
        df_agenda['Projeto'] = df_agenda['Projeto'].astype(str)
        df_processado = df_agenda.dropna(subset=['Data Início', 'Data Fim'])
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return

    if df_processado.empty:
        st.warning("Sem dados válidos.")
        return

    # 2. Filtros
    min_date = df_processado['Data Início'].min().date()
    max_date = df_processado['Data Fim'].max().date()
    
    c1, c2 = st.columns(2)
    with c1:
        inicio = st.date_input("De:", value=min_date, format="DD/MM/YYYY")
    with c2:
        fim = st.date_input("Até:", value=max_date, format="DD/MM/YYYY")

    mask = (df_processado['Data Início'].dt.date >= inicio) & (df_processado['Data Fim'].dt.date <= fim)
    df_filtrado = df_processado.loc[mask]

    # 3. VISUAL DARK MODE MINIMALISTA
    if not df_filtrado.empty:
        # Ordenação
        df_filtrado = df_filtrado.sort_values(by=['Projeto', 'Data Início'], ascending=[True, True])
        
        # Altura dinâmica
        qtd_projetos_unicos = len(df_filtrado['Projeto'].unique())
        altura_grafico = max(300, qtd_projetos_unicos * 40) # 40px por linha

        # Cores Vibrantes (Neon) para contrastar com fundo escuro
        cores_dark_mode = {
            "Planejado": "#00B4D8",  # Ciano Neon
            "Confirmado": "#F77F00", # Laranja Vivo
            "Executado": "#2D6A4F",  # Verde Escuro (mas visível)
            "Cancelado": "#D62828"   # Vermelho Sangue
        }

        fig = px.timeline(
            df_filtrado, 
            x_start="Data Início", 
            x_end="Data Fim", 
            y="Projeto",       
            color="Status",    
            text="Projeto",
            color_discrete_map=cores_dark_mode,
            height=altura_grafico,
            hover_data={"Projeto":False, "Status":False} # Hover limpo
        )

        fig.update_layout(
            # Fundo Transparente (Pega a cor do seu Streamlit Dark)
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            
            # Fonte Global
            font=dict(color="white", family="sans-serif"),
            
            # Eixo X (Datas) - A única coisa que sobra fora a barra
            xaxis=dict(
                title=None,
                tickformat="%d/%m", 
                side="top",         
                showgrid=True,
                gridcolor='#333333', # Grade cinza chumbo bem sutil
                gridwidth=1,
                tickcolor='white',
                tickfont=dict(color='#cccccc', size=12) # Texto cinza claro
            ),
            
            # Eixo Y (Projetos) - TOTALMENTE OCULTO
            yaxis=dict(
                title=None,
                autorange="reversed", 
                showgrid=False,
                showticklabels=False, # <--- Remove os nomes da esquerda
                visible=True, # Mantém eixo ativo para ordenação, mas invisível
                type='category'
            ),
            
            margin=dict(t=30, b=10, l=0, r=0), # Margem Zero nas laterais
            showlegend=False, # <--- Remove Legenda
            bargap=0.2
        )

        fig.update_traces(
            textposition='inside', 
            insidetextanchor='start',
            textfont=dict(color='white', weight='bold'), # Texto dentro da barra
            marker_line_width=0,
            opacity=1
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela (Opcional, se quiser remover me avise, mantive pois é útil)
        st.divider()
        df_exibicao = df_filtrado.copy()
        df_exibicao["Data Início"] = df_exibicao["Data Início"].dt.date
        df_exibicao["Data Fim"] = df_exibicao["Data Fim"].dt.date
        
        st.dataframe(
            df_exibicao[["Projeto", "Data Início", "Data Fim", "Veículo", "Status"]], 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("Sem dados.")
