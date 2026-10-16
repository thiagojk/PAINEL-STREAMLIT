"""Navegação nativa, acessível por teclado, com aparência de barra do sistema."""
import streamlit as st

NAV_LABELS = {
    'Visão Geral':'Visão Geral', 'Estados':'Estados', 'Municípios':'Municípios',
    'Indicadores':'Indicadores', 'Mapas':'Mapas', 'Análise Histórica':'Histórico',
    'Comparações':'Comparações', 'Tabela de Dados':'Dados', 'Sobre / Metodologia':'Sobre',
}


def navigation():
    return st.radio('Navegação principal', list(NAV_LABELS), horizontal=True,
                    format_func=NAV_LABELS.get, key='pagina', label_visibility='collapsed', width='stretch')


def open_maps(filters):
    # Callback executado antes da próxima renderização, sem alterar widget já criado.
    st.session_state['pagina'] = 'Mapas'
    st.session_state['mapa_ano'] = filters['year']
    st.session_state['mapa_uf'] = filters['uf']
    if filters['indicator'] not in [None, 'Todos']:
        st.session_state['mapa_indicador'] = filters['indicator']
