"""Auditoria reproduzível de disponibilidade, casos reais e hashes protegidos."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.data import DATA, filter_data
from src.geography import load_geojson, map_signature, municipality_layer
from src.target_progress import progress_layer, progress_signature
from src.rules import version_for_year

ROOT=Path(__file__).resolve().parents[1]
b=pd.read_parquet(DATA/'base_pqavs.parquet');c=pd.read_parquet(DATA/'indicadores.parquet')
rules=version_for_year(2021)['progress_rules']
lines=['# Disponibilidade do grau de alcance por indicador e período','',
'Fonte: catálogo anual de Base_Painel.xlsx, preservado em `data/indicadores.parquet`. Registro complementar em `indicator_rules/historical.json`; não ativa incentivo ou avaliador oficial. Cada linha tem correspondência exata de ano, número, série, descrição, unidade e meta.','',
'92 de 128 combinações indicador/ano suportam a razão de proximidade; 36 não suportam. A disponibilidade do indicador não garante a do registro: resultado e NUM/DEN também precisam ser válidos.','',
'| Indicador | Ano | Tipo/meta da fonte | Fórmula | Disponível | Justificativa |','|---|---|---|---|---|---|']
for r in sorted(rules,key=lambda r:(r['year'],r['number'])):
    lines.append(f"| {r['number']} | {r['year']} | {r['target_label']} | "+('100 × resultado (%) / '+str(r['target']) if r['supports_progress_map'] else '—')+f" | {'Sim' if r['supports_progress_map'] else 'Não'} | {r['justification']} |")
(ROOT/'docs/GRAU_ALCANCE_INDICADORES.md').write_text('\n'.join(lines)+'\n')
report={'casos':[],'cobertura':[],'desempenho':[],'integridade':[]}
# Conta manual independente: frações NUM/DEN e limites literais do catálogo,
# sem usar a função calculate_target_progress para produzir o esperado.
for indicator,target in [('IND_01',90),('IND_02',90),('IND_04',100),('IND_07',70)]:
    raw=b[(b.ANO==2021)&(b.COD_MUN=='150140')&(b.INDICADOR==indicator)].iloc[0]
    expected=100*(100*raw.NUM/raw.DEN)/target
    entry=c[(c.ANO==2021)&(c.INDICADOR==indicator)].iloc[0]
    layer=municipality_layer(filter_data(b,year=2021,uf='PA',indicator=indicator),load_geojson(map_signature('PA')))
    derived=progress_layer(layer,entry,progress_signature())
    actual=derived[derived.COD_MUN.eq('150140')].iloc[0]
    assert abs(actual.GRAU_REAL-expected)<1e-8
    assert abs(actual.GRAU_VISUAL-min(100,expected))<1e-8
    report['casos'].append({'municipio':'Belém','codigo':'150140','ano':2021,'indicador':indicator,'NUM':raw.NUM,'DEN':raw.DEN,'resultado_percentual':100*raw.NUM/raw.DEN,'meta':target,'grau_manual':expected,'grau_dashboard':actual.GRAU_REAL,'grau_visual':actual.GRAU_VISUAL,'situacao_fonte':str(raw.SITUACAO)})
for uf in ['PA','AC']:
    geometry=load_geojson(map_signature(uf))
    for row in c[c.ANO.eq(2021)].itertuples():
        entry=c[(c.ANO==row.ANO)&(c.INDICADOR==row.INDICADOR)].iloc[0]
        layer=municipality_layer(filter_data(b,year=row.ANO,uf=uf,indicator=row.INDICADOR),geometry)
        start=time.perf_counter();out=progress_layer(layer,entry,progress_signature());cold=time.perf_counter()-start
        start=time.perf_counter();progress_layer(layer,entry,progress_signature());warm=time.perf_counter()-start
        report['cobertura'].append({'uf':uf,'indicador':row.INDICADOR,'calculaveis':int(out.GRAU_VALIDO.sum()),'indisponiveis':int((~out.GRAU_VALIDO).sum())})
        report['desempenho'].append({'uf':uf,'indicador':row.INDICADOR,'preparo_segundos':cold,'cache_segundos':warm})
# Verifica identidade com o commit da rodada anterior, sem depender de hashes
# calculados depois das alterações. Cadastro de proximidade é mudança autorizada.
paths=[*sorted((ROOT/'data').glob('*')),*sorted((ROOT/'assets/maps').rglob('*.geojson')),*[ROOT/p for p in ['src/data.py','src/metrics.py','src/state_analysis.py','src/rules.py','src/profile_history.py','src/territorial_history.py','indicator_rules/2025.json','requirements.txt','app.py']]]
for path in paths:
    if not path.is_file():continue
    relative=str(path.relative_to(ROOT))
    previous=subprocess.check_output(['git','show',f'fa80798:{relative}'],cwd=ROOT)
    assert previous==path.read_bytes(),relative
    report['integridade'].append({'arquivo':relative,'sha256':hashlib.sha256(previous).hexdigest(),'identico_fa80798':True})
(ROOT/'docs/auditoria_grau_alcance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'casos':report['casos'],'arquivos_protegidos':len(report['integridade'])},ensure_ascii=False,indent=2))
