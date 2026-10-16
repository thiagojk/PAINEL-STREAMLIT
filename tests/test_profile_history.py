from pathlib import Path
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from streamlit.testing.v1 import AppTest
from src.data import DATA, file_signature
from src.profile_history import profile_evolution, comparable_series_history, historical_exploration
from src.state_analysis import state_dashboard
from src import charts

APP=Path(__file__).resolve().parents[1]/'app.py'


@pytest.fixture
def fixture():
    records=[];catalog=[]
    for year in [2017,2018,2019]:
        number='IND_02' if year==2017 else 'IND_01'
        for code,status in [('A','Atingida'),('B','Não atingida'),('C','Sem informação')]:
            records.append({'ANO':year,'COD_MUN':code,'NOME_MUN':code,'UF':'PA','SITUACAO':status,'INDICADOR':number,'SERIE':'same-series'})
        catalog.append({'ANO':year,'INDICADOR':number,'SERIE':'same-series','DESCRICAO':f'Indicador {number[-2:]} - Proporção de registros.', 'LABEL_META':'Meta >= 80%','UNIDADE':'%'})
    return pd.DataFrame(records),pd.DataFrame(catalog)


def test_evolution_denominators_missing_and_no_recalculation(fixture):
    frame,catalog=fixture
    unknown=frame.copy();unknown.loc[unknown.ANO.eq(2019),'SITUACAO']='Sem informação'
    data,coverage=profile_evolution(unknown,catalog,[2017,2018,2019,2020])
    p=data.loc[data.ANO.eq(2017)&data.PATAMAR.eq(30)].iloc[0]
    assert (p.MUNICIPIOS,p.DENOMINADOR,p.PERCENTUAL,p.SEM_AVALIACAO)==(1,2,50,1)
    assert len(data)==16
    assert data.loc[data.ANO.isin([2019,2020]),'PERCENTUAL'].isna().all()
    assert coverage.loc[coverage.ANO.eq(2020),'MUNICIPIOS_OBSERVADOS'].iloc[0]==0
    # Mesmo alterando a regra textual, o alcance da fonte não é recalculado.
    different=catalog.copy();different.loc[different.ANO.eq(2018),'LABEL_META']='Meta >= 99%'
    changed,info=profile_evolution(unknown,different,[2017,2018,2019])
    assert changed.loc[changed.ANO.eq(2018)&changed.PATAMAR.eq(30),'PERCENTUAL'].iloc[0]==50
    assert info.loc[info.ANO.eq(2018),'CATALOGO_MUDOU'].iloc[0]
    with pytest.raises(ValueError,match='duplicadas'):
        profile_evolution(pd.concat([frame,frame.iloc[:1]]),catalog,[2017])


def test_renumbering_is_not_a_catalog_break_but_cohort_changes_are(fixture):
    frame,catalog=fixture
    _,coverage=profile_evolution(frame,catalog,[2017,2018,2019])
    assert not coverage.CATALOGO_MUDOU.any()
    extra=frame.loc[frame.ANO.eq(2019)].iloc[:1].assign(COD_MUN='D',NOME_MUN='D')
    data,coverage=profile_evolution(pd.concat([frame,extra]),catalog,[2017,2018,2019])
    assert coverage.COORTE_MUDOU.tolist()==[False,False,True]
    fig=charts.profile_evolution(data)
    assert len(fig.data)==4 and all(None in list(trace.x) for trace in fig.data)
    assert all(trace.connectgaps is False for trace in fig.data)
    assert list(fig.layout.yaxis.range)==[0,105]


