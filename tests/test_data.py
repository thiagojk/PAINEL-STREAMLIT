from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.data import (numeric, clean_missing, detect_indicators, goal_status, normalize_dimensions,
                      series_key, wide_to_long, result_scale, filter_data, available_indicators,
                      available_municipalities, load_data, file_signature, DATA)
from src.metrics import summarize, history, variation, municipal_ranking, single_municipality_trajectory
from scripts.preparar_dados import prepare


def test_missing_and_brazilian_numeric():
    raw = pd.Series(['NULL', 'NA', ' n/a ', '', None, '1.234,50', '0.85', '0', 'inválido', 'inf'])
    values = numeric(raw)
    assert values.iloc[:5].isna().all()
    assert values.iloc[5:8].tolist() == [1234.5, .85, 0.]
    assert values.iloc[8:].isna().all()
    assert clean_missing(pd.Series([' Sim ', 'Não'])).tolist() == ['Sim', 'Não']


def test_generic_indicator_detection():
    d = detect_indicators(['IND_01_NUM', 'IND_01_RES', 'IND_99_ALCANCE_META', 'IND_105_DEN', 'OTHER', 'IND_03_BAD'])
    assert set(d) == {'IND_01', 'IND_99', 'IND_105'}
    assert d['IND_99'] == {'ALCANCE_META': 'IND_99_ALCANCE_META'}


def test_status_priority_fallback_and_conflicts():
    status, conflicts = goal_status(pd.Series([1, 0, None, None, None, 2, None]),
                                   pd.Series(['Não', 'Sim', 'Sim', 'Não', 0, 'Sim', 'NA']))
    assert status.tolist() == ['Atingida', 'Não atingida', 'Atingida', 'Não atingida', 'Sem informação', 'Atingida', 'Sem informação']
    assert conflicts.tolist() == [True, True, False, False, False, False, False]


def fixture_wide():
    return pd.DataFrame({'ANO': [2020]*6, 'UF': ['PA']*3+['AC']*3,
        'COD_MUN': ['001234','150010','150020','120001','120005','120010'],
        'NOME_MUN': ['A','B','C','D','E','F'], 'POP_ANO': [100]*6,
        'IND_01_NUM': [8,9,10,8,9,10], 'IND_01_DEN': [10]*6, 'IND_01_RES': [.8,.9,1,.8,.9,1],
        'IND_01_META': ['Não','Sim','Sim','Não','Sim','Sim'], 'IND_01_ALCANCE_META': [0,1,1,0,1,1],
        'IND_15_META': [0]*6, 'IND_15_ALCANCE_META': ['NULL']*6})


def fixture_dictionary():
    return pd.DataFrame([{'ANO':2020,'INDICADOR':'IND_01','DESCRICAO':'Indicador 1 - Proporção de registros.',
                          'LABEL_META':'Meta >= 90%','LABEL_NUM':'Registros','LABEL_DEN':'Total'}])


def test_dimensions_preserve_codes_validate_year():
    d = normalize_dimensions(fixture_wide())
    assert d.COD_MUN.iloc[0] == '001234'
    assert d.ANO.dtype == 'int16'
    with pytest.raises(ValueError, match='ANO'):
        normalize_dimensions(fixture_wide().assign(ANO=2020.5))
    with pytest.raises(ValueError, match='Colunas'):
        normalize_dimensions(fixture_wide().drop(columns='UF'))


def test_wide_long_new_indicator_and_placeholder():
    frame, cat = wide_to_long(fixture_wide(), fixture_dictionary())
    assert len(frame) == 6
    assert cat.INDICADOR.tolist() == ['IND_01']
    assert frame.RES_EXIBICAO.tolist() == [80,90,100,80,90,100]
    assert cat.META_NUMERICA.iloc[0] == 90
    source = fixture_wide().assign(IND_99_RES=15)
    new, catalog = wide_to_long(source, fixture_dictionary())
    assert len(new) == 12
    assert 'IND_99' in catalog.INDICADOR.tolist()
    assert catalog[catalog.INDICADOR.eq('IND_99')].UNIDADE.iloc[0] == 'Original'


def test_scale_never_uses_maximum_heuristic():
    block = pd.DataFrame({'NUM':[8]*6, 'DEN':[10]*6,'RES':[.8]*6})
    assert result_scale(block,'Proporção de registros','Meta >= 90%')[:2] == (100., '%')
    assert result_scale(block.assign(RES=80),'Proporção de registros','Meta >= 90%')[:2] == (1., '%')
    assert result_scale(block,'Número de testes','Meta 2 testes')[:2] == (1., 'Original')
    assert result_scale(block.assign(RES=.2),'Proporção de registros','Meta >= 90%')[1] == 'Original'
    assert result_scale(block,'Proporção de registros','Meta 50 semanas')[1] == 'Original'


