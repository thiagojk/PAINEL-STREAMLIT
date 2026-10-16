"""Leitura, limpeza e transformação; nenhuma regra de meta é inventada."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DIMENSIONS = ['ANO', 'UF', 'COD_MUN', 'NOME_MUN', 'POP_ANO']
FIELDS = ['NUM', 'DEN', 'RES', 'META', 'ALCANCE_META']
MISSING = {'', 'null', 'na', 'n/a', 'nan', 'none', 'nat', '-'}
STATUS = ['Atingida', 'Não atingida', 'Sem informação']


def text_key(value: object) -> str:
    s = unicodedata.normalize('NFKD', str(value).strip().lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


def clean_missing(s: pd.Series) -> pd.Series:
    text = s.astype('string').str.strip()
    return text.mask(text.str.lower().isin(MISSING))


def numeric(s: pd.Series) -> pd.Series:
    s = clean_missing(s)
    # Formatação brasileira com vírgula; ponto isolado mantém escala original.
    comma = s.str.contains(',', na=False)
    s = s.where(~comma, s.str.replace('.', '', regex=False).str.replace(',', '.', regex=False))
    return pd.to_numeric(s, errors='coerce').replace([np.inf, -np.inf], np.nan).astype('float64')


def detect_indicators(columns) -> dict[str, dict[str, str]]:
    result = {}
    for c in columns:
        match = re.fullmatch(r'IND_(\d+)_(NUM|DEN|RES|META|ALCANCE_META)', str(c).strip().upper())
        if match:
            key = f'IND_{int(match[1]):02d}'
            result.setdefault(key, {})[match[2]] = c
    return dict(sorted(result.items()))


def goal_status(alcance: pd.Series, meta: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Prioridade: flag 0/1; fallback apenas Sim/Não. META=0 não é Não."""
    flag = numeric(alcance)
    fallback = clean_missing(meta).map(lambda x: text_key(x) if pd.notna(x) else '')
    fallback = fallback.map({'sim': 1., 'nao': 0.})
    valid = flag.isin([0, 1])
    chosen = flag.where(valid, fallback)
    situation = chosen.map({1.: STATUS[0], 0.: STATUS[1]}).fillna(STATUS[2])
    conflict = valid & fallback.notna() & flag.ne(fallback)
    return situation, conflict


def normalize_dimensions(frame: pd.DataFrame) -> pd.DataFrame:
    missing = set(DIMENSIONS) - set(frame)
    if missing:
        raise ValueError(f'Colunas obrigatórias ausentes: {sorted(missing)}')
    result = frame[DIMENSIONS].copy()
    years = numeric(result.ANO)
    if years.isna().any() or (years % 1 != 0).any():
        raise ValueError('ANO contém valores ausentes ou não inteiros.')
    result['ANO'] = years.astype('int16')
    result['UF'] = clean_missing(result.UF).str.upper()
    result['COD_MUN'] = clean_missing(result.COD_MUN).str.replace(r'\.0$', '', regex=True)
    # A fonte usa código de seis dígitos: não acrescentar dígito verificador.
    result['NOME_MUN'] = clean_missing(result.NOME_MUN)
    result['POP_ANO'] = numeric(result.POP_ANO)
    if result[['UF', 'COD_MUN', 'NOME_MUN']].isna().any().any():
        raise ValueError('Localidade sem UF, código ou nome; corrija a fonte.')
    return result


def series_key(description: str, indicator: str, unit: str) -> str:
    # Remover somente o número; não adivinhar equivalência entre redações diferentes.
    description = re.sub(r'^indicador\s*\d+\s*[-–—:]?\s*', '', text_key(description))
    description = re.sub(r'[^a-z0-9]+', ' ', description).strip()
    if not description or description == 'descricao indisponivel':
        description = f'sem descricao {indicator}'
    return hashlib.sha256(f'{description}|{unit}'.encode()).hexdigest()[:16]


def result_scale(block: pd.DataFrame, description: str, rule: str) -> tuple[float, str, str]:
    """Conversão de proporções só com evidência de NUM/DEN, por indicador/ano."""
    desc, meta = text_key(description), text_key(rule)
    percent = ('proporcao' in desc or 'percentual' in desc) and '%' in meta
    if not percent:
        return 1., 'Original', 'Escala original; conversão não demonstrada.'
    ratio = block.NUM / block.DEN.where(block.DEN.gt(0))
    mask = ratio.notna() & ratio.ne(0) & block.RES.notna()
    if mask.sum() < 5:
        return 1., 'Original', 'Escala sem evidência numérica suficiente.'
    r, v = ratio[mask].to_numpy(), block.loc[mask, 'RES'].to_numpy()
    for factor, scale in [(1., 100.), (100., 1.)]:
        # Tolerância para arredondamento da planilha de 2013.
        share = np.isclose(v, r * factor, rtol=.015, atol=.51 if factor == 100 else .0001).mean()
        if share >= .98:
            return scale, '%', f'Escala validada contra NUM/DEN ({share:.1%} dos pares não nulos).'
    return 1., 'Original', 'Escala inconsistente; valores preservados sem conversão.'


