"""GeoJSON local, associação explícita e agregação com as métricas existentes."""
from __future__ import annotations
import json
from pathlib import Path
import re
import pandas as pd
import streamlit as st
from src.data import ROOT, STATUS, filter_data
from src.metrics import summarize

MAPS = ROOT / 'assets/maps'
# Código oficial da UF (dois primeiros dígitos do código municipal IBGE).
UF_CODES = {'RO':'11','AC':'12','AM':'13','RR':'14','PA':'15','AP':'16','TO':'17',
 'MA':'21','PI':'22','CE':'23','RN':'24','PB':'25','PE':'26','AL':'27','SE':'28','BA':'29',
 'MG':'31','ES':'32','RJ':'33','SP':'35','PR':'41','SC':'42','RS':'43',
 'MS':'50','MT':'51','GO':'52','DF':'53'}


def geographic_code(code: str) -> str:
    """GeoJSON tem sete dígitos; a chave da fonte são os seis primeiros.

    Não calcula nem acrescenta dígito verificador; não altera COD_MUN da base.
    Unicidade e UF são verificadas antes da associação.
    """
    if not isinstance(code, str) or not re.fullmatch(r'\d{7}', code):
        raise ValueError('Código geográfico deve ser texto de sete dígitos.')
    return code[:6]


def _read_geojson(path: Path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('type') != 'FeatureCollection':
        raise ValueError('GeoJSON deve ser uma coleção de feições.')
    ids = [f['id'] for f in data['features']]
    if len(ids) != len(set(ids)):
        raise ValueError('GeoJSON contém identificadores duplicados.')
    return data


def map_signature(uf=None, directory=MAPS):
    if uf is not None and uf not in UF_CODES:
        raise ValueError('UF inválida.')
    path = Path(directory) / (f'municipios/{uf}.geojson' if uf else 'brasil_ufs.geojson')
    return str(path), path.stat().st_mtime_ns, path.stat().st_size


@st.cache_data(show_spinner=False, max_entries=8)
def load_geojson(signature):
    return _read_geojson(Path(signature[0]))


def geographic_index(directory=MAPS):
    records = []
    for uf in sorted(UF_CODES):
        data = _read_geojson(Path(directory) / f'municipios/{uf}.geojson')
        for f in data['features']:
            p = f['properties']
            code = geographic_code(p['COD_MUN_GEO'])
            if code != p['COD_MUN'] or p['UF'] != uf or code[:2] != UF_CODES[uf]:
                raise ValueError(f'Código/UF incompatível: {code}')
            records.append({'COD_MUN': code, 'UF': uf, 'COD_MUN_GEO': p['COD_MUN_GEO']})
    result = pd.DataFrame(records)
    if result.COD_MUN.duplicated().any():
        raise ValueError('Prefixos geográficos municipais não são únicos.')
    return result


def correspondence_report(base, directory=MAPS):
    index = geographic_index(directory)
    places = base[['COD_MUN','NOME_MUN','UF']].drop_duplicates()
    joined = places.merge(index, on=['COD_MUN','UF'], how='left', validate='one_to_one')
    missing = joined[joined.COD_MUN_GEO.isna()][['COD_MUN','NOME_MUN','UF']]
    extra = index.merge(places[['COD_MUN','UF']], on=['COD_MUN','UF'], how='left', indicator=True)
    return {'municipios_base': len(places), 'associados': int(joined.COD_MUN_GEO.notna().sum()),
            'nao_associados': len(missing), 'municipios_nao_associados': missing.to_dict('records'),
            'taxa_percentual': 100 * joined.COD_MUN_GEO.notna().mean(),
            'geometrias_sem_codigo_na_base': extra.loc[extra._merge.eq('left_only'), ['COD_MUN','UF']].to_dict('records')}


@st.cache_data(show_spinner=False, max_entries=24)
def state_summary(frame):
    """Um indicador por vez: a unidade de avaliação é o município."""
    if frame.INDICADOR.nunique() > 1 or frame.ANO.nunique() > 1:
        raise ValueError('Mapa exige um ano e um indicador.')
    return summarize(frame, ['UF'])


def municipality_layer(frame, geojson):
    """Sem observação e situação ausente têm legenda cinza, sem imputar registros."""
    if frame.INDICADOR.nunique() > 1 or frame.ANO.nunique() > 1:
        raise ValueError('Mapa exige um ano e um indicador.')
    if frame.COD_MUN.duplicated().any():
        raise ValueError('Mais de uma observação por município neste recorte.')
    places = pd.DataFrame([f['properties'] for f in geojson['features']])
    joined = places.merge(frame, on=['COD_MUN','UF'], how='left', validate='one_to_one', indicator=True)
    joined['TEM_OBSERVACAO'] = joined._merge.eq('both')
    joined['SITUACAO_MAPA'] = joined.SITUACAO.astype('string').fillna(STATUS[2])
    joined['NOME_EXIBICAO'] = joined.NOME_MUN.astype('string').fillna(joined.NOME_GEO)
    return joined.drop(columns='_merge')


def map_metadata():
    return json.loads((MAPS / 'manifest.json').read_text(encoding='utf-8'))
