"""Recortes históricos locais em cache, com invalidação pela assinatura dos Parquets."""
import streamlit as st
from src.data import load_data, filter_data
from src.geography import state_summary, municipality_layer
from src.historical import compatible_years, validate_map_years


@st.cache_data(show_spinner=False, max_entries=12)
def historical_slice(signature, series, uf='Todos'):
    base, catalog = load_data(signature)
    # Uma única filtragem para todos os anos da série/território, não por mapa.
    return filter_data(base, series=series, uf=uf), catalog.loc[catalog.SERIE.eq(series)].copy()


@st.cache_data(show_spinner=False, max_entries=24)
def prepare_history(signature, series, uf, years, geometry_signature):
    from src.geography import load_geojson
    frame, catalog = historical_slice(signature, series, uf)
    years = validate_map_years(years, compatible_years(catalog, series))
    geojson = load_geojson(geometry_signature)
    prepared = []
    for year in years:
        local = frame.loc[frame.ANO.eq(year)]
        entry = catalog.loc[catalog.ANO.eq(year)].iloc[0]
        prepared.append({'year':year, 'entry':entry, 'empty':local.empty,
                         'conflicts':int(local.CONFLITO_META.sum()),
                         'data':None if local.empty else state_summary(local) if uf == 'Todos' else municipality_layer(local, geojson)})
    return prepared