def wide_to_long(frame: pd.DataFrame, dictionary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    dims = normalize_dimensions(frame)
    blocks, catalog = [], []
    found = detect_indicators(frame.columns)
    for indicator, fields in found.items():
        block = dims.copy()
        for field in FIELDS:
            raw = frame[fields[field]] if field in fields else pd.Series(pd.NA, index=frame.index)
            block[field] = numeric(raw) if field in ['NUM', 'DEN', 'RES', 'ALCANCE_META'] else clean_missing(raw)
        block['SITUACAO'], block['CONFLITO_META'] = goal_status(block.ALCANCE_META, block.META)
        for year, group in block.groupby('ANO', sort=True):
            entry = dictionary[(dictionary.ANO == year) & (dictionary.INDICADOR == indicator)]
            has_values = group[['NUM', 'DEN', 'RES', 'ALCANCE_META']].notna().any().any()
            has_status = group.SITUACAO.ne(STATUS[2]).any()
            if entry.empty and not has_values and not has_status:
                continue  # Coluna estrutural vazia não implica indicador disponível.
            info = entry.iloc[0].to_dict() if not entry.empty else {}
            description = str(info.get('DESCRICAO') or 'Descrição indisponível')
            rule = str(info.get('LABEL_META') or 'Regra indisponível')
            scale, unit, evidence = result_scale(group, description, rule)
            sid = series_key(description, indicator, unit)
            if unit == 'Original':
                # Mesma descrição não comprova escala histórica desconhecida.
                sid = f'{sid}-{year}'
            group = group.copy()
            group['INDICADOR'], group['SERIE'] = indicator, sid
            group['RES_EXIBICAO'] = group.RES * scale
            group['UNIDADE'] = unit
            blocks.append(group)
            m = re.fullmatch(r'Meta\s*(?:>=|≥)\s*([\d.,]+)\s*%', rule, re.I)
            threshold = float(m[1].replace(',', '.')) if m and unit == '%' else np.nan
            catalog.append({
                'ANO': int(year), 'INDICADOR': indicator, 'SERIE': sid,
                'DESCRICAO': description, 'LABEL_NUM': info.get('LABEL_NUM', 'Indisponível'),
                'LABEL_DEN': info.get('LABEL_DEN', 'Indisponível'), 'LABEL_META': rule,
                'UNIDADE': unit, 'FATOR_EXIBICAO': scale, 'META_NUMERICA': threshold,
                'ESCALA_NOTA': evidence, 'TEM_RESULTADO': bool(group.RES.notna().any()),
                'ALERTA': 'Rótulo da meta cita semanas, mas a descrição cita proporção.'
                if 'semanas' in text_key(rule) and 'proporcao' in text_key(description) else '',
            })
    if not blocks:
        raise ValueError('Nenhum indicador com dados ou definição foi encontrado.')
    result = pd.concat(blocks, ignore_index=True)
    if result.duplicated(['ANO', 'COD_MUN', 'INDICADOR']).any():
        raise ValueError('Observações duplicadas por ano, município e indicador.')
    for c in ['UF', 'COD_MUN', 'NOME_MUN', 'INDICADOR', 'SERIE', 'SITUACAO', 'UNIDADE', 'META']:
        result[c] = result[c].astype('category')
    return result, pd.DataFrame(catalog)


def read_dictionary(excel: pd.ExcelFile) -> pd.DataFrame:
    name = next((s for s in excel.sheet_names if 'indicadores' in text_key(s) and 'ano' in text_key(s)), None)
    columns = ['ANO', 'INDICADOR', 'DESCRICAO', 'LABEL_NUM', 'LABEL_DEN', 'LABEL_META']
    if name is None:
        return pd.DataFrame(columns=columns)
    d = pd.read_excel(excel, sheet_name=name, keep_default_na=False)
    d.columns = d.columns.str.strip().str.upper()
    for c in columns:
        if c not in d:
            d[c] = pd.NA
    d['ANO'] = numeric(d.ANO).astype('Int16')
    numbers = numeric(d.INDICADOR.astype('string').str.replace('IND_', '', regex=False))
    d['INDICADOR'] = numbers.map(lambda x: f'IND_{int(x):02d}' if pd.notna(x) else None)
    if d[['ANO', 'INDICADOR']].isna().any().any():
        raise ValueError('Dicionário possui ano/indicador inválido.')
    if d.duplicated(['ANO', 'INDICADOR']).any():
        raise ValueError('Dicionário duplicado por ano/indicador.')
    for c in columns[2:]:
        d[c] = clean_missing(d[c]).fillna('Indisponível')
    return d[columns]


def file_signature(directory: Path = DATA) -> tuple:
    return tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in
                 [directory / 'base_pqavs.parquet', directory / 'indicadores.parquet', directory / 'metadata.json'])


@st.cache_data(show_spinner='Carregando indicadores…', max_entries=2)
def load_data(signature: tuple, directory: str = str(DATA)) -> tuple[pd.DataFrame, pd.DataFrame]:
    path = Path(directory)
    base = pd.read_parquet(path / 'base_pqavs.parquet')
    catalog = pd.read_parquet(path / 'indicadores.parquet')
    return base, catalog


def filter_data(frame: pd.DataFrame, year=None, uf=None, municipality=None, indicator=None, series=None) -> pd.DataFrame:
    mask = pd.Series(True, index=frame.index)
    for column, value in [('ANO', year), ('UF', uf), ('COD_MUN', municipality), ('INDICADOR', indicator), ('SERIE', series)]:
        if value is not None and value != 'Todos':
            mask &= frame[column].eq(value)
    return frame.loc[mask]


def available_years(frame):
    return sorted(frame.ANO.unique().tolist())


def available_indicators(catalog, year):
    return catalog.loc[catalog.ANO.eq(year), 'INDICADOR'].sort_values().tolist()


def available_municipalities(frame, uf=None, year=None):
    return filter_data(frame, year=year, uf=uf)[['COD_MUN', 'NOME_MUN', 'UF']].drop_duplicates().sort_values(['NOME_MUN', 'UF'])
