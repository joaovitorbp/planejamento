import streamlit as st
import plotly.express as px
import pandas as pd
import conexao
from datetime import datetime

# --- Modal (Pop-up) de Agendamento ---
# (Lógica mantida idêntica, pois funciona perfeitamente)
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

    # 1. Tratamento de Dados (BLINDADO)
    try:
        df_agenda['Data Início'] = pd.to_datetime(df_agenda['Data Início'], format='mixed', dayfirst=True, errors='coerce')
        df_agenda['Data Fim'] = pd.to_datetime(df_agenda['Data Fim'], format='mixed', dayfirst=True, errors='coerce')
        df_agenda['Projeto'] = df_agenda['Projeto'].astype(str) # Força texto
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

    # 3. VISUALIZAÇÃO PROFISSIONAL
    if not df_filtrado.empty:
        # Ordenação
        df_filtrado = df_filtrado.sort_values(by=['Projeto', 'Data Início'], ascending=[True, True])
        
        # Altura: Compacta mas legível
        qtd_projetos_unicos = len(df_filtrado['Projeto'].unique())
        altura_grafico = max(350, qtd_projetos_unicos * 45)

        # --- PALETA DE CORES MODERNA (Flat Design) ---
        cores_status = {
            "Planejado": "#3B82F6",  # Azul Moderno
            "Confirmado": "#F59E0B", # Âmbar/Laranja Suave
            "Executado": "#10B981",  # Verde Esmeralda
            "Cancelado": "#EF4444"   # Vermelho Fosco
        }

        fig = px.timeline(
            df_filtrado, 
            x_start="Data Início", 
            x_end="Data Fim", 
            y="Projeto",       
            color="Status",    
            text="Projeto",
            color_discrete_map=cores_status, # Aplica as cores manuais
            height=altura_grafico,
            # Customizando o Hover (tooltip) para ficar limpo
            hover_data={
                "Projeto": False, # Já está no eixo Y
                "Data Início": "|%d/%m", # Formato curto
                "Data Fim": "|%d/%m",
                "Status": False, # Já está na cor
                "Veículo": True,
                "Executantes": True
            }
        )

        # --- LAYOUT MINIMALISTA ---
        fig.update_layout(
            # Fontes
            font_family="Arial, sans-serif",
            font_color="#333333",
            title_font_size=18,
            
            # Eixo X (Datas)
            xaxis=dict(
                title="",
                tickformat="%d/%b", # Dia/Mês (ex: 01/Fev)
                tickfont=dict(size=12, color="#666"),
                side="top",         
                showgrid=True,
                gridcolor='#F3F4F6', # Grade muito sutil
                gridwidth=1,
                dtick="D1", # Grade diária (opcional, pode remover se ficar muito cheio)
                showline=False,
                ticks=""
            ),
            
            # Eixo Y (Projetos)
            yaxis=dict(
                title=None,
                autorange="reversed", 
                showgrid=False, # Sem linhas horizontais para limpar
                automargin=True,
                type='category',
                tickfont=dict(size=13, weight="bold", color="#111827") # Projetos em destaque
            ),
            
            # Fundo e Margens
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(t=30, b=10, l=10, r=10),
            
            # Legenda Elegante
            showlegend=True,
            legend=dict(
                orientation="h", 
                yanchor="bottom", y=1.05, 
                xanchor="left", x=0,
                title=None, # Remove título da legenda
                font=dict(size=12)
            ),
            
            # Espaçamento das barras
            bargap=0.3 # 0.3 dá um respiro bom entre as linhas
        )

        # --- ESTILO DAS BARRAS ---
        fig.update_traces(
            textposition='inside', 
            insidetextanchor='start',
            textfont=dict(color='white', size=12), # Texto branco para contraste
            marker_line_width=0, # Remove borda preta (Flat design)
            opacity=1.0
        )

        st.plotly_chart(fig, use_container_width=True)
        st.divider()
        
        # Tabela Minimalista
        st.markdown("### Detalhes")
        df_exibicao = df_filtrado.copy()
        df_exibicao["Data Início"] = df_exibicao["Data Início"].dt.date
        df_exibicao["Data Fim"] = df_exibicao["Data Fim"].dt.date
        
        st.dataframe(
            df_exibicao[["Projeto", "Data Início", "Data Fim", "Veículo", "Status"]], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Data Início": st.column_config.DateColumn("Início", format="DD/MM/YYYY"),
                "Data Fim": st.column_config.DateColumn("Fim", format="DD/MM/YYYY"),
                "Status": st.column_config.Column(
                    "Status",
                    width="small"
                )
            }
        )
    else:
        st.info("Utilize os filtros acima ou cadastre um novo agendamento.")
