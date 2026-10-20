"""Um único controle real coordena cores, escala, filtros e caches."""
import json
from pathlib import Path
import pandas as pd
from streamlit.testing.v1 import AppTest
from src import geography, theme
from src.data import load_data


def test_sidebar_mode_synchronizes_current_history_and_reuses_sources(monkeypatch):
    reads={'parquet':0,'geometry':0}
    original_parquet=pd.read_parquet
    original_geometry=geography._read_geojson
    def parquet(*args,**kwargs):
        reads['parquet']+=1
        return original_parquet(*args,**kwargs)
    def geometry(*args,**kwargs):
        reads['geometry']+=1
        return original_geometry(*args,**kwargs)
    load_data.clear();geography.load_geojson.clear()
    monkeypatch.setattr(pd,'read_parquet',parquet)
    monkeypatch.setattr(geography,'_read_geojson',geometry)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=60)
    app.radio(key='pagina').set_value('Mapas').run(timeout=60)
    app.selectbox(key='mapa_uf').set_value('PA').run(timeout=60)
    app.selectbox(key='mapa_indicador').set_value('IND_13').run(timeout=60)
    app.toggle(key='mapa_historico').set_value(True).run(timeout=60)
    years=[2013,2015,2017,2019,2021]
    app.sidebar.multiselect[0].set_value(years).run(timeout=60)
    assert len(app.sidebar.radio)==1 and app.sidebar.radio[0].key=='map_mode'
    assert sum(x.key=='map_mode' for x in app.radio)==1
    assert reads['parquet']>=2 and reads['geometry']>=1
    baseline=reads.copy()
    for mode in ['Situação da meta','Grau de alcance (%)','Situação da meta','Grau de alcance (%)']:
        app.sidebar.radio(key='map_mode').set_value(mode).run(timeout=60)
        assert not app.error and not app.exception
        assert app.selectbox(key='mapa_ano').value==2021
        assert app.selectbox(key='mapa_uf').value=='PA'
        assert app.selectbox(key='mapa_indicador').value=='IND_13'
        assert app.sidebar.multiselect[0].value==years
        figures=[json.loads(x.proto.spec) for x in app.get('plotly_chart')]
        maps=[f for f in figures if f['data'] and f['data'][0]['type']=='choropleth']
        assert len(maps)==5  # comparação substitui o principal; sem ranking
        for index,figure in enumerate(maps):
            for trace in figure['data']:
                scale=trace['colorscale']
                if mode=='Situação da meta':
                    assert scale==[[0,theme.MAP_STATUS_COLORS[trace['name']]],[1,theme.MAP_STATUS_COLORS[trace['name']]]]
                    assert trace['showscale'] is False
                else:
                    assert trace['zmin']==0 and trace['zmax']==100
                    assert scale==theme.MAP_PROGRESS_SCALE or scale==[[0,theme.MAP_STATUS_MISSING],[1,theme.MAP_STATUS_MISSING]]
                    assert trace['showscale'] is False
        app.toggle(key='mapa_historico').set_value(False).run(timeout=60)
        assert len(app.get('plotly_chart'))==2
        current=json.loads(app.get('plotly_chart')[0].proto.spec)['data']
        if mode=='Grau de alcance (%)':
            assert current[0]['colorscale']==theme.MAP_PROGRESS_SCALE
            assert current[0]['zmin']==0 and current[0]['zmax']==100
        else:
            assert all(t['colorscale']==[[0,theme.MAP_STATUS_COLORS[t['name']]],[1,theme.MAP_STATUS_COLORS[t['name']]]] for t in current)
        app.toggle(key='mapa_historico').set_value(True).run(timeout=60)
        assert app.sidebar.multiselect[0].value==years
        assert reads==baseline  # a troca não relê Parquet nem GeoJSON
    assert theme.MAP_STATUS_REACHED!=theme.MAP_STATUS_NOT_REACHED
    assert theme.MAP_STATUS_MISSING!=theme.MAP_PROGRESS_SCALE[0][1]
