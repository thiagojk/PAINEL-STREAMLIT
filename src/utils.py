import pandas as pd


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
    desc = str(row.DESCRICAO)
    if desc.startswith('Indicador '):
        return desc
    return f'Indicador {str(row.INDICADOR).removeprefix("IND_")} — {desc}'
