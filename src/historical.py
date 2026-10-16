"""Catálogo de apresentação: conceitos agrupados sem unir séries anuais inseguras."""
import re
import pandas as pd
from src.data import series_key


def concept_options(catalog):
    """Mesma normalização estrita da preparação; nunca agrupa só pelo número.

    SERIE continua sendo a chave analítica. O conceito é somente o agrupador do
    seletor: escalas Original continuam exigindo a escolha de uma série anual.
    """
    rows = []
    annotated = catalog.copy()
    annotated['CONCEITO'] = [series_key(r.DESCRICAO, r.INDICADOR, r.UNIDADE) for r in catalog.itertuples()]
    for concept, group in annotated.groupby('CONCEITO', sort=False):
        latest = group.sort_values('ANO').iloc[-1]
        description = re.sub(r'^indicador\s*\d+\s*[-–—:]?\s*', '', str(latest.DESCRICAO), flags=re.I).strip()
        years = sorted(map(int, group.ANO.unique()))
        numbers = '/'.join(sorted(group.INDICADOR.str.removeprefix('IND_').unique()))
        period = str(years[0]) if len(years) == 1 else f'{years[0]}–{years[-1]}'
        short = description if len(description) <= 90 else description[:87].rstrip() + '…'
        rows.append({'CONCEITO':concept, 'LABEL':f'{numbers} · {period} — {short}',
                     'DESCRICAO':description, 'ANOS':years,
                     'SERIES':group.sort_values('ANO').SERIE.unique().tolist(),
                     'INDICADOR':latest.INDICADOR, 'ULTIMO_ANO':years[-1]})
    result = pd.DataFrame(rows).sort_values(['INDICADOR','ULTIMO_ANO','LABEL'], ascending=[True,False,True]).reset_index(drop=True)
    # Em caso de descrições com prefixos iguais, o sufixo identifica a variante.
    duplicates = result.LABEL.duplicated(keep=False)
    result.loc[duplicates,'LABEL'] += ' · definição ' + result.loc[duplicates,'CONCEITO'].str[:8]
    return result


def compatible_years(catalog, series):
    return sorted(map(int, catalog.loc[catalog.SERIE.eq(series), 'ANO'].unique()))


def representative_years(years, count=5):
    years = sorted(set(years))
    if len(years) <= count:
        return years
    return [years[round(i*(len(years)-1)/(count-1))] for i in range(count)]


def validate_map_years(selected, available):
    if len(selected) > 6:
        raise ValueError('Selecione até 6 anos para comparação territorial.')
    if len(selected) != len(set(selected)) or not set(selected).issubset(available):
        raise ValueError('Anos incompatíveis com a série selecionada.')
    return sorted(selected)
