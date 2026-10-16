"""Análise descritiva: situações da fonte, sem estimar resultados ou incentivo."""
import numpy as np
import pandas as pd
import streamlit as st
from src.data import filter_data, load_data
from src.metrics import summarize, municipal_ranking

BANDS = ['< 30%', '30% a < 50%', '50% a < 70%', '70% a < 90%', '≥ 90%', 'Sem avaliação']


def indicator_summary(frame, catalog, year):
    if not frame.empty and set(frame.ANO) != {year}:
        raise ValueError('A análise exige um único ano.')
    if frame.duplicated(['ANO','COD_MUN','INDICADOR']).any():
        raise ValueError('Observações municipais duplicadas.')
    totals = summarize(frame, ['INDICADOR'])
    definitions = catalog.loc[catalog.ANO.eq(year), ['INDICADOR','DESCRICAO','SERIE']]
    result = totals.merge(definitions, on='INDICADOR', how='left', validate='one_to_one')
    for name,column in [('PCT_ATINGIRAM','ATINGIRAM'),('PCT_NAO_ATINGIRAM','NAO_ATINGIRAM'),('PCT_SEM_INFORMACAO','SEM_INFORMACAO')]:
        # Barras distribuem TODAS as observações, incluindo situação desconhecida.
        result[name] = 100 * result[column] / result.OBSERVACOES.replace(0,np.nan)
    result['SEM_REGISTRO'] = frame.COD_MUN.nunique() - result.MUNICIPIOS
    result['ANO'] = year
    return result


def municipal_profiles(frame, indicator_count):
    if frame.ANO.nunique() > 1:
        raise ValueError('Perfil exige um único ano.')
    profiles = municipal_ranking(frame)
    profiles['SEM_REGISTRO'] = indicator_count - profiles.OBSERVACOES
    if profiles.SEM_REGISTRO.lt(0).any():
        raise ValueError('Quantidade de indicadores incompatível.')
    # Descritivo: situações conhecidas, sem afirmar aplicabilidade oficial.
    profiles['FAIXA'] = pd.cut(profiles.CUMPRIMENTO, [-np.inf,30,50,70,90,np.inf], right=False,
                               labels=BANDS[:-1]).astype('string').fillna(BANDS[-1])
    return profiles


def profile_distribution(profiles):
    counts = profiles.FAIXA.value_counts().reindex(BANDS,fill_value=0)
    return pd.DataFrame({'FAIXA':counts.index, 'MUNICIPIOS':counts.values,
                         'PERCENTUAL':100*counts.values / len(profiles) if len(profiles) else np.zeros(len(counts))})


def profile_thresholds(profiles):
    known = profiles.loc[profiles.AVALIADOS.gt(0)]
    return {threshold:{'municipalities':int(known.CUMPRIMENTO.ge(threshold).sum()),
                       'denominator':len(known),
                       'percent':100*known.CUMPRIMENTO.ge(threshold).mean() if len(known) else np.nan}
            for threshold in [30,50,70,90]}


@st.cache_data(show_spinner=False,max_entries=12)
def annual_aggregations(signature, year):
    base,catalog = load_data(signature)
    frame = filter_data(base,year=year)
    return summarize(frame,['UF','INDICADOR']), catalog.loc[catalog.ANO.eq(year)].copy()


@st.cache_data(show_spinner=False,max_entries=24)
def state_dashboard(signature, year, uf='Todos'):
    base,catalog = load_data(signature)
    frame = filter_data(base,year=year,uf=uf)
    count = catalog.loc[catalog.ANO.eq(year),'INDICADOR'].nunique()
    summary = indicator_summary(frame,catalog,year)
    profiles = municipal_profiles(frame,count)
    return summary, profiles, profile_distribution(profiles), profile_thresholds(profiles)
