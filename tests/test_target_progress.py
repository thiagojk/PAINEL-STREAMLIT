"""Regras complementares, guards históricos, geometrias e troca de modo."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from src import charts, theme
from src.data import DATA, file_signature, filter_data
from src.geography import municipality_layer, load_geojson, map_signature
from src.rules import load_versions
from src.target_progress import (calculate_target_progress, progress_rule, progress_layer,
                                 progress_signature, continuous_compatibility)
from src.territorial_history import prepare_history

RULE={'supports_progress_map':True,'target_rule':'GREATER_EQUAL','progress_rule':'ratio_to_positive_target'}

@pytest.mark.parametrize('value,target,actual,visual',[(0,80,0,0),(40,80,50,50),(80,80,100,100),(96,80,120,100)])
def test_valid_increasing_rule_and_cap(value,target,actual,visual):
    v=calculate_target_progress(value,target,RULE)
    assert v.valid and v.actual==actual and v.visual==visual

@pytest.mark.parametrize('value,target',[(None,80),(np.nan,80),(np.inf,80),(40,None),(40,np.nan),(40,0),(40,-1),(-1,80)])
def test_invalid_numbers_never_become_zero(value,target):
    v=calculate_target_progress(value,target,RULE)
    assert not v.valid and v.actual is None and v.visual is None and v.reason

@pytest.mark.parametrize('direction',['LESS_EQUAL','MAINTAIN_ZERO','COMPOSITE'])
def test_no_unvalidated_inverse_zero_or_composite_formula(direction):
    v=calculate_target_progress(1,2,{**RULE,'target_rule':direction})
    assert not v.valid and 'sem transformação' in v.reason


def test_baseline_and_unsupported_are_explicit():
    rule={**RULE,'target_rule':'REDUCTION_FROM_BASELINE'}
    assert 'Baseline ausente' in calculate_target_progress(10,15,rule).reason
    assert not calculate_target_progress(10,15,rule,baseline=12).valid
    assert not calculate_target_progress(10,15,None).valid
    assert not calculate_target_progress(10,15,{'supports_progress_map':False}).valid

@pytest.fixture(scope='module')
def data():
    return pd.read_parquet(DATA/'base_pqavs.parquet'),pd.read_parquet(DATA/'indicadores.parquet')


def test_annual_registry_exact_match_and_official_policy_unchanged(data):
    _,catalog=data
    version=next(v for v in load_versions() if v['start_year']==2013)
    assert version['status']=='source_only' and not version['indicators'] and version['state_incentive'] is None
    rules=[progress_rule(r) for r in catalog.itertuples()]
    assert all(rules) and len(rules)==128
    assert sum(r['supports_progress_map'] for r in rules)==92
    entry=catalog.iloc[0].copy();entry.SERIE='wrong'
    assert progress_rule(entry) is None
    entry=catalog.iloc[0].copy();entry.META_NUMERICA=1
    assert progress_rule(entry) is None
    entry=catalog.iloc[0].copy();entry.ANO=2025
    assert progress_rule(entry) is None
    assert not progress_rule(catalog.query('ANO==2021 and INDICADOR=="IND_12"').iloc[0])['supports_progress_map']

@pytest.mark.parametrize('uf',['PA','AC'])
def test_real_layer_zero_absence_consistency_tooltip_and_fixed_scale(data,uf):
    base,catalog=data
    geometry=load_geojson(map_signature(uf))
    row=catalog.query('ANO==2021 and INDICADOR=="IND_01"').iloc[0]
    frame=filter_data(base,year=2021,indicator='IND_01',uf=uf)
    layer=municipality_layer(frame,geometry)
    original=layer.copy(deep=True)
    derived=progress_layer(layer,row,progress_signature())
    pd.testing.assert_frame_equal(layer,original)
    assert derived.GRAU_VALIDO.any()
    valid=derived[derived.GRAU_VALIDO]
    np.testing.assert_allclose(valid.GRAU_REAL,100*valid.RES_EXIBICAO/90)
    assert valid.GRAU_VISUAL.le(100).all()
    fig=charts.target_progress_map(derived,geometry,2021,row.DESCRICAO,row.LABEL_META)
    assert len(set(x for t in fig.data for x in t.locations))==len(geometry['features'])
    assert all(t.zmin==0 and t.zmax==100 for t in fig.data)
    assert fig.data[0].colorscale==tuple(map(tuple,theme.MAP_SCALE))
    for field in ['Ano:','Indicador:','Resultado:','Meta:','Grau de alcance:','Situação da fonte:']:
        assert field in fig.data[0].hovertemplate
    # Mesmo recorte com zero real, resultado ausente e denominador zero.
    synthetic=layer.iloc[:3].copy()
    synthetic['NUM']=[0,1,1];synthetic['DEN']=[10,10,0]
    synthetic['RES_EXIBICAO']=[0,np.nan,10]
    values=progress_layer(synthetic,row,('synthetic',uf))
    assert values.GRAU_VALIDO.tolist()==[True,False,False]
    assert values.GRAU_VISUAL.iloc[0]==0 and values.GRAU_VISUAL.iloc[1:].isna().all()
    empty=municipality_layer(frame.iloc[:0],geometry)
    absent=progress_layer(empty,row,('empty',uf))
    assert not absent.GRAU_VALIDO.any() and absent.GRAU_VISUAL.isna().all()
    gray=charts.target_progress_map(absent,geometry,2021,row.DESCRICAO,row.LABEL_META)
    assert len(gray.data)==1 and gray.data[0].colorscale[0][1]==theme.NEUTRAL and not gray.data[0].showscale


def test_continuous_history_renumbering_and_concept_guard(data):
    _,catalog=data
    entries=catalog[(catalog.ANO.isin([2016,2021])) & catalog.INDICADOR.eq('IND_14')]
    assert not continuous_compatibility(entries)[0]  # mesmo número, conceitos diferentes
    series=catalog.query('ANO==2021 and INDICADOR=="IND_14"').iloc[0].SERIE
    entries=catalog[catalog.SERIE.eq(series)]
    assert continuous_compatibility(entries)[0]
    geometry=load_geojson(map_signature('PA'))
    items=prepare_history(file_signature(),series,'PA',(2016,2021),map_signature('PA'))
    for item in items:
        derived=progress_layer(item['data'],item['entry'],progress_signature())
        fig=charts.target_progress_map(derived,geometry,item['year'],'Indicador',item['entry'].LABEL_META)
        assert fig.data[0].zmin==0 and fig.data[0].zmax==100
    unsupported=catalog.query('ANO==2021 and INDICADOR=="IND_08"')
    assert not continuous_compatibility(unsupported)[0]


def test_mode_preserves_filters_history_status_and_unavailable(data):
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=60)
    app.radio(key='pagina').set_value('Mapas').run(timeout=60)
    app.selectbox(key='mapa_uf').set_value('PA').run(timeout=60)
    app.selectbox(key='mapa_indicador').set_value('IND_14').run(timeout=60)
    app.toggle(key='mapa_historico').set_value(True).run(timeout=60)
    app.sidebar.multiselect[0].set_value([2016,2021]).run(timeout=60)
    # Opera o rádio único na sidebar, sem simular um estado paralelo.
    app.sidebar.radio(key='map_mode').set_value('Grau de alcance (%)').run(timeout=60)
    assert app.selectbox(key='mapa_uf').value=='PA'
    assert app.selectbox(key='mapa_indicador').value=='IND_14'
    assert app.sidebar.multiselect[0].value==[2016,2021]
    assert len(app.get('plotly_chart'))==2
    assert not app.exception and not app.error
    app.sidebar.radio(key='map_mode').set_value('Situação da meta').run(timeout=60)
    assert len(app.get('plotly_chart'))==2 and app.sidebar.multiselect[0].value==[2016,2021]
    app.sidebar.radio(key='map_mode').set_value('Grau de alcance (%)').run(timeout=60)
    app.selectbox(key='mapa_indicador').set_value('IND_08').run(timeout=60)
    assert any('Grau percentual de alcance não disponível' in i.value for i in app.info)
    assert len(app.get('plotly_chart'))==0  # só o histórico, com ano indisponível explícito
    app.selectbox(key='mapa_uf').set_value('Todos').run(timeout=60)
    assert any('nem resultado estadual validado' in i.value for i in app.info)
    assert not app.exception and not app.error


def test_color_contrast_semantics_and_sequential_luminance():
    def luminance(h):
        rgb=[int(h[i:i+2],16)/255 for i in [1,3,5]]
        c=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb]
        return sum(x*w for x,w in zip(c,[.2126,.7152,.0722]))
    def contrast(a,b):
        l=sorted([luminance(a),luminance(b)])
        return (l[1]+.05)/(l[0]+.05)
    for color in [theme.PRIMARY,theme.PRIMARY_DARK,theme.TEXT_PRIMARY,theme.TEXT_SECONDARY,theme.POSITIVE,theme.NEGATIVE]:
        assert contrast(color,theme.SURFACE)>=4.5
    assert theme.COLORS==charts.COLORS
    light=[luminance(c) for _,c in theme.MAP_SCALE]
    assert light==sorted(light,reverse=True)
    assert theme.MAP_SCALE[0][1]!=theme.NEUTRAL
