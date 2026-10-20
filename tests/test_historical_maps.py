import json
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from src.data import DATA, file_signature, filter_data, series_key
from src.historical import concept_options, compatible_years, representative_years, validate_map_years
from src.geography import load_geojson, map_signature, state_summary
from src.territorial_history import prepare_history
from src import charts

APP = Path(__file__).resolve().parents[1] / 'app.py'


@pytest.fixture(scope='module')
def catalog():
    return pd.read_parquet(DATA / 'indicadores.parquet')


def test_concept_identity_and_annual_scale_guards(catalog):
    options = concept_options(catalog)
    assert options.CONCEITO.is_unique and options.LABEL.is_unique
    cycles = options[options.DESCRICAO.str.contains('Número de ciclos')]
    assert len(cycles) == 1
    assert cycles.iloc[0].ANOS == list(range(2014,2022))
    assert len(cycles.iloc[0].SERIES) == 8  # Apresentação agrupada; análise anual intacta.
    occupation = options[options.DESCRICAO.str.contains('ocupação')].iloc[0]
    assert len(occupation.SERIES) == 1 and occupation.ANOS == list(range(2013,2022))
    assert '13/14' in occupation.LABEL
    # Definições distintas de vacinação continuam separadas, mesmo número.
    assert len(options[options.INDICADOR.eq('IND_03')]) == 3
    assert series_key('Indicador 8 - Mesmo conceito', 'IND_08','%') == series_key('Indicador 9 - Mesmo conceito','IND_09','%')
    assert series_key('Conceito diferente','IND_08','%') != series_key('Mesmo conceito','IND_08','%')


@pytest.mark.parametrize('page', ['Análise Histórica'])
def test_clean_concept_selector_and_correct_selection(page, catalog):
    app = AppTest.from_file(str(APP)).run(timeout=60)
    app.radio(key='pagina').set_value(page).run(timeout=60)
    choices = app.selectbox(key='conceito').options
    assert len(choices) == len(set(choices)) == len(concept_options(catalog))
    occupation = concept_options(catalog).loc[lambda x:x.DESCRICAO.str.contains('ocupação')].iloc[0]
    app.selectbox(key='conceito').set_value(occupation.CONCEITO).run(timeout=60)
    assert app.selectbox(key='serie').value == occupation.SERIES[0]
    assert not app.error and not app.exception
    cycles = concept_options(catalog).loc[lambda x:x.DESCRICAO.str.contains('Número de ciclos')].iloc[0]
    app.selectbox(key='conceito').set_value(cycles.CONCEITO).run(timeout=60)
    assert app.selectbox(key='serie').options == list(map(str,range(2014,2022)))
    app.selectbox(key='serie').set_value(cycles.SERIES[0]).run(timeout=60)
    assert app.selectbox(key='serie').value.endswith('-2014')
    assert not app.error and not app.exception


def test_representative_years_limit_and_compatibility(catalog):
    assert representative_years(list(range(2013,2022))) == [2013,2015,2017,2019,2021]
    assert representative_years([2014]) == [2014]
    assert validate_map_years([2021,2015],[2014,2015,2021]) == [2015,2021]
    with pytest.raises(ValueError,match='até 6'):
        validate_map_years(list(range(2013,2020)),list(range(2013,2022)))
    with pytest.raises(ValueError,match='incompatíveis'):
        validate_map_years([2013],[2014,2015])
    annual = catalog.loc[catalog.INDICADOR.eq('IND_08') & catalog.ANO.eq(2021)].iloc[0]
    assert compatible_years(catalog,annual.SERIE) == [2021]


@pytest.mark.parametrize('uf',['Todos','PA','AC'])
def test_historical_maps_data_territory_tooltips_and_colors(catalog,uf):
    series = catalog.loc[catalog.ANO.eq(2021) & catalog.INDICADOR.eq('IND_14'),'SERIE'].iloc[0]
    sig=map_signature(None if uf=='Todos' else uf)
    geometry=load_geojson(sig)
    items=prepare_history(file_signature(),series,uf,(2016,2021),sig)
    assert len(items)==2
    base=pd.read_parquet(DATA/'base_pqavs.parquet')
    for item in items:
        year=item['year'];row=item['entry']
        assert row.INDICADOR == ('IND_15' if year==2016 else 'IND_14')
        expected=filter_data(base,series=series,uf=uf,year=year)
        assert not item['empty']
        if uf=='Todos':
            pd.testing.assert_frame_equal(item['data'],state_summary(expected))
            fig=charts.state_map(item['data'],geometry,year,row.DESCRICAO)
            assert fig.data[0].zmin==0 and fig.data[0].zmax==100
            assert 'Ano:' in fig.data[0].hovertemplate
            assert 'Municípios avaliados' in fig.data[0].hovertemplate
        else:
            assert set(item['data'].UF)=={uf}
            assert item['data'].COD_MUN.is_unique
            fig=charts.municipality_map(item['data'],geometry,year,row.DESCRICAO,row.LABEL_META)
            for trace in fig.data:
                assert trace.colorscale[0][1] == charts.COLORS[trace.name]
                assert 'Meta:' in trace.hovertemplate and 'Situação:' in trace.hovertemplate
            assert all(str(year) in r for t in fig.data for r in t.customdata)
    assert items[0]['entry'].SERIE == items[1]['entry'].SERIE


