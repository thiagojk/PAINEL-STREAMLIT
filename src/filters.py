import streamlit as st
from src.data import available_municipalities, filter_data
from src.utils import description_label


def select(label, options, key, format_func=str, index=0):
    if key in st.session_state and st.session_state[key] not in options:
        del st.session_state[key]
    return st.selectbox(label, options, index=index, key=key, format_func=format_func)


def global_filters(base, catalog, historical=False, required_indicator=False):
    with st.sidebar:
        st.divider()
        st.caption('RECORTE DA ANÁLISE')
        year = None if historical else select('Ano', sorted(base.ANO.unique().tolist(), reverse=True), 'ano')
        reference = base if historical else filter_data(base, year=year)
        uf = select('UF', ['Todos'] + sorted(reference.UF.unique().tolist()), 'uf')
        mun = available_municipalities(reference, uf=uf)
        labels = {str(r.COD_MUN): f'{r.NOME_MUN} · {r.UF} ({r.COD_MUN})' for r in mun.itertuples()}
        municipality = select('Município', ['Todos'] + list(labels), 'municipio', lambda x, labels=labels: 'Todos' if x == 'Todos' else labels[x])
        if historical:
            d = catalog.sort_values('ANO').drop_duplicates('SERIE', keep='last').sort_values(['INDICADOR', 'ANO'], ascending=[True, False])
            labels = {r.SERIE: f'{description_label(r)} [{", ".join(map(str, sorted(catalog.loc[catalog.SERIE.eq(r.SERIE), "ANO"].unique())))}]' for r in d.itertuples()}
            series = select('Definição do indicador', list(labels), 'serie', lambda x, labels=labels: labels[x])
            st.caption('Séries usam a mesma definição e unidade. Mudanças de redação são separadas por segurança.')
            years = sorted(catalog.loc[catalog.SERIE.eq(series), 'ANO'].unique().tolist())
            if len(years) > 1:
                period = st.select_slider('Período', options=years, value=(years[0], years[-1]), key=f'periodo_{series}')
            else:
                period = (years[0], years[0])
                st.caption(f'Definição disponível somente em {years[0]}.')
            return dict(year=None, uf=uf, municipality=municipality, indicator=None, series=series), period
        d = catalog[catalog.ANO.eq(year)]
        local = filter_data(reference, uf=uf, municipality=municipality)
        d = d[d.INDICADOR.isin(local.INDICADOR.unique())]
        labels = {r.INDICADOR: description_label(r) for r in d.itertuples()}
        options = list(labels) if required_indicator else ['Todos'] + list(labels)
        if not options:
            st.info('Não há indicadores disponíveis neste recorte.')
            return dict(year=year, uf=uf, municipality=municipality, indicator=None, series=None), None
        indicator = select('Indicador', options, 'indicador_obrigatorio' if required_indicator else 'indicador', lambda x, labels=labels: 'Todos' if x == 'Todos' else labels[x])
        st.caption('As opções acompanham o ano e a localidade selecionados.')
        return dict(year=year, uf=uf, municipality=municipality, indicator=indicator, series=None), None
