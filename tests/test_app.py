from pathlib import Path
import json
import pytest
from streamlit.testing.v1 import AppTest

APP=Path(__file__).resolve().parents[1]/'app.py'


@pytest.fixture(scope='module')
def app():
    return AppTest.from_file(str(APP)).run(timeout=60)


def assert_clean(app):
    assert not app.exception, app.exception
    assert not app.error, app.error


@pytest.mark.parametrize('page', ['Visão Geral','Estados','Municípios','Indicadores','Análise Histórica','Comparações','Tabela de Dados','Sobre / Metodologia'])
def test_all_pages(app,page):
    app.radio(key='pagina').set_value(page).run(timeout=60)
    assert_clean(app)


def test_dependent_filters_and_historical_municipality(app):
    app.radio(key='pagina').set_value('Municípios').run(timeout=60)
    app.selectbox(key='uf').set_value('PA').run(timeout=60)
    app.selectbox(key='municipio').set_value('150140').run(timeout=60)
    assert_clean(app)
    assert any('Belém' in x.value for x in app.subheader)
    app.selectbox(key='uf').set_value('AC').run(timeout=60)
    assert app.selectbox(key='municipio').value == 'Todos'
    app.selectbox(key='ano').set_value(2016).run(timeout=60)
    app.selectbox(key='indicador').set_value('IND_15').run(timeout=60)
    app.selectbox(key='ano').set_value(2021).run(timeout=60)
    assert app.selectbox(key='indicador').value == 'Todos'
    app.selectbox(key='municipio').set_value('120001').run(timeout=60)
    app.radio(key='pagina').set_value('Análise Histórica').run(timeout=60)
    assert_clean(app)
    assert any(json.loads(x.proto.spec)['layout']['title']['text'] == 'Trajetória do resultado municipal' for x in app.get('plotly_chart'))