def test_matrix_preserves_strict_series_not_number_or_annual_original(fixture):
    frame,catalog=fixture
    extra_frame=[];extra_catalog=[]
    for year in [2017,2018,2019]:
        extra_frame.append(frame.loc[frame.ANO.eq(year)].assign(INDICADOR='IND_99',SERIE=f'original-{year}'))
        extra_catalog.append({'ANO':year,'INDICADOR':'IND_99','SERIE':f'original-{year}',
                              'DESCRICAO':'Indicador 99 - Número de ciclos.','LABEL_META':'Meta 4 ciclos','UNIDADE':'Original'})
    matrix,excluded=comparable_series_history(pd.concat([frame,*extra_frame]),pd.concat([catalog,pd.DataFrame(extra_catalog)]),[2017,2018,2019])
    assert set(matrix.SERIE)=={'same-series'} and len(matrix)==3 and excluded==3
    assert matrix.INDICADOR.tolist()==['IND_02','IND_01','IND_01']
    assert '01/02' in matrix.ROTULO.iloc[0]
    changed=frame.copy();changed.loc[changed.ANO.eq(2019),'SERIE']='different-concept'
    definitions=catalog.copy();definitions.loc[definitions.ANO.eq(2019),'SERIE']='different-concept'
    assert comparable_series_history(changed,definitions,[2017,2018,2019])[0].empty
    assert comparable_series_history(frame,catalog,[2017,2018])[0].empty
    # Não avalia apenas as pontas: o valor intermediário permanece na matriz.
    frame.loc[frame.ANO.eq(2018)&frame.COD_MUN.eq('B'),'SITUACAO']='Atingida'
    matrix,_=comparable_series_history(frame,catalog,[2017,2018,2019])
    assert matrix.CUMPRIMENTO.tolist()==[50,100,50]
    fig=charts.temporal_heatmap(matrix,[2017,2018,2019])
    assert fig.data[0].zmin==0 and fig.data[0].zmax==100
    np.testing.assert_allclose(fig.data[0].z,[[50,100,50]])


@pytest.mark.parametrize('uf',['Todos','PA','AC'])
def test_cached_evolution_matches_existing_annual_thresholds(uf):
    data,coverage,matrix,_=historical_exploration(file_signature(),uf,(2013,2021))
    assert len(data)==36 and len(coverage)==9
    for year in [2013,2017,2021]:
        _,profiles,distribution,thresholds=state_dashboard(file_signature(),year,uf)
        for threshold,expected in thresholds.items():
            row=data.loc[data.ANO.eq(year)&data.PATAMAR.eq(threshold)].iloc[0]
            assert row.PERCENTUAL==pytest.approx(expected['percent'])
            assert row.MUNICIPIOS==expected['municipalities']
            assert row.DENOMINADOR==expected['denominator']
    assert set(matrix.SERIE).issubset(set(pd.read_parquet(DATA/'indicadores.parquet').SERIE))
    assert matrix.groupby('SERIE',observed=True).ANO.nunique().ge(3).all()


def test_overview_helpers_align_only_the_requested_row():
    a=go.Figure(go.Bar(x=[1,2],y=[3,4]));a.update_layout(height=320)
    b=go.Figure(go.Bar(x=[1,2],y=[3,4]));b.update_layout(height=430)
    untouched=go.Figure().update_layout(height=590)
    values=[a.data[0].to_plotly_json(),b.data[0].to_plotly_json()]
    charts.align_row_figures(a,b)
    assert a.layout.height==b.layout.height==430 and untouched.layout.height==590
    assert [a.data[0].to_plotly_json(),b.data[0].to_plotly_json()]==values
    assert charts.ranking_height(15)>charts.CHART_HEIGHT_STANDARD


def test_ui_cards_once_above_chart_and_history_opt_in():
    app=AppTest.from_file(str(APP)).run(timeout=60)
    app.radio(key='pagina').set_value('Estados').run(timeout=60)
    html=[x.proto.body for x in app.get('html')]
    assert sum(text.count('Municípios com ≥30%') for text in html)==1
    assert any('Resumo do recorte' in text and 'Perfil de alcance' in text and 'title=' in text for text in html)
    app.radio(key='pagina').set_value('Análise Histórica').run(timeout=60)
    initial=len(app.get('plotly_chart'))
    app.toggle(key='hist_explorar').set_value(True).run(timeout=60)
    assert len(app.get('plotly_chart'))==initial+2
    assert app.select_slider(key='hist_perfil_periodo').value==(2013,2021)
    assert any('incentivo oficial' in warning.value for warning in app.warning)
    app.selectbox(key='uf').set_value('PA').run(timeout=60)
    app.selectbox(key='municipio').set_value('150140').run(timeout=60)
    assert any('coletivas' in info.value for info in app.info)
    assert not app.error and not app.exception
    app.sidebar.button(key='limpar_filtros').click().run(timeout=60)
    assert not app.toggle(key='hist_explorar').value
