import streamlit as st
import planejamento
import plano_de_acao

st.set_page_config(
    page_title="Termo Eletro App",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.sidebar.title("Navegação")
    escolha = st.sidebar.radio("Ir para:", ["📅 Planejamento (Geral)", "📝 Plano de Ação (Editor)"])
    st.sidebar.divider()
    st.sidebar.info("Conectado ao Google Drive ☁️")

    if escolha == "📅 Planejamento (Geral)":
        planejamento.show_page()
    elif escolha == "📝 Plano de Ação (Editor)":
        plano_de_acao.show_page()

if __name__ == "__main__":
    main()
