import streamlit as st
import planejamento
import plano_de_acao

# Configuração da página (Sempre a primeira linha)
st.set_page_config(page_title="Gestão de Obras", layout="wide")

# Inicializa estado da página
if 'pagina_atual' not in st.session_state:
    st.session_state['pagina_atual'] = 'Planejamento'

# --- BARRA LATERAL ---
st.sidebar.title("Navegação")

if st.sidebar.button("📅 Cronograma (Gantt)", use_container_width=True):
    st.session_state['pagina_atual'] = 'Planejamento'
    st.rerun()

if st.sidebar.button("📝 Editar Agenda (Tabela)", use_container_width=True):
    st.session_state['pagina_atual'] = 'Editar'
    st.rerun()

st.sidebar.divider()

# --- BOTÃO MÁGICO PARA LIMPAR O CACHE ---
# Se você editou algo direto no Google Sheets e não apareceu, clique aqui.
st.sidebar.markdown("### Admin")
if st.sidebar.button("🔄 Atualizar Dados (Limpar Cache)", use_container_width=True, type="secondary"):
    st.cache_data.clear()  # Apaga a memória
    st.rerun()             # Recarrega a página

st.sidebar.divider()

# --- ROTEAMENTO DE PÁGINAS ---
if st.session_state['pagina_atual'] == 'Planejamento':
    planejamento.app()
elif st.session_state['pagina_atual'] == 'Editar':
    plano_de_acao.app()
