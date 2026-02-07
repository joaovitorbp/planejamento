import streamlit as st

# Importa as outras páginas (arquivos que estão na mesma pasta)
import planejamento
import plano_de_acao

# --- CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira linha do app) ---
st.set_page_config(
    page_title="Termo Eletro App",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SIDEBAR E NAVEGAÇÃO ---
def main():
    st.sidebar.title("Navegação")
    
    # Menu Principal
    escolha = st.sidebar.radio(
        "Ir para:",
        ["📅 Planejamento (Geral)", "📝 Plano de Ação (Editor)"]
    )
    
    st.sidebar.divider()
    
    # Placeholder para Login Futuro
    # if not st.session_state.get('logado'):
    #     mostrar_login()
    # else: ...

    st.sidebar.info("Base de Dados: Google Drive\nOrçamentos: Excel Local")

    # --- ROTEAMENTO ---
    # Chama a função principal de cada arquivo baseado na escolha
    if escolha == "📅 Planejamento (Geral)":
        planejamento.show_page()
    elif escolha == "📝 Plano de Ação (Editor)":
        plano_de_acao.show_page()

if __name__ == "__main__":
    main()
