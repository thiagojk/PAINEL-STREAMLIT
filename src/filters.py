"""Filtros contextuais na sidebar nativa; dependências e chaves preservadas."""
import streamlit as st
from src.data import available_municipalities, filter_data
from src.utils import description_label

FILTER_KEYS = {'ano','uf','municipio','indicador','indicador_obrigatorio','serie',
               'mapa_ano','mapa_uf','mapa_indicador','situacao','linhas_por_pagina','pagina_tabela','comparar_modo'}


def clear_filters():
    """Callback anterior ao rerun; nunca altera a página de navegação."""
    for key in list(st.session_state):
        if key in FILTER_KEYS or key.startswith(('periodo_', 'comparar_')):
            del st.session_state[key]


def reset_button():
    st.button('Limpar filtros', icon=':material/filter_alt_off:', on_click=clear_filters,
              key='limpar_filtros', width='stretch')


def select(label, options, key, format_func=str, index=0):
    if key in st.session_state and st.session_state[key] not in options:
        del st.session_state[key]
    return st.selectbox(label, options, index=index, key=key, format_func=format_func)


def global_filters(base, catalog, historical=False, required_indicator=False):
    page = st.session_state.get('pagina', 'Visão Geral')
    show_uf = page != 'Estados'
    show_municipality = page in {'Municípios','Indicadores','Análise Histórica','Tabela de Dados'}
    with st.sidebar:
        st.subheader('Filtros')
        year = None if historical else select('Ano', sorted(base.ANO.unique().tolist(), reverse=True), 'ano')
        reference = base if historical else filter_data(base, year=year)
        uf = select('UF', ['Todos'] + sorted(reference.UF.unique().tolist()), 'uf',
                    lambda value: 'Brasil · todas as UFs' if value == 'Todos' else value) if show_uf else 'Todos'
        municipality = 'Todos'
        if show_municipality:
            mun = available_municipalities(reference, uf=uf)
            labels = {str(r.COD_MUN): f'{r.NOME_MUN} · {r.UF} ({r.COD_MUN})' for r in mun.itertuples()}
            municipality = select('Município', ['Todos'] + list(labels), 'municipio',
                                  lambda x, labels=labels: 'Todos os municípios' if x == 'Todos' else labels[x])
        if historical:
            d = catalog.sort_values('ANO').drop_duplicates('SERIE', keep='last').sort_values(['INDICADOR', 'ANO'], ascending=[True, False])
            labels = {r.SERIE: f'{description_label(r)} [{", ".join(map(str, sorted(catalog.loc[catalog.SERIE.eq(r.SERIE), "ANO"].unique())))}]' for r in d.itertuples()}
            series = select('Definição do indicador', list(labels), 'serie', lambda x, labels=labels: labels[x])
            years = sorted(catalog.loc[catalog.SERIE.eq(series), 'ANO'].unique().tolist())
            if len(years) > 1:
                period = st.select_slider('Período', options=years, value=(years[0], years[-1]), key=f'periodo_{series}')
            else:
                period = (years[0], years[0])
                st.caption(f'Definição disponível somente em {years[0]}.')
            reset_button()
            st.caption('Séries com a mesma definição e unidade. Regras em Sobre.')
            return dict(year=None, uf=uf, municipality=municipality, indicator=None, series=series), period
        d = catalog[catalog.ANO.eq(year)]
        local = filter_data(reference, uf=uf, municipality=municipality)
        d = d[d.INDICADOR.isin(local.INDICADOR.unique())]
        labels = {r.INDICADOR: description_label(r) for r in d.itertuples()}
        options = list(labels) if required_indicator else ['Todos'] + list(labels)
        if not options:
            st.info('Não há indicadores disponíveis neste recorte.')
            return dict(year=year, uf=uf, municipality=municipality, indicator=None, series=None), None
        indicator = select('Indicador', options, 'indicador_obrigatorio' if required_indicator else 'indicador',
                           lambda x, labels=labels: 'Todos os indicadores' if x == 'Todos' else labels[x])
        reset_button()
        return dict(year=year, uf=uf, municipality=municipality, indicator=indicator, series=None), None


def map_filters(base, catalog):
    with st.sidebar:
        st.subheader('Filtros do mapa')
        year = select('Ano', sorted(base.ANO.unique().tolist(), reverse=True), 'mapa_ano')
        uf = select('UF', ['Todos'] + sorted(filter_data(base, year=year).UF.unique().tolist()), 'mapa_uf',
                    lambda x: 'Brasil · mapa de UFs' if x == 'Todos' else f'{x} · mapa municipal')
        d = catalog[catalog.ANO.eq(year)].sort_values('INDICADOR')
        labels = {r.INDICADOR: description_label(r) for r in d.itertuples()}
        indicator = select('Indicador', list(labels), 'mapa_indicador', lambda x: labels[x])
        reset_button()
    return dict(year=year, uf=uf, municipality='Todos', indicator=indicator, series=None), None
