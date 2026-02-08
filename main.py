import streamlit as st
import planejamento
import plano_de_acao

st.set_page_config(page_title="Gestão de Obras", layout="wide")

st.sidebar.title("Navegação")
pagina = st.sidebar.radio("Ir para:", ["Planejamento (Gantt)", "Editar Agenda"])

if pagina == "Planejamento (Gantt)":
    planejamento.app()
elif pagina == "Editar Agenda":
    plano_de_acao.app()
