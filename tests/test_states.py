import copy
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from src import charts, views
from src.data import DATA, load_data, file_signature
from src.state_analysis import (indicator_summary, municipal_profiles, profile_distribution, profile_thresholds,
                                annual_aggregations, state_dashboard)
from src.rules import (GoalDirection, load_versions, version_for_year, indicator_rule, classify_state_incentive, category_summary)
from src.navigation import NAV_LABELS


@pytest.fixture
def example():
    records=[('A','IND_01','Atingida'),('B','IND_01','Não atingida'),('C','IND_01','Sem informação'),
             ('A','IND_02','Atingida'),('B','IND_02','Atingida')]
    frame=pd.DataFrame(records,columns=['COD_MUN','INDICADOR','SITUACAO']).assign(ANO=2017,UF='PA')
    frame['NOME_MUN']=frame.COD_MUN
    catalog=pd.DataFrame({'ANO':[2017]*2,'INDICADOR':['IND_01','IND_02'],'DESCRICAO':['Definição um','Definição dois'],'SERIE':['one','two']})
    return frame,catalog


def test_indicator_distribution_includes_unknown_and_discloses_missing(example):
    frame,catalog=example
    result=indicator_summary(frame,catalog,2017).set_index('INDICADOR')
    row=result.loc['IND_01']
    assert (row.ATINGIRAM,row.NAO_ATINGIRAM,row.SEM_INFORMACAO,row.AVALIADOS,row.OBSERVACOES)==(1,1,1,2,3)
    assert row.CUMPRIMENTO==50  # Cumprimento tem denominador diferente da barra 100%.
    assert row.PCT_ATINGIRAM==pytest.approx(100/3)
    assert np.allclose(result[['PCT_ATINGIRAM','PCT_NAO_ATINGIRAM','PCT_SEM_INFORMACAO']].sum(axis=1),100)
    assert result.loc['IND_02'].SEM_REGISTRO==1
    assert result.loc['IND_02'].OBSERVACOES==2  # Ausência não vira falha nem aplicabilidade inferida.
    fig=charts.indicator_stack(result.reset_index())
    assert len(fig.data)==3 and fig.layout.barmode=='stack'
    assert list(fig.layout.xaxis.range)==[0,100]
    assert all('Sem informação' in t.hovertemplate and 'Registros no denominador' in t.hovertemplate for t in fig.data)
    with pytest.raises(ValueError,match='duplicadas'):
        indicator_summary(pd.concat([frame,frame.iloc[:1]]),catalog,2017)


def test_profile_denominators_zero_coverage_thresholds_and_bands(example):
    frame,_=example
    profiles=municipal_profiles(frame,2).set_index('COD_MUN')
    assert profiles.loc['A'].CUMPRIMENTO==100
    assert profiles.loc['B'].CUMPRIMENTO==50
    assert np.isnan(profiles.loc['C'].CUMPRIMENTO)
    assert profiles.loc['C'].FAIXA=='Sem avaliação' and profiles.loc['C'].SEM_REGISTRO==1
    thresholds=profile_thresholds(profiles)
    assert thresholds[30]=={'municipalities':2,'denominator':2,'percent':100}
    assert thresholds[70]=={'municipalities':1,'denominator':2,'percent':50}
    distribution=profile_distribution(profiles)
    assert distribution.MUNICIPIOS.sum()==3
    assert distribution.PERCENTUAL.sum()==pytest.approx(100)
    unknown=municipal_profiles(frame.assign(SITUACAO='Sem informação'),2)
    assert all(np.isnan(t['percent']) and t['denominator']==0 for t in profile_thresholds(unknown).values())


def test_exact_profile_boundaries():
    rows=[]
    for municipality,hits in enumerate([0,3,5,7,9,10,None]):
        for i in range(10):
            rows.append({'ANO':2021,'UF':'PA','COD_MUN':str(municipality),'NOME_MUN':str(municipality),
                         'INDICADOR':f'IND_{i+1:02}',
                         'SITUACAO':'Sem informação' if hits is None else 'Atingida' if i<hits else 'Não atingida'})
    actual=municipal_profiles(pd.DataFrame(rows),10).set_index('COD_MUN').FAIXA
    assert actual.reindex(list(map(str,range(7)))).tolist()==['< 30%','30% a < 50%','50% a < 70%','70% a < 90%','≥ 90%','≥ 90%','Sem avaliação']


@pytest.mark.parametrize('year,count',[(2013,14),(2017,15),(2021,14)])
@pytest.mark.parametrize('uf',['Todos','PA','AC'])
def test_real_state_aggregations_years_territories_and_heatmap(year,count,uf):
    summary,profiles,distribution,_=state_dashboard(file_signature(),year,uf)
    assert len(summary)==count and profiles.OBSERVACOES.eq(count).all()
    assert summary.ATINGIRAM.sum()+summary.NAO_ATINGIRAM.sum()+summary.SEM_INFORMACAO.sum()==profiles.OBSERVACOES.sum()
    assert not profiles.SEM_REGISTRO.any()
    if uf!='Todos': assert set(profiles.UF)=={uf}
    territorial,definitions=annual_aggregations(file_signature(),year)
    assert len(territorial)==27*count
    fig=charts.state_heatmap(territorial,definitions)
    assert fig.data[0].zmin==0 and fig.data[0].zmax==100
    assert np.asarray(fig.data[0].z).shape==(27,count)
    if uf!='Todos':
        expected=territorial.loc[territorial.UF.eq(uf)].set_index('INDICADOR')
        actual=summary.set_index('INDICADOR')
        np.testing.assert_allclose(actual.CUMPRIMENTO,expected.CUMPRIMENTO)


