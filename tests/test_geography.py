import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from src.data import DATA, STATUS, filter_data
from src.geography import (UF_CODES, MAPS, geographic_code, geographic_index,
    correspondence_report, map_signature, load_geojson, map_metadata, state_summary, municipality_layer)
from src.metrics import summarize
from src import charts
from src.navigation import NAV_LABELS


@pytest.fixture(scope='module')
def base():
    return pd.read_parquet(DATA / 'base_pqavs.parquet')


def test_navigation_nine_areas_no_sidebar():
    assert len(NAV_LABELS) == 9 and 'Mapas' in NAV_LABELS
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=60)
    assert len(app.radio(key='pagina').options) == 9
    assert app.radio(key='pagina').proto.horizontal
    assert not app.sidebar.radio and not app.sidebar.selectbox
    assert not app.error and not app.exception


def test_geojson_load_and_uf_ids():
    geo = load_geojson(map_signature())
    assert geo['type'] == 'FeatureCollection'
    assert {f['id'] for f in geo['features']} == set(UF_CODES)
    assert len(set(UF_CODES.values())) == 27
    for f in geo['features']:
        assert f['properties']['COD_UF'] == UF_CODES[f['properties']['UF']]
        assert f['geometry']['type'] in ['Polygon','MultiPolygon']
    with pytest.raises(ValueError):
        map_signature('../../x')


def test_all_files_integrity_and_small_size():
    metadata = map_metadata()
    assert len(metadata['arquivos']) == 28
    for name, record in metadata['arquivos'].items():
        p = MAPS / name
        assert p.stat().st_size == record['bytes']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == record['sha256']
        data = json.loads(p.read_text())
        assert len(data['features']) == record['features']
        for f in data['features']:
            coords = f['geometry']['coordinates']
            polys = [coords] if f['geometry']['type'] == 'Polygon' else coords
            for poly in polys:
                for index,ring in enumerate(poly):
                    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]))
                    assert area < 0 if index == 0 else area > 0
                    assert len(ring) >= 4 and ring[0] == ring[-1]
                    assert all(-180 <= xy[0] <= 180 and -90 <= xy[1] <= 90 for xy in ring)
    assert metadata['geojson_total_bytes'] < 8 * 1024**2


def test_seven_to_six_digits_without_invention():
    assert geographic_code('1501402') == '150140'
    assert geographic_code('1200013') == '120001'
    for invalid in ['150140', 1501402, '01501402', 'PA15014']:
        with pytest.raises(ValueError):
            geographic_code(invalid)
    idx = geographic_index()
    assert len(idx) == 5570 and not idx.COD_MUN.duplicated().any()
    assert idx[idx.COD_MUN.eq('150140')].UF.iloc[0] == 'PA'
    assert len(idx[idx.UF.eq('PA')]) == 144


def test_full_match_and_report(base):
    report = correspondence_report(base)
    assert report == map_metadata()['correspondencia']
    assert report['associados'] == report['municipios_base'] == 5570
    assert report['taxa_percentual'] == 100
    assert not report['municipios_nao_associados']


def test_state_aggregation_uses_existing_denominator(base):
    frame = filter_data(base, year=2021, indicator='IND_01')
    actual = state_summary(frame)
    expected = summarize(frame, ['UF'])
    pd.testing.assert_frame_equal(actual, expected)
    pa = actual[actual.UF.eq('PA')].iloc[0]
    assert pa.AVALIADOS == 144
    fixture = frame[frame.UF.eq('AC')].head(3).copy()
    fixture['SITUACAO'] = ['Atingida','Não atingida','Sem informação']
    r = state_summary(fixture).iloc[0]
    assert r.AVALIADOS == 2 and r.SEM_INFORMACAO == 1 and r.CUMPRIMENTO == 50
    with pytest.raises(ValueError):
        state_summary(filter_data(base, year=2021))


