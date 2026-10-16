"""Exploração histórica descritiva; não une definições por numeração."""
import hashlib
import json
import re
import numpy as np
import pandas as pd
import streamlit as st
from src.data import load_data, filter_data, series_key, text_key
from src.metrics import summarize
from src.state_analysis import profile_thresholds


def _catalog_signature(catalog):
    fields = sorted((series_key(r.DESCRICAO,r.INDICADOR,r.UNIDADE), text_key(r.LABEL_META)) for r in catalog.itertuples())
    return hashlib.sha256(json.dumps(fields).encode()).hexdigest()


def profile_evolution(frame, catalog, years):
    """Quatro patamares por ano, usando todas as metas daquele período."""
    if frame.duplicated(['ANO','COD_MUN','INDICADOR']).any():
        raise ValueError('Perfil histórico contém observações duplicadas.')
    profiles = summarize(frame,['ANO','COD_MUN','NOME_MUN','UF'])
    rows, coverage = [], []
    previous_signature = previous_cohort = None
    for year in sorted(years):
        definitions = catalog.loc[catalog.ANO.eq(year)]
        local = profiles.loc[profiles.ANO.eq(year)]
        indicator_count = definitions.INDICADOR.nunique()
        missing = indicator_count * len(local) - int(local.OBSERVACOES.sum())
        if missing < 0:
            raise ValueError('Catálogo incompatível com as observações do período.')
        signature = _catalog_signature(definitions)
        cohort = frozenset(local.COD_MUN.astype(str))
        info = {'ANO':year,'MUNICIPIOS_OBSERVADOS':len(local),
                'MUNICIPIOS_AVALIADOS':int(local.AVALIADOS.gt(0).sum()),
                'SEM_AVALIACAO':int(local.AVALIADOS.eq(0).sum()),
                'INDICADORES_CATALOGO':indicator_count,'AVALIACOES':int(local.AVALIADOS.sum()),
                'SEM_INFORMACAO':int(local.SEM_INFORMACAO.sum()), 'SEM_REGISTRO':missing,
                'CATALOGO_MUDOU':previous_signature is not None and signature != previous_signature,
                'COORTE_MUDOU':previous_cohort is not None and cohort != previous_cohort}
        coverage.append(info)
        for threshold, metric in profile_thresholds(local).items():
            rows.append({**info,'PATAMAR':threshold,'MUNICIPIOS':metric['municipalities'],
                         'DENOMINADOR':metric['denominator'],'PERCENTUAL':metric['percent']})
        previous_signature, previous_cohort = signature, cohort
    return pd.DataFrame(rows), pd.DataFrame(coverage)


def comparable_series_history(frame, catalog, years, minimum_years=3):
    """Uma célula por SERIE/ano; séries anuais inseguras nunca são agrupadas."""
    definitions = catalog.loc[catalog.ANO.isin(years)].copy()
    ambiguous = definitions.groupby(['SERIE','ANO'],observed=True).INDICADOR.nunique().gt(1)
    ambiguous_ids = {key[0] for key in ambiguous[ambiguous].index}
    frame = frame.loc[frame.ANO.isin(years)]
    yearly = summarize(frame,['SERIE','ANO'])
    eligible = yearly.dropna(subset=['CUMPRIMENTO']).groupby('SERIE',observed=True).ANO.nunique()
    selected = (set(eligible[eligible.ge(minimum_years)].index) & set(definitions.SERIE)) - ambiguous_ids
    excluded = int(definitions.SERIE.nunique() - len(selected))
    definitions = definitions.loc[definitions.SERIE.isin(selected)]
    yearly = yearly.loc[yearly.SERIE.isin(selected)]
    result = yearly.merge(definitions[['SERIE','ANO','INDICADOR','DESCRICAO','LABEL_META']],on=['SERIE','ANO'],how='left',validate='one_to_one')
    labels = {}
    for series, group in definitions.groupby('SERIE',observed=True):
        latest = group.sort_values('ANO').iloc[-1]
        name = re.sub(r'^indicador\s*\d+\s*[-–—:]?\s*','',str(latest.DESCRICAO),flags=re.I)
        name = re.sub(r'^(?:Proporção|Percentual|Número) de\s+','',name,flags=re.I)
        numbers = '/'.join(sorted(group.INDICADOR.astype(str).str.removeprefix('IND_').unique()))
        labels[series] = f'{numbers} · {int(group.ANO.min())}–{int(group.ANO.max())} · {name[:36].rstrip()}' + ('…' if len(name)>36 else '')
    # Identificadores explícitos distinguem eventuais prefixos de texto iguais.
    duplicated = pd.Series(labels).duplicated(keep=False)
    for series in duplicated[duplicated].index:
        labels[series] += f' · {str(series)[:6]}'
    result['ROTULO'] = result.SERIE.astype('string').map(labels)
    return result, excluded


@st.cache_data(show_spinner=False,max_entries=12)
def historical_exploration(signature, uf, period):
    base,catalog = load_data(signature)
    years = sorted(int(y) for y in base.ANO.unique() if period[0] <= y <= period[1])
    frame = filter_data(base,uf=uf)
    frame = frame.loc[frame.ANO.isin(years)]
    catalog = catalog.loc[catalog.ANO.isin(years)]
    evolution,coverage = profile_evolution(frame,catalog,years)
    series,excluded = comparable_series_history(frame,catalog,years)
    return evolution,coverage,series,excluded