def test_version_periods_do_not_invent_rules():
    assert version_for_year(2021)['status']=='source_only'
    assert version_for_year(2024) is None
    assert version_for_year(2025)['status']=='reference_only'
    assert version_for_year(2025)['reference_counts']=={'indicators':14,'universal':7,'specific':7}
    assert len(GoalDirection)==5
    versions=load_versions();versions[0]['status']='validated'
    assert all(v['status']!='validated' for v in load_versions())
    with pytest.raises(ValueError,match='sobrepostas'):
        version_for_year(2025,[version_for_year(2025)]*2)


def future_fixture(hits=8):
    version=copy.deepcopy(version_for_year(2025))
    version.update(status='validated',applicability_policy_validated=True,missing_policy='require_complete',
                   reference_counts={'indicators':10,'universal':5,'specific':5})
    version['indicators']=[{'number':f'IND_{i:02}', 'concept_id':f'concept-{i}', 'series_ids':[f'series-{i}'],
                            'name':f'Nome exclusivo 2025 {i}', 'category':'universal' if i<6 else 'specific',
                            'target':'regra de teste', 'source':'referência sintética validada',
                            'evaluation':{'direction':list(GoalDirection)[(i-1)%5].value}}
                           for i in range(1,11)]
    frame=pd.DataFrame([{'ANO':2025,'UF':'PA','COD_MUN':str(m),'INDICADOR':r['number'],'SERIE':r['series_ids'][0],
                         'SITUACAO':'Atingida' if i<hits else 'Não atingida'}
                        for m in range(10) for i,r in enumerate(version['indicators'])])
    applicability=frame[['COD_MUN','INDICADOR']].assign(APLICAVEL=True)
    return version,frame,applicability


@pytest.mark.parametrize('hits,tier',[(0,0),(3,25),(5,50),(8,75),(9,100)])
def test_future_incentive_requires_explicit_complete_applicability(hits,tier):
    version,frame,applicability=future_fixture(hits)
    cohort=set(frame.COD_MUN)
    result=classify_state_incentive(2025,frame,applicability,cohort,[version])
    assert result['incentive']==tier
    incomplete=copy.deepcopy(version);incomplete['indicators']=incomplete['indicators'][:-1]
    assert classify_state_incentive(2025,frame,applicability,cohort,[incomplete]) is None
    assert category_summary(frame,2025,[incomplete]).empty
    assert classify_state_incentive(2025,frame,None,cohort,[version]) is None
    assert classify_state_incentive(2025,frame,applicability.iloc[:-1],cohort,[version]) is None
    assert classify_state_incentive(2025,frame.iloc[:-1],applicability,cohort,[version]) is None
    assert classify_state_incentive(2025,frame.assign(SITUACAO='Sem informação'),applicability,cohort,[version]) is None
    assert classify_state_incentive(2025,frame.assign(SERIE='outro conceito'),applicability,cohort,[version]) is None
    assert classify_state_incentive(2025,frame,applicability,cohort) is None  # Configuração distribuída é referência.


def test_critical_no_2025_backfill_of_historical_names_targets_or_categories():
    base,catalog=load_data(file_signature())
    before=catalog.copy(deep=True)
    version,frame,applicability=future_fixture()
    versions=[version_for_year(2013),version]
    for year in range(2013,2022):
        historical=base[base.ANO.eq(year)]
        assert indicator_rule(year,'concept-1','IND_01',versions) is None
        assert category_summary(historical,year,versions).empty
        assert classify_state_incentive(year,historical,applicability,set(frame.COD_MUN),versions) is None
    pd.testing.assert_frame_equal(catalog,before)
    assert not catalog.DESCRICAO.str.contains('Nome exclusivo 2025').any()
    assert indicator_rule(2025,'wrong-concept','IND_01',[version]) is None
    assert indicator_rule(2025,'concept-1','IND_01',[version])['evaluation']['direction']=='GREATER_EQUAL'
    assert not category_summary(frame,2025,[version]).empty


def test_routes_and_shared_functions_preserved():
    assert list(NAV_LABELS.values())==['Visão Geral','Estados','Mapas','Histórico','Dados','Sobre']
    assert not any(hasattr(views,name) for name in ['municipalities','indicators','comparisons'])
    assert callable(views.detail_table) and callable(views.historical) and callable(charts.trajectory)
    assert not hasattr(charts,'distribution') and not hasattr(charts,'municipal_comparison')


def test_state_ui_keeps_all_indicators_table_after_visuals_and_filters():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=60)
    app.radio(key='pagina').set_value('Estados').run(timeout=60)
    app.selectbox(key='uf').set_value('PA').run(timeout=60)
    assert {w.key for w in app.sidebar.selectbox}=={'ano','uf','ordem_estados'}
    fig=json.loads(app.get('plotly_chart')[0].proto.spec)
    assert len(fig['data'][0]['y'])==14
    app.selectbox(key='ano').set_value(2017).run(timeout=60)
    fig=json.loads(app.get('plotly_chart')[0].proto.spec)
    assert len(fig['data'][0]['y'])==15
    assert not app.error and not app.exception
    assert not any('incentivo' in h.value.lower() or 'universais' in h.value.lower() for h in app.subheader)
