"""Mede renderização no AppTest; não é benchmark do navegador ou da hospedagem."""
import json
from pathlib import Path
from statistics import median
import time
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
a=time.perf_counter()
app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=60)
cold=time.perf_counter()-a
report={'cold_seconds':cold,'pages':{},'mediana_segundos':{},'contexto':'Linux/Python 3.12; 3 reruns por página; AppTest. Não inclui rasterização do browser.'}
for name in ['Visão Geral','Estados','Municípios','Indicadores','Análise Histórica','Comparações','Tabela de Dados','Sobre / Metodologia','Mapas']:
    values=[]
    for _ in range(3):
        a=time.perf_counter();app.radio(key='pagina').set_value(name).run(timeout=60)
        values.append(time.perf_counter()-a)
        assert not app.error and not app.exception
    report['pages'][name]=values
    report['mediana_segundos'][name]=median(values)
app.selectbox(key='mapa_uf').set_value('PA').run(timeout=60)
values=[]
for _ in range(3):
    a=time.perf_counter();app.run(timeout=60);values.append(time.perf_counter()-a)
    assert not app.error and not app.exception
report['pages']['Mapas · PA']=values
report['mediana_segundos']['Mapas · PA']=median(values)
before=json.loads((ROOT/'docs/desempenho_antes.json').read_text())
report['comparacao_mediana_segundos']={name:{'antes':median(values),'depois':report['mediana_segundos'][name]}
    for name,values in before['pages'].items()}
(ROOT/'docs/desempenho_depois.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
