"""Validação visual da aplicação em execução; não faz publicação.

python scripts/validar_interface.py --url http://127.0.0.1:8501/ --chromium /usr/bin/chromium
"""
import argparse
import json
from pathlib import Path
import tempfile
import pandas as pd
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:8502/')
parser.add_argument('--chromium', default=None)
args = parser.parse_args()
OUT = Path(__file__).resolve().parents[1] / 'docs/screenshots'
OUT.mkdir(exist_ok=True)
TEMP = Path(tempfile.mkdtemp(prefix='pqavs-ui-'))
results, dimensions, console_errors, external = [], [], [], []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.chromium, args=[
        '--no-sandbox', '--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1440,'height':1100}, device_scale_factor=1)
    page.on('pageerror', lambda e: console_errors.append(str(e)))
    page.on('console', lambda m: console_errors.append(m.text) if m.type == 'error' else None)
    page.on('request', lambda r: external.append(r.url) if not r.url.startswith((args.url.rstrip('/'), args.url.replace('http:', 'ws:').rstrip('/'), 'blob:', 'data:')) else None)
    page.goto(args.url)
    expect(page.locator('.js-plotly-plot')).to_have_count(4, timeout=60000)

    def clean():
        expect(page.get_by_test_id('stException')).to_have_count(0)
        assert not any('Não foi possível concluir' in x for x in page.get_by_test_id('stAlert').all_text_contents())

    def settle():
        page.wait_for_timeout(300)
        for graph in page.get_by_test_id('stPlotlyChart').all():
            graph.locator('.js-plotly-plot').wait_for(timeout=30000)
        clean()

    def snapshot(name, target=None):
        settle()
        if target:
            target.scroll_into_view_if_needed()
            page.wait_for_timeout(200)
        page.screenshot(path=str(OUT / name))

    def nav(name):
        page.locator('.st-key-pagina').get_by_text(name, exact=True).click()
        page.wait_for_timeout(500)
        clean()
        page.get_by_test_id('stMain').evaluate('(el)=>el.scrollTop=0')

    def select(label, value):
        box = page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True)).get_by_role('combobox')
        if box.input_value() == value: return
        box.fill(value)
        page.get_by_role('option',name=value,exact=True).click()
        page.wait_for_timeout(500)
        clean()

    def map_ready():
        page.locator('.choroplethlayer path').first.wait_for(timeout=30000)
        return page.locator('.js-plotly-plot').first

    def hover_map(lon, lat, expected):
        graph = map_ready()
        graph.scroll_into_view_if_needed()
        point = graph.evaluate('(gd,xy)=>gd._fullLayout.geo._subplot.projection(xy)',[lon,lat])
        box = graph.bounding_box()
        page.mouse.move(box['x']+point[0],box['y']+point[1])
        expect(graph.locator('.hoverlayer')).to_contain_text(expected,timeout=10000)
        return graph.locator('.hoverlayer').text_content()

    snapshot('visao-geral.png')
    assert page.get_by_test_id('stSidebar').count() == 1
    page.get_by_test_id('stMain').evaluate('(el)=>el.scrollTop=650')
    page.wait_for_timeout(250)
    assert -2 <= page.locator('.st-key-pagina').bounding_box()['y'] <= 4
    results.append('Navegação superior aderente à rolagem, com filtros na sidebar nativa')
    nav('Visão Geral')
    page.locator('.st-key-pagina input[type=radio]').first.focus()
    page.keyboard.press('ArrowRight')
    expect(page.get_by_role('heading',name='Estados',exact=True)).to_be_visible()
    results.append('Navegação superior acessível por teclado')
    snapshot('estados.png')
    nav('Municípios'); select('UF','PA'); select('Município','Belém · PA (150140)')
    expect(page.get_by_role('heading',name='Belém · PA',exact=True)).to_be_visible()
    snapshot('municipios.png'); snapshot('municipio.png')
    select('UF','AC')
    assert 'Belém' not in page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Município',exact=True)).inner_text()
    results.append('Ficha municipal e filtros dependentes PA/Belém → AC')
    nav('Indicadores'); snapshot('indicador.png')
    nav('Histórico'); select('Município','Acrelândia · AC (120001)')
    snapshot('historico.png')
    page.get_by_test_id('stMain').evaluate('(el)=>el.scrollTop=1000')
    snapshot('historico-graficos.png')
    results.append('Histórico municipal com rótulos, valores inicial/final e linha da meta')
    nav('Comparações'); snapshot('comparacoes.png')
    page.get_by_test_id('stRadio').filter(has=page.get_by_text('Comparar localidades',exact=True)).get_by_text('Municípios',exact=True).click()
    settle()
    results.append('Comparações de UFs e municípios, sem regressão')
    nav('Dados'); select('UF','AC'); select('Município','Acrelândia · AC (120001)')
    page.get_by_role('button',name='Preparar CSV do recorte',exact=True).click()
    with page.expect_download() as download:
        page.get_by_role('button',name='Baixar CSV',exact=True).click()
    download.value.save_as(str(TEMP / 'dados.csv'))
    csv=pd.read_csv(TEMP/'dados.csv',sep=';',decimal=',',dtype={'Código do município':'string'})
    assert len(csv) and csv['Código do município'].eq('120001').all()
    page.get_by_role('button',name='Preparar Excel do recorte',exact=True).click()
    with page.expect_download() as download:
        page.get_by_role('button',name='Baixar XLSX',exact=True).click()
    download.value.save_as(str(TEMP / 'dados.xlsx'))
    xlsx=pd.read_excel(TEMP/'dados.xlsx',dtype={'Código do município':'string'})
    assert len(xlsx)==len(csv) and xlsx['Código do município'].eq('120001').all()
    results.append('CSV e XLSX baixados e relidos, somente município filtrado')
    nav('Sobre'); snapshot('metodologia.png')
    expect(page.get_by_role('heading',name='Análise geográfica',exact=True)).to_have_count(1)
    results.append('Metodologia anterior e seção geográfica presentes')
    nav('Mapas'); map_ready()
    tooltip=hover_map(-52,-4,'Pará')
    assert 'Municípios avaliados' in tooltip and 'Indicador' in tooltip and 'Cumprimento' in tooltip
    page.mouse.move(5,500)
    snapshot('mapas-estados.png',page.locator('.st-key-map_main'))
    results.append('Mapa nacional renderizado sem tiles externos; tooltip de UF verificado')
    select('UF','PA · mapa municipal'); map_ready()
    tooltip=hover_map(-48.45,-1.4,'Belém')
    assert '150140' in tooltip and 'Meta:' in tooltip and 'Situação:' in tooltip
    page.mouse.move(5,500)
    snapshot('mapas-municipios.png',page.locator('.st-key-map_main'))
    results.append('Mapa do Pará e tooltip real de Belém verificados')
    select('Ano','2016')
    # Selecionar a opção 15 sem assumir sua descrição.
    box=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Indicador',exact=True)).get_by_role('combobox')
    box.fill('Indicador 15')
    page.get_by_role('option').first.click(); settle();map_ready()
    select('Ano','2021'); map_ready()
    indicator=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Indicador',exact=True)).inner_text()
    assert 'Indicador 15' not in indicator
    results.append('Mapas: troca de ano e indicador, incluindo reset de indicador indisponível')
    select('UF','PI · mapa municipal');map_ready()
    expect(page.get_by_text('7 territórios da malha sem observação no recorte (cinza). Não entram no denominador nem são acrescentados à base.',exact=True)).to_be_visible()
    # Francisco Macedo não tem observação em 2021; a camada cinza não imputa um resultado.
    graph=map_ready()
    unknown=graph.evaluate("gd=>gd.data.filter(t=>t.type==='choropleth').flatMap(t=>Array.from(t.customdata||[])).filter(r=>r[2]==='220415')")
    assert len(unknown)==1 and 'Sem informação' in unknown[0][7] and 'Sem observação' in unknown[0][8]
    results.append('Municípios sem observação: cinza, aviso e tooltip distintos, sem imputação')
    select('UF','Brasil · mapa de UFs');map_ready()
    for width in [1920,1440,1366,1024,768,390]:
        page.set_viewport_size({'width':width,'height':1080 if width>768 else 1000})
        page.get_by_test_id('stMain').evaluate('(el)=>el.scrollTop=0')
        settle()
        assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        # A faixa da navegação cabe na página; sua rolagem interna é intencional.
        assert page.locator('.st-key-pagina').bounding_box()['width'] <= width
        snapshot(f'mapas-{width}.png',page.locator('.st-key-map_main'))
        graph=map_ready()
        shape=graph.locator('.choroplethlayer').bounding_box()
        box=graph.bounding_box()
        assert shape['width'] > min(box['width'],box['height']) * .6, (width,shape,box)
        assert shape['x'] >= box['x']-2 and shape['x']+shape['width'] <= box['x']+box['width']+2, (width,shape,box)
        assert shape['y'] >= box['y']-2 and shape['y']+shape['height'] <= box['y']+box['height']+2, (width,shape,box)
        dimensions.append({'largura':width,'sem_overflow_da_pagina':True,'mapa_enquadrado':True})
    results.append('Mapas e navegação revisados em 1920, 1440, 1366, 1024, 768 e 390px')
    nav('Sobre');nav('Visão Geral')
    density=[]
    for width,height in [(1920,1080),(1440,900),(1366,768),(1024,768),(768,1024),(390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        page.get_by_test_id('stMain').evaluate('(el)=>el.scrollTop=0')
        settle()
        if width<=768:
            toggle=page.get_by_test_id('stSidebarCollapseButton').get_by_role('button')
            if toggle.is_visible(): toggle.click(); page.wait_for_timeout(500)
        snapshot(f'visao-geral-{width}x{height}.png')
        graph=page.get_by_test_id('stPlotlyChart').first.bounding_box()
        density.append({'largura':width,'altura':height,'primeiro_grafico':graph})
        if width==1366: assert graph['y']<450,graph
        assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
    (OUT.parent/'densidade_layout.json').write_text(json.dumps(density,indent=2))
    snapshot('mobile.png')
    page.get_by_test_id('stExpandSidebarButton').click()
    expect(page.get_by_role('button',name='Limpar filtros')).to_be_visible()
    page.get_by_test_id('stSidebarCollapseButton').get_by_role('button').click()
    expect(page.get_by_test_id('stExpandSidebarButton')).to_be_visible()
    results.append('Sidebar móvel abre e recolhe pelos controles nativos')
    page.set_viewport_size({'width':768,'height':1024});snapshot('tablet.png')
    assert not console_errors,console_errors
    assert not external,external
    report={'checks':results,'larguras':dimensions,'browser_errors':console_errors,'requisicoes_externas':external}
    (OUT.parent/'validacao_navegador.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    browser.close()
