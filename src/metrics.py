"""Métricas com denominadores explícitos. Não agrega resultados incompatíveis."""
import numpy as np
import pandas as pd
from src.data import STATUS


def summarize(frame: pd.DataFrame, groups: list[str] | None = None) -> pd.DataFrame:
    groups = groups or []
    frame = frame.assign(
        ATINGIRAM=frame.SITUACAO.eq(STATUS[0]).astype('int32'),
        NAO_ATINGIRAM=frame.SITUACAO.eq(STATUS[1]).astype('int32'),
        SEM_INFORMACAO=frame.SITUACAO.eq(STATUS[2]).astype('int32'),
    )
    if not groups:
        frame = frame.assign(RECORTE='Total')
        groups = ['RECORTE']
    result = frame.groupby(groups, observed=True, dropna=False).agg(
        MUNICIPIOS=('COD_MUN', 'nunique'), OBSERVACOES=('SITUACAO', 'size'),
        ATINGIRAM=('ATINGIRAM', 'sum'), NAO_ATINGIRAM=('NAO_ATINGIRAM', 'sum'),
        SEM_INFORMACAO=('SEM_INFORMACAO', 'sum'),
    ).reset_index()
    result['AVALIADOS'] = result.ATINGIRAM + result.NAO_ATINGIRAM
    result['CUMPRIMENTO'] = 100 * result.ATINGIRAM / result.AVALIADOS.replace(0, np.nan)
    result['NAO_CUMPRIMENTO'] = 100 * result.NAO_ATINGIRAM / result.AVALIADOS.replace(0, np.nan)
    result['COBERTURA'] = 100 * result.AVALIADOS / result.OBSERVACOES.replace(0, np.nan)
    return result


def history(frame):
    return summarize(frame, ['ANO']).sort_values('ANO')


def variation(frame):
    valid = frame.dropna(subset=['CUMPRIMENTO']).sort_values('ANO')
    if len(valid) < 2:
        return None
    first, last = valid.iloc[0], valid.iloc[-1]
    delta = float(last.CUMPRIMENTO - first.CUMPRIMENTO)
    return {'inicio': int(first.ANO), 'fim': int(last.ANO), 'pontos_percentuais': delta,
            'variacao_relativa': delta / first.CUMPRIMENTO * 100 if first.CUMPRIMENTO else None}


def municipal_ranking(frame):
    result = summarize(frame, ['COD_MUN', 'NOME_MUN', 'UF'])
    result = result.sort_values(['CUMPRIMENTO', 'AVALIADOS', 'NOME_MUN'], ascending=[False, False, True], na_position='last')
    # Empates compartilham posição; ausência de avaliação não recebe posição.
    result['POSICAO'] = result.CUMPRIMENTO.rank(method='min', ascending=False).astype('Int64')
    if frame.INDICADOR.nunique() == 1 and frame.ANO.nunique() == 1:
        result = result.merge(frame[['COD_MUN', 'RES_EXIBICAO', 'UNIDADE', 'META', 'SITUACAO', 'POP_ANO']], on='COD_MUN')
    return result


def single_municipality_trajectory(frame, catalog):
    if frame.COD_MUN.nunique() != 1 or frame.SERIE.nunique() != 1:
        raise ValueError('Trajetória exige um município e uma definição do indicador.')
    return frame.merge(catalog[['ANO', 'INDICADOR', 'META_NUMERICA', 'LABEL_META']], on=['ANO', 'INDICADOR'], how='left').sort_values('ANO')