def test_filters_year_uf_code_and_availability():
    data, cat = wide_to_long(fixture_wide(), fixture_dictionary())
    assert len(filter_data(data, year=2020, uf='PA')) == 3
    assert len(filter_data(data, municipality='001234')) == 1
    assert filter_data(data, year=2019).empty
    assert len(available_municipalities(data, uf='AC')) == 3
    assert available_indicators(cat, 2020) == ['IND_01']
    assert available_indicators(cat, 2019) == []


def test_denominator_unknown_and_multiple_indicators():
    data, cat = wide_to_long(fixture_wide(), fixture_dictionary())
    data['SITUACAO'] = ['Atingida','Não atingida','Sem informação','Atingida','Sem informação','Sem informação']
    s = summarize(data).iloc[0]
    assert s.AVALIADOS == 3
    assert s.SEM_INFORMACAO == 3
    assert s.CUMPRIMENTO == pytest.approx(200/3)
    assert s.COBERTURA == 50
    unknown = summarize(data.assign(SITUACAO='Sem informação')).iloc[0]
    assert np.isnan(unknown.CUMPRIMENTO)
    assert summarize(data.iloc[0:0]).empty
    ranking = municipal_ranking(data)
    assert ranking.POSICAO.notna().sum() == 3


def test_history_variation_and_definition_identity():
    data, cat = wide_to_long(fixture_wide(), fixture_dictionary())
    other = data.assign(ANO=2021, SITUACAO='Atingida')
    h = history(pd.concat([data,other]))
    v = variation(h)
    assert (v['inicio'],v['fim']) == (2020,2021)
    assert v['pontos_percentuais'] == pytest.approx(100/3)
    assert series_key('Indicador 7 - Proporção de registros.', 'IND_07','%') == series_key('Indicador 9 - Proporção de registros.', 'IND_09','%')
    assert series_key('Proporção de registros','IND_01','%') != series_key('Proporção de vacinas','IND_01','%')
    assert series_key('Proporção de registros','IND_01','%') != series_key('Proporção de registros','IND_01','Original')
    with pytest.raises(ValueError):
        single_municipality_trajectory(data,cat)


def test_duplicates_rejected():
    f = fixture_wide()
    with pytest.raises(ValueError,match='duplicadas'):
        wide_to_long(pd.concat([f,f],ignore_index=True),fixture_dictionary())


def test_excel_to_parquet_roundtrip(tmp_path):
    source=tmp_path/'fonte.xlsx'
    d=fixture_dictionary().assign(INDICADOR=1)
    with pd.ExcelWriter(source) as writer:
        d.to_excel(writer,sheet_name='Indicadores e Metas por Ano',index=False)
        fixture_wide().to_excel(writer,sheet_name='PQA_VS_2020',index=False)
    out=tmp_path/'data'
    metadata=prepare(source,out)
    assert metadata['observacoes'] == 6
    base, cat=load_data(file_signature(out),str(out))
    assert base.COD_MUN.iloc[0] == '001234'
    assert base.RES.iloc[0] == .8
    assert cat.META_NUMERICA.iloc[0] == 90
    # Reexecutar mantém conteúdo; não acumula linhas.
    prepare(source,out)
    assert len(pd.read_parquet(out/'base_pqavs.parquet')) == 6


def test_real_dataset_integrity_and_renumbering():
    base,cat=load_data(file_signature())
    assert len(base) == 712708
    assert base.COD_MUN.nunique() == 5570
    assert sorted(base.ANO.unique()) == list(range(2013,2022))
    assert not base.duplicated(['ANO','COD_MUN','INDICADOR']).any()
    assert base[base.INDICADOR.eq('IND_15')].ANO.unique().tolist() == [2016,2017]
    assert base.CONFLITO_META.sum() == 4784
    a=cat[cat.ANO.eq(2017)&cat.INDICADOR.eq('IND_15')].SERIE.iloc[0]
    b=cat[cat.ANO.eq(2018)&cat.INDICADOR.eq('IND_14')].SERIE.iloc[0]
    assert a == b  # Mesmo conceito, numeração diferente.
    assert cat[cat.ANO.eq(2017)&cat.INDICADOR.eq('IND_14')].SERIE.iloc[0] != b
    missing=base[base.ANO.isin([2020,2021])&base.INDICADOR.eq('IND_08')]
    assert missing.RES.isna().all()
    assert missing.SITUACAO.ne('Sem informação').all()
