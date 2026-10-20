"""Filtros contextuais na sidebar nativa; dependências e chaves preservadas."""
import streamlit as st
from src.data import available_municipalities, filter_data
from src.utils import description_label
from src.styles import sidebar_header
from src.historical import concept_options, compatible_years, representative_years, validate_map_years

FILTER_KEYS = {'ano','uf','municipio','indicador','serie','conceito',
               'mapa_ano','mapa_uf','mapa_indicador','situacao','linhas_por_pagina','pagina_tabela',
               'mapa_historico','map_mode','ordem_estados','hist_explorar','hist_perfil_periodo'}


def clear_filters():
    """Callback anterior ao rerun; nunca altera a página de navegação."""
    for key in list(st.session_state):
        if key in FILTER_KEYS or key.startswith(('periodo_', 'mapa_anos_')):
            del st.session_state[key]


def reset_button():
    st.button('Limpar filtros', icon=':material/filter_alt_off:', on_click=clear_filters,
              key='limpar_filtros', width='stretch')


def select(label, options, key, format_func=str, index=0):
    if key in st.session_state and st.session_state[key] not in options:
        del st.session_state[key]
    return st.selectbox(label, options, index=index, key=key, format_func=format_func)


def global_filters(base, catalog, historical=False):
    page = st.session_state.get('pagina', 'Visão Geral')
    show_municipality = page in {'Análise Histórica','Tabela de Dados'}
    with st.sidebar:
        sidebar_header()
        year = None if historical else select('Ano', sorted(base.ANO.unique().tolist(), reverse=True), 'ano')
        reference = base if historical else filter_data(base, year=year)
        uf = select('UF', ['Todos'] + sorted(reference.UF.unique().tolist()), 'uf',
                    lambda value: 'Brasil · todas as UFs' if value == 'Todos' else value)
        municipality = 'Todos'
        if show_municipality:
            mun = available_municipalities(reference, uf=uf)
            labels = {str(r.COD_MUN): f'{r.NOME_MUN} · {r.UF} ({r.COD_MUN})' for r in mun.itertuples()}
            municipality = select('Município', ['Todos'] + list(labels), 'municipio',
                                  lambda x, labels=labels: 'Todos os municípios' if x == 'Todos' else labels[x])
        if page == 'Estados':
            select('Ordenar indicadores', ['Maior não atingimento','Número do indicador','Maior cumprimento','Menor cumprimento'], 'ordem_estados')
            reset_button()
            return dict(year=year, uf=uf, municipality='Todos', indicator='Todos', series=None), None
        if historical:
            concepts = concept_options(catalog)
            labels = dict(zip(concepts.CONCEITO, concepts.LABEL))
            concept = select('Indicador · série conceitual', list(labels), 'conceito', lambda x: labels[x])
            info = concepts.loc[concepts.CONCEITO.eq(concept)].iloc[0]
            candidates = info.SERIES
            if len(candidates) > 1:
                entries = catalog[catalog.SERIE.isin(candidates)]
                annual = dict(zip(entries.SERIE, entries.ANO.astype(str)))
                series = select('Ano da série · escala não comparável', candidates, 'serie', lambda x: annual[x], index=len(candidates)-1)
                st.caption('A escala original não foi comprovada entre anos. Cada ano permanece separado.')
            else:
                series = select('Série histórica', candidates, 'serie', lambda x: 'Definição e unidade compatíveis')
            st.caption(info.DESCRICAO)
            years = compatible_years(catalog, series)
            if len(years) > 1:
                period = st.select_slider('Período', options=years, value=(years[0], years[-1]), key=f'periodo_{series}')
            else:
                period = (years[0], years[0])
                st.caption(f'Definição disponível somente em {years[0]}.')
            st.divider()
            explore = st.toggle('Explorar perfil e persistência', key='hist_explorar')
            if explore:
                all_years = sorted(base.ANO.unique().tolist())
                st.select_slider('Período da exploração territorial', options=all_years,
                                 value=(all_years[0],all_years[-1]), key='hist_perfil_periodo')
                st.caption('Análises coletivas por Brasil/UF; período próprio, independente do indicador acima.')
            reset_button()
            st.caption('Séries com a mesma definição e unidade. Regras em Sobre.')
            return dict(year=None, uf=uf, municipality=municipality, indicator=None, series=series), period
        d = catalog[catalog.ANO.eq(year)]
        local = filter_data(reference, uf=uf, municipality=municipality)
        d = d[d.INDICADOR.isin(local.INDICADOR.unique())]
        labels = {r.INDICADOR: description_label(r) for r in d.itertuples()}
        options = ['Todos'] + list(labels)
        if not options:
            st.info('Não há indicadores disponíveis neste recorte.')
            return dict(year=year, uf=uf, municipality=municipality, indicator=None, series=None), None
        indicator = select('Indicador', options, 'indicador',
                           lambda x, labels=labels: 'Todos os indicadores' if x == 'Todos' else labels[x])
        reset_button()
        return dict(year=year, uf=uf, municipality=municipality, indicator=indicator, series=None), None


def map_filters(base, catalog):
    with st.sidebar:
        sidebar_header('Filtros do mapa')
        year = select('Ano', sorted(base.ANO.unique().tolist(), reverse=True), 'mapa_ano')
        uf = select('UF', ['Todos'] + sorted(filter_data(base, year=year).UF.unique().tolist()), 'mapa_uf',
                    lambda x: 'Brasil · mapa de UFs' if x == 'Todos' else f'{x} · mapa municipal')
        d = catalog[catalog.ANO.eq(year)].sort_values('INDICADOR')
        labels = {r.INDICADOR: description_label(r) for r in d.itertuples()}
        indicator = select('Indicador', list(labels), 'mapa_indicador', lambda x: labels[x])
        st.divider()
        st.radio('Visualização do mapa', ['Situação da meta','Grau de alcance (%)'], key='map_mode', width='stretch')
        st.divider()
        st.caption('EVOLUÇÃO TERRITORIAL')
        enabled = st.toggle('Comparar mapas no tempo', key='mapa_historico')
        entry = d.loc[d.INDICADOR.eq(indicator)].iloc[0]
        years = compatible_years(catalog, entry.SERIE)
        if enabled:
            if len(years) == 1:
                st.caption('Somente este ano tem definição e escala compatíveis. Outros anos não são unidos por número.')
            key = f'mapa_anos_{entry.SERIE}'
            if key in st.session_state:
                st.session_state[key] = [y for y in st.session_state[key] if y in years][:6]
            chosen = st.multiselect('Anos da evolução territorial', years, default=representative_years(years),
                                    max_selections=6, key=key, help='Selecione até 6 anos para comparação territorial.')
            validate_map_years(chosen, years)
        reset_button()
    return dict(year=year, uf=uf, municipality='Todos', indicator=indicator, series=None), None