def test_municipal_layer_observations_unknown_and_absent(base):
    geo = load_geojson(map_signature('PA'))
    frame = filter_data(base, year=2021, uf='PA', indicator='IND_01')
    layer = municipality_layer(frame, geo)
    assert len(layer) == 144 and layer.TEM_OBSERVACAO.all()
    assert layer[layer.COD_MUN.eq('150140')].NOME_EXIBICAO.iloc[0] == 'Belém'
    changed = frame[~frame.COD_MUN.eq('150140')].copy()
    first = changed.index[0]
    changed['SITUACAO'] = changed.SITUACAO.astype('string')
    changed.loc[first, 'SITUACAO'] = 'Sem informação'
    layer = municipality_layer(changed, geo)
    absent = layer[layer.COD_MUN.eq('150140')].iloc[0]
    assert not absent.TEM_OBSERVACAO and absent.SITUACAO_MAPA == 'Sem informação'
    assert layer.SITUACAO_MAPA.eq('Sem informação').sum() == 2
    # Nenhuma imputação nos registros da análise.
    assert len(changed) == 143
    assert state_summary(changed).AVALIADOS.iloc[0] == 142
    assert len(municipality_layer(frame.iloc[:0],geo)) == 144


def test_real_missing_territories_not_added_to_totals(base):
    geo = load_geojson(map_signature('PI'))
    frame = filter_data(base, year=2021, uf='PI', indicator='IND_01')
    layer = municipality_layer(frame, geo)
    assert (~layer.TEM_OBSERVACAO).sum() == 7
    assert len(frame) == 217
    assert len(layer) == 224
    assert state_summary(frame).MUNICIPIOS.iloc[0] == 217


def test_empty_maps_and_no_runtime_tiles(base):
    frame = filter_data(base, year=2021, indicator='IND_01').iloc[:0]
    fig = charts.state_map(state_summary(frame),load_geojson(map_signature()),2021,'Indicador')
    assert fig.layout.geo.visible is False
    assert fig.layout.geo.fitbounds == 'locations'
    assert state_summary(frame).empty


def test_map_labels_tooltips_and_brazilian_chart_labels(base):
    frame = filter_data(base, year=2021, uf='PA', indicator='IND_01')
    summary = state_summary(frame)
    fig = charts.state_map(summary,load_geojson(map_signature()),2021,'Descrição do indicador')
    assert 'Municípios avaliados' in fig.data[0].hovertemplate
    assert 'Descrição do indicador' in fig.data[0].customdata[0]
    bar = charts.ranking(summary,'UF','Ranking')
    assert all(',' in label and label.endswith('%') for label in bar.data[0].text)
    hist = summarize(frame.assign(ANO=2021),['ANO'])
    line = charts.time_line(hist)
    assert '%' in line.data[0].text[0]
    donut = charts.donut(frame)
    assert any('%' in t for t in donut.data[0].text)


def test_map_page_filters_and_absent_indicator_reset():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=60)
    app.radio(key='pagina').set_value('Mapas').run(timeout=60)
    assert not app.error and not app.exception
    app.selectbox(key='mapa_uf').set_value('PA').run(timeout=60)
    app.selectbox(key='mapa_ano').set_value(2016).run(timeout=60)
    app.selectbox(key='mapa_indicador').set_value('IND_15').run(timeout=60)
    app.selectbox(key='mapa_ano').set_value(2021).run(timeout=60)
    assert app.selectbox(key='mapa_indicador').value == 'IND_01'
    assert app.selectbox(key='mapa_uf').value == 'PA'
    assert not app.error and not app.exception
    fig = json.loads(app.get('plotly_chart')[0].proto.spec)
    assert fig['data'][0]['type'] == 'choropleth'
    app.selectbox(key='mapa_uf').set_value('PI').run(timeout=60)
    assert any('7 territórios' in x.value for x in app.caption)


def test_local_topology_and_static_serving():
    import tomllib
    root=Path(__file__).resolve().parents[1]
    cfg=tomllib.loads((root/'.streamlit/config.toml').read_text())
    assert cfg['server']['enableStaticServing'] is True
    data=json.loads((root/'static/maps/un/world_110m.json').read_text())
    assert data['type']=='Topology' and 'land' in data['objects']
    source=json.loads((root/'static/maps/source.json').read_text())
    assert hashlib.sha256((root/'static/maps/un/world_110m.json').read_bytes()).hexdigest()==source['sha256']
