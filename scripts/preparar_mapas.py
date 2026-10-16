"""Prepara GeoJSON local; dependências opcionais em requirements-maps.txt.

Uso: python scripts/preparar_mapas.py [--cache /tmp/pqavs-geometrias]
O dashboard nunca executa downloads nem importa Shapely.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import pandas as pd
import requests
from shapely.geometry import shape, mapping
from shapely import make_valid, union_all, orient_polygons

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.geography import UF_CODES, geographic_code, correspondence_report

REVISION = 'e85ba38c0c7d5acda8d8878099a7f321dddefa33'
SOURCE = f'https://raw.githubusercontent.com/luizpedone/municipal-brazilian-geodata/{REVISION}'


def fetch(name, cache):
    url = f'{SOURCE}/minified/{name}.min.json'
    target = cache / f'{REVISION}-{name}.json'
    if not target.exists():
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        target.write_bytes(r.content)
    raw = target.read_bytes()
    data = json.loads(raw)
    if data.get('type') != 'FeatureCollection' or not data.get('features'):
        raise ValueError(f'GeoJSON inválido: {name}')
    return name, data, {'url': url, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def rounded(value, places):
    if isinstance(value, (list, tuple)):
        return [rounded(x, places) for x in value]
    return round(value, places)


def optimize(geometry, tolerance):
    g = shape(geometry)
    repaired = not g.is_valid
    if repaired:
        g = make_valid(g)
    if g.geom_type == 'GeometryCollection':
        # make_valid pode produzir linhas sem área; o coroplético usa só componentes poligonais.
        pending, polygons = list(g.geoms), []
        while pending:
            part = pending.pop()
            if part.geom_type == 'Polygon':
                polygons.append(part)
            elif hasattr(part, 'geoms'):
                pending.extend(part.geoms)
        g = union_all(polygons)
    g = g.simplify(tolerance, preserve_topology=True)
    if g.geom_type not in ['Polygon', 'MultiPolygon'] or g.is_empty or not g.is_valid:
        raise ValueError('Geometria vazia ou inválida após simplificação.')
    # D3/Plotly SVG usa anéis externos horários; só muda a ordem dos vértices.
    g = orient_polygons(g, exterior_cw=True)
    result = mapping(g)
    for places in [4, 6]:
        candidate = {'type': result['type'], 'coordinates': rounded(result['coordinates'], places)}
        check = shape(candidate)
        if check.is_valid and not check.is_empty:
            return candidate, repaired
    return dict(result), repaired


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')


def prepare(cache, output):
    cache.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'municipios').mkdir(exist_ok=True)
    names = ['Brasil'] + sorted(UF_CODES)
    with ThreadPoolExecutor(max_workers=4) as pool:
        downloaded = list(pool.map(lambda name: fetch(name, cache), names))
    manifest = {'fonte': 'IBGE, redistribuído por luizpedone/municipal-brazilian-geodata',
                'repositorio': 'https://github.com/luizpedone/municipal-brazilian-geodata',
                'revisao': REVISION, 'licenca_espelho': 'MIT', 'crs': 'WGS84 / longitude, latitude',
                'preparado_em_utc': datetime.now(timezone.utc).isoformat(),
                'ano_da_malha': None, 'orientacao': 'Anéis externos horários e interiores anti-horários para D3/Plotly; sem alteração dos limites.',
                'tolerancia_graus': {'municipios': .006, 'ufs': .025},
                'nota': 'Malha estática do espelho; não representa necessariamente os limites de cada ano histórico. Simplificada para visualização, sem finalidade cartográfica de precisão.',
                'originais': {}, 'arquivos': {}, 'reparos_topologicos': 0, 'codigos_reparados': []}
    for name, data, provenance in downloaded:
        manifest['originais'][name] = provenance
        features = []
        for original in data['features']:
            p = original['properties']
            geometry, repaired = optimize(original['geometry'], .025 if name == 'Brasil' else .006)
            manifest['reparos_topologicos'] += int(repaired)
            if repaired:
                manifest['codigos_reparados'].append(p.get('GEOCODIGO', p.get('UF')))
            if name == 'Brasil':
                uf = str(p['UF'])
                properties = {'UF': uf, 'COD_UF': UF_CODES[uf], 'NOME_UF': str(p['ESTADO'])}
                fid = uf
            else:
                code = str(p['GEOCODIGO'])
                key = geographic_code(code)
                if p['UF'] != name or code[:2] != UF_CODES[name]:
                    raise ValueError(f'UF incompatível: {code}')
                properties = {'UF': name, 'COD_MUN_GEO': code, 'COD_MUN': key, 'NOME_GEO': str(p['NOME'])}
                fid = key
            features.append({'type': 'Feature', 'id': fid, 'properties': properties, 'geometry': geometry})
        ids = [f['id'] for f in features]
        if len(ids) != len(set(ids)):
            raise ValueError(f'Identificadores duplicados: {name}')
        target = output / ('brasil_ufs.geojson' if name == 'Brasil' else f'municipios/{name}.geojson')
        save_json(target, {'type': 'FeatureCollection', 'features': features})
        manifest['arquivos'][str(target.relative_to(output))] = {'bytes': target.stat().st_size,
            'features': len(features), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
        print(name, len(features), target.stat().st_size, flush=True)
    # Licença do espelho é preservada na íntegra.
    license_response = requests.get(f'{SOURCE}/LICENSE', timeout=30)
    license_response.raise_for_status()
    (output / 'LICENSE-source.txt').write_text(license_response.text, encoding='utf-8')
    base = pd.read_parquet(ROOT / 'data/base_pqavs.parquet', columns=['COD_MUN','NOME_MUN','UF'])
    manifest['correspondencia'] = correspondence_report(base, output)
    manifest['geojson_total_bytes'] = sum(x['bytes'] for x in manifest['arquivos'].values())
    save_json(output / 'manifest.json', manifest)
    print(json.dumps(manifest['correspondencia'], ensure_ascii=False, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=Path(tempfile.gettempdir()) / 'pqavs-geometrias')
    parser.add_argument('--saida', type=Path, default=ROOT / 'assets/maps')
    args = parser.parse_args()
    prepare(args.cache, args.saida)
