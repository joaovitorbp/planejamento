import streamlit as st
import planejamento
import plano_de_acao

# Configuração da página deve ser a primeira coisa
st.set_page_config(page_title="Gestão de Obras", layout="wide")

# Inicializa o estado da página se não existir
if 'pagina_atual' not in st.session_state:
    st.session_state['pagina_atual'] = 'Planejamento'

# --- Sidebar de Navegação (Estilo Menu) ---
st.sidebar.title("Navegação")

# Botões que funcionam como links
if st.sidebar.button("📊 Visualizar Planejamento", use_container_width=True):
    st.session_state['pagina_atual'] = 'Planejamento'
    st.rerun()

if st.sidebar.button("📝 Editar Agenda", use_container_width=True):
    st.session_state['pagina_atual'] = 'Editar'
    st.rerun()

st.sidebar.divider()
st.sidebar.info(f"Página Atual: {st.session_state['pagina_atual']}")

# --- Controle de Páginas ---
if st.session_state['pagina_atual'] == 'Planejamento':
    planejamento.app()
elif st.session_state['pagina_atual'] == 'Editar':
    plano_de_acao.app()
