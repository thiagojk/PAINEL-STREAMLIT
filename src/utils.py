import pandas as pd
import re


def number(value, decimals=0):
    if pd.isna(value):
        return '—'
    return f'{value:,.{decimals}f}'.replace(',', '§').replace('.', ',').replace('§', '.')


def percent(value):
    return '—' if pd.isna(value) else f'{number(value, 1)}%'


def result(value, unit='Original'):
    if pd.isna(value):
        return '—'
    return number(value, 2) + ('%' if unit == '%' else '')


def description_label(row):
    # O código do registro é a referência de apresentação na renumeração.
    # A descrição bruta continua nas exportações.
    desc = re.sub(r'^indicador\s*\d+\s*[-–—:]?\s*', '', str(row.DESCRICAO), flags=re.I).strip()
    return f'Indicador {str(row.INDICADOR).removeprefix("IND_")} — {desc}'
