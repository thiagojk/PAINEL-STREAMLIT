from pathlib import Path
from playwright.sync_api import sync_playwright, expect
import json
import argparse
import tempfile

parser=argparse.ArgumentParser(description="Validação visual e de downloads no Chromium; inicie o painel antes.")
parser.add_argument("--url", default="http://127.0.0.1:8502/")
parser.add_argument("--chromium", default=None, help="Executável Chromium local; omitido usa o browser instalado pelo Playwright.")
args=parser.parse_args()
TEMP=Path(tempfile.mkdtemp(prefix="pqavs-ui-"))

OUT=Path(__file__).resolve().parents[1] / 'docs' / 'screenshots'
OUT.mkdir(exist_ok=True)
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
 console=[]
 page.on('pageerror',lambda e:console.append(str(e)))
 page.goto(args.url)
 page.get_by_text('RECORTE ATUAL',exact=False).wait_for(timeout=60000)
 expect(page.locator('.js-plotly-plot')).to_have_count(4, timeout=60000)
 page.wait_for_timeout(350)
 def snapshot(**kwargs):
  page.wait_for_timeout(350)
  for graph in page.get_by_test_id('stPlotlyChart').all():
   graph.locator('.js-plotly-plot').wait_for(timeout=30000)
  page.screenshot(**kwargs)
 def clean():
  expect(page.locator('[data-testid="stException"]')).to_have_count(0)
  alerts=page.locator('[data-testid="stAlert"]').all_text_contents()
  assert not any('Não foi possível concluir' in a for a in alerts),alerts
 def nav(name):
  page.get_by_test_id('stSidebar').get_by_text(name,exact=True).click()
  page.wait_for_timeout(650)
  clean()
 def select(label,value):
  box=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True)).get_by_role('combobox')
  box.fill(value)
  page.get_by_role('option',name=value,exact=True).click()
  page.wait_for_timeout(550)
  clean()
 clean()
 snapshot(path=str(OUT/'visao-geral.png'))
 results.append('Visão Geral: cards e gráficos renderizados')
 nav('Estados');snapshot(path=str(OUT/'estados.png'));results.append('Estados: ranking e tabela renderizados')
 nav('Municípios');select('UF','PA');select('Município','Belém · PA (150140)')
 expect(page.get_by_role('heading',name='Belém · PA',exact=True)).to_be_visible()
 snapshot(path=str(OUT/'municipio.png'));results.append('Municípios: filtro PA/Belém e ficha municipal')
 select('UF','AC')
 assert 'Belém' not in page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Município',exact=True)).inner_text()
 results.append('Filtro dependente: município reiniciado ao trocar UF')
 nav('Indicadores');snapshot(path=str(OUT/'indicador.png'));results.append('Indicadores: definição, metas e distribuição')
 nav('Análise Histórica');select('Município','Acrelândia · AC (120001)')
 snapshot(path=str(OUT/'historico.png'))
 page.get_by_test_id('stMain').evaluate('(el)=>el.scrollTop=1100')
 snapshot(path=str(OUT/'historico-graficos.png'))
 page.get_by_test_id('stMain').evaluate('(el)=>el.scrollTop=0')
 results.append('Histórico: trajetória municipal e linha da meta')
 nav('Comparações');snapshot(path=str(OUT/'comparacoes.png'))
 page.get_by_test_id('stRadio').filter(has=page.get_by_text('Comparar localidades',exact=True)).get_by_text('Municípios',exact=True).click();page.wait_for_timeout(500);clean()
 results.append('Comparações: modos estados e municípios')
 nav('Tabela de Dados')
 page.get_by_role('button',name='Preparar CSV do recorte',exact=True).click()
 page.get_by_role('button',name='Baixar CSV',exact=True).wait_for()
 with page.expect_download() as info:
  page.get_by_role('button',name='Baixar CSV',exact=True).click()
 download=info.value; download.save_as(str(TEMP / 'pqavs-export.csv'))
 text=Path(str(TEMP / 'pqavs-export.csv')).read_text(encoding='utf-8-sig')
 assert 'Código do município' in text and '120001' in text and '150140' not in text
 results.append('CSV: download contém somente o município filtrado')
 page.get_by_role('button',name='Preparar Excel do recorte',exact=True).click()
 page.get_by_role('button',name='Baixar XLSX',exact=True).wait_for()
 with page.expect_download() as info:
  page.get_by_role('button',name='Baixar XLSX',exact=True).click()
 info.value.save_as(str(TEMP / 'pqavs-export.xlsx'))
 import pandas as pd
 x=pd.read_excel(str(TEMP / 'pqavs-export.xlsx'),dtype={'Código do município':'string'})
 assert x['Código do município'].eq('120001').all()
 results.append('XLSX: download validado com filtro aplicado')
 nav('Sobre / Metodologia');snapshot(path=str(OUT/'metodologia.png'));results.append('Metodologia: fonte e limitações visíveis')
 nav('Visão Geral')
 page.set_viewport_size({'width':768,'height':1024});page.wait_for_timeout(500);clean()
 page.get_by_test_id('stSidebarCollapseButton').get_by_role('button').click()
 page.get_by_test_id('stMain').evaluate('(el)=>el.scrollTop=0')
 page.wait_for_timeout(300)
 snapshot(path=str(OUT/'tablet.png'));results.append('Tablet: layout 768px sem exceções')
 page.set_viewport_size({'width':390,'height':844});page.get_by_test_id('stMain').evaluate('(el)=>el.scrollTop=0');page.wait_for_timeout(500);clean()
 snapshot(path=str(OUT/'mobile.png'))
 overflow=page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
 assert not overflow
 results.append('Celular: layout 390px sem transbordamento horizontal da página')
 assert not console,console
 report={'checks':results,'browser_errors':console}
 (OUT.parent / 'validacao_navegador.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))
 browser.close()