def test_empty_historical_combination_has_no_imputation(catalog,monkeypatch):
    import src.territorial_history as module
    base=pd.read_parquet(DATA/'base_pqavs.parquet')
    series=catalog.iloc[0].SERIE
    monkeypatch.setattr(module,'historical_slice', lambda *args:(base.iloc[:0],catalog[catalog.SERIE.eq(series)]))
    module.prepare_history.clear()
    result=module.prepare_history(('empty-fixture',),series,'Todos',(2013,),map_signature())
    assert result[0]['empty'] and result[0]['data'] is None
    module.prepare_history.clear()


def test_map_history_controls_lazy_render_and_reset():
    app=AppTest.from_file(str(APP)).run(timeout=60)
    app.radio(key='pagina').set_value('Mapas').run(timeout=60)
    assert len(app.get('plotly_chart'))==2
    app.toggle(key='mapa_historico').set_value(True).run(timeout=60)
    years=app.sidebar.multiselect[0]
    assert years.value==[2014,2016,2018,2019,2021]
    assert years.proto.max_selections==6
    assert len(app.get('plotly_chart'))==5
    years.set_value([]).run(timeout=60)
    assert len(app.get('plotly_chart'))==0
    assert any('Selecione até 6 anos' in x.value for x in app.info)
    app.sidebar.button(key='limpar_filtros').click().run(timeout=60)
    assert not app.toggle(key='mapa_historico').value
    assert app.radio(key='pagina').value=='Mapas'
    assert not app.error and not app.exception


def test_annual_labels_use_actual_number_without_changing_raw(catalog):
    from src.utils import description_label
    row=catalog.loc[catalog.ANO.eq(2021) & catalog.INDICADOR.eq('IND_14')].iloc[0]
    original = row.DESCRICAO
    assert description_label(row).startswith('Indicador 14 —')
    old = catalog.loc[catalog.ANO.eq(2016) & catalog.INDICADOR.eq('IND_15')].iloc[0]
    assert description_label(old).startswith('Indicador 15 —')
    assert old.SERIE == row.SERIE
    assert row.DESCRICAO == original


def test_map_years_reset_for_incompatible_definition(catalog):
    app=AppTest.from_file(str(APP)).run(timeout=60)
    app.radio(key='pagina').set_value('Mapas').run(timeout=60)
    app.toggle(key='mapa_historico').set_value(True).run(timeout=60)
    app.selectbox(key='mapa_indicador').set_value('IND_08').run(timeout=60)
    assert app.sidebar.multiselect[0].value==[2021]
    assert len(app.get('plotly_chart'))==1
    assert any('Somente este ano' in x.value for x in app.caption)
    series=catalog.loc[catalog.ANO.eq(2021) & catalog.INDICADOR.eq('IND_08'),'SERIE'].iloc[0]
    with pytest.raises(ValueError,match='incompatíveis'):
        prepare_history(file_signature(),series,'Todos',(2016,),map_signature())
    app.selectbox(key='mapa_indicador').set_value('IND_14').run(timeout=60)
    assert app.sidebar.multiselect[0].value==[2016,2017,2018,2020,2021]
    assert not app.error and not app.exception


def test_gray_state_tooltip_keeps_year_and_definition():
    base=pd.read_parquet(DATA/'base_pqavs.parquet')
    fig=charts.state_map(state_summary(base.iloc[:0]),load_geojson(map_signature()),2017,'Definição histórica')
    gray=fig.data[-1]
    assert len(gray.locations)==27
    assert all(row[1]=='2017' and row[2]=='Definição histórica' for row in gray.customdata)
    assert all(field in gray.hovertemplate for field in ['Ano:','Indicador:','Municípios avaliados:','Atingiram:','Não atingiram:','Sem informação:','Cumprimento:'])
