"""Filtros próximos da análise; as chaves existentes e dependências são preservadas."""
import streamlit as st
from src.data import available_municipalities, filter_data
from src.utils import description_label


def select(label, options, key, format_func=str, index=0):
    if key in st.session_state and st.session_state[key] not in options:
        del st.session_state[key]
    return st.selectbox(label, options, index=index, key=key, format_func=format_func)


def global_filters(base, catalog, historical=False, required_indicator=False):
    with st.container(key='filter_bar'):
        st.caption('FILTRE SUA ANÁLISE')
        columns = st.columns([1, 1.7, 2.8] if historical else [.8, .8, 1.5, 2.5], gap='small')
        offset = 0
        if not historical:
            with columns[0]:
                year = select('Ano', sorted(base.ANO.unique().tolist(), reverse=True), 'ano')
            offset = 1
        else:
            year = None
        reference = base if historical else filter_data(base, year=year)
        with columns[offset]:
            uf = select('UF', ['Todos'] + sorted(reference.UF.unique().tolist()), 'uf',
                        lambda value: 'Brasil · todas as UFs' if value == 'Todos' else value)
        mun = available_municipalities(reference, uf=uf)
        labels = {str(r.COD_MUN): f'{r.NOME_MUN} · {r.UF} ({r.COD_MUN})' for r in mun.itertuples()}
        with columns[offset + 1]:
            municipality = select('Município', ['Todos'] + list(labels), 'municipio',
                                  lambda x, labels=labels: 'Todos os municípios' if x == 'Todos' else labels[x])
        with columns[offset + 2]:
            if historical:
                d = catalog.sort_values('ANO').drop_duplicates('SERIE', keep='last').sort_values(['INDICADOR', 'ANO'], ascending=[True, False])
                labels = {r.SERIE: f'{description_label(r)} [{", ".join(map(str, sorted(catalog.loc[catalog.SERIE.eq(r.SERIE), "ANO"].unique())))}]' for r in d.itertuples()}
                series = select('Definição do indicador', list(labels), 'serie', lambda x, labels=labels: labels[x])
            else:
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
        if historical:
            years = sorted(catalog.loc[catalog.SERIE.eq(series), 'ANO'].unique().tolist())
            if len(years) > 1:
                period = st.select_slider('Período', options=years, value=(years[0], years[-1]), key=f'periodo_{series}')
            else:
                period = (years[0], years[0])
                st.caption(f'Definição disponível somente em {years[0]}.')
            st.caption('Mesma definição e unidade ao longo do tempo. Mudanças de redação são separadas por segurança.')
            return dict(year=None, uf=uf, municipality=municipality, indicator=None, series=series), period
        return dict(year=year, uf=uf, municipality=municipality, indicator=indicator, series=None), None


def map_filters(base, catalog):
    with st.container(key='filter_bar'):
        st.caption('ESCOLHA O RECORTE TERRITORIAL')
        a, b, c = st.columns([.8, 3, 1.2], gap='small')
        with a:
            year = select('Ano', sorted(base.ANO.unique().tolist(), reverse=True), 'mapa_ano')
        with b:
            d = catalog[catalog.ANO.eq(year)].sort_values('INDICADOR')
            labels = {r.INDICADOR: description_label(r) for r in d.itertuples()}
            indicator = select('Indicador', list(labels), 'mapa_indicador', lambda x: labels[x])
        with c:
            uf = select('UF', ['Todos'] + sorted(filter_data(base, year=year).UF.unique().tolist()), 'mapa_uf',
                        lambda x: 'Brasil · mapa de UFs' if x == 'Todos' else f'{x} · mapa municipal')
    return dict(year=year, uf=uf, municipality='Todos', indicator=indicator, series=None), None
