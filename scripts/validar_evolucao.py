"""Valida as séries conceituais e os mapas temporais na aplicação em execução."""
import argparse
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url',default='http://127.0.0.1:8501/')
parser.add_argument('--chromium',default='/usr/bin/chromium')
args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/screenshots'
errors=[]
external=[]
report={'series':[],'mapas':[],'larguras':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1366,'height':768})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
    page.on('request',lambda r:external.append(r.url) if not r.url.startswith((args.url.rstrip('/'),args.url.replace('http:','ws:').rstrip('/'),'blob:','data:')) else None)
    page.goto(args.url)
    page.locator('.js-plotly-plot').first.wait_for(timeout=60000)

    def clean():
        expect(page.get_by_test_id('stException')).to_have_count(0)
        assert not any('Não foi possível concluir' in t for t in page.get_by_test_id('stAlert').all_text_contents())

    def nav(label):
        page.locator('.st-key-pagina').get_by_text(label,exact=True).click()
        page.wait_for_timeout(450);page.locator('.stApp[data-test-script-state="notRunning"]').wait_for(timeout=60000);clean()

    def box(label):
        return page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True)).get_by_role('combobox')

    def choose(label, value):
        control=box(label)
        if control.input_value()==value:return
        control.fill(value)
        page.get_by_role('option',name=value,exact=True).click()
        page.wait_for_timeout(450);page.locator('.stApp[data-test-script-state="notRunning"]').wait_for(timeout=60000);clean()

    def hover(graph,xy,expected):
        graph.scroll_into_view_if_needed()
        point=graph.evaluate('(gd,xy)=>gd._fullLayout.geo._subplot.projection(xy)',xy)
        rect=graph.bounding_box()
        page.mouse.move(rect['x']+point[0],rect['y']+point[1])
        expect(graph.locator('.hoverlayer')).to_contain_text(expected)
        return graph.locator('.hoverlayer').text_content()

    assert not page.get_by_test_id('stAppDeployButton').is_visible()
    assert not page.get_by_test_id('stMainMenu').is_visible()
    for name in ['Histórico']:
        nav(name)
        control=box('Indicador · série conceitual')
        control.fill('Número de ciclos')
        page.wait_for_timeout(200)
        options=page.get_by_role('option').all_text_contents()
        assert len(options)==1 and '08/09' in options[0]
        page.screenshot(path=str(OUT/f'series-{name.lower()}.png'))
        page.keyboard.press('Escape')
        control.fill('ocupação')
        page.wait_for_timeout(200)
        occupation=[x for x in page.get_by_role('option').all_text_contents() if 'ocupação' in x]
        assert len(occupation)==1
        occupation=occupation[0]
        page.get_by_role('option',name=occupation,exact=True).click()
        page.wait_for_timeout(500);clean()
        assert '2013–2021' in occupation and '13/14' in occupation
        report['series'].append({'pagina':name,'busca_ciclos_opcoes':len(options),'ciclos_uma_opcao':True,'renumeracao_13_14':True})

    nav('Mapas')
    page.get_by_text('Comparar mapas no tempo',exact=True).click()
    grid=page.locator('.st-key-map_history_grid')
    start=time.perf_counter()
    expect(grid.locator('.js-plotly-plot')).to_have_count(5,timeout=60000)
    grid.locator('.choroplethlayer path').first.wait_for(timeout=60000)
    report['primeira_renderizacao_historico_segundos']=round(time.perf_counter()-start,3)
    figs=grid.locator('.js-plotly-plot')
    for graph in figs.all():
        values=graph.evaluate("gd=>gd.data.filter(t=>t.zmax===100).map(t=>[t.zmin,t.zmax,t.showscale])")
        assert values==[[0,100,False]],values
    tooltip=hover(figs.first,[-52,-4],'Pará')
    assert '2014' in tooltip and 'Municípios avaliados' in tooltip
    report['mapas'].append('Brasil: cinco mapas, escala 0–100 comum, legenda compartilhada e tooltip verificados')
    page.mouse.move(1,500)
    page.get_by_test_id('stMain').evaluate('(el,dy)=>el.scrollTop+=dy',page.get_by_test_id('stExpander').filter(has=grid).bounding_box()['y']-60);page.wait_for_timeout(300)
    page.screenshot(path=str(OUT/'evolucao-brasil.png'))
    choose('UF','PA · mapa municipal')
    expect(grid.locator('.js-plotly-plot')).to_have_count(5,timeout=60000)
    grid.locator('.choroplethlayer path').first.wait_for(timeout=60000)
    page.wait_for_function("Array.from(document.querySelectorAll('.st-key-map_history_grid .js-plotly-plot')).every(g=>g.data?.[0]?.featureidkey==='properties.COD_MUN')",timeout=60000)
    page.wait_for_timeout(500)
    tooltip=hover(grid.locator('.js-plotly-plot').first,[-48.45,-1.4],'Belém')
    assert '150140' in tooltip and '2014' in tooltip and 'Meta:' in tooltip
    for graph in grid.locator('.js-plotly-plot').all():
        data=graph.evaluate('gd=>gd.data.map(t=>({name:t.name,color:t.colorscale[0][1]}))')
        colors={'Atingida':'#14887D','Não atingida':'#CA785C','Sem informação':'#ACB9C8'}
        assert all(t['color']==colors[t['name']] for t in data)
    report['mapas'].append('Pará: cinco mapas municipais, cores categóricas constantes e tooltip de Belém verificados')
    page.mouse.move(1,500)
    page.get_by_test_id('stMain').evaluate('(el,dy)=>el.scrollTop+=dy',page.get_by_test_id('stExpander').filter(has=grid).bounding_box()['y']-60);page.wait_for_timeout(300)
    page.screenshot(path=str(OUT/'evolucao-para.png'))
    for width,height in [(1920,1080),(1440,900),(1366,768),(1024,768),(768,1024),(390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        page.wait_for_timeout(600)
        if width<=768:
            collapse=page.get_by_test_id('stSidebarCollapseButton').get_by_role('button')
            if collapse.is_visible():collapse.click();page.wait_for_timeout(400)
        rects=[g.bounding_box() for g in grid.locator('.js-plotly-plot').all()]
        assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        for graph in grid.locator('.js-plotly-plot').all():
            shape=graph.locator('.choroplethlayer').bounding_box();rect=graph.bounding_box()
            assert shape['width']>.6*min(rect['width'],rect['height'])
            assert shape['x']>=rect['x']-2 and shape['x']+shape['width']<=rect['x']+rect['width']+2
        columns=sum(abs(r['y']-rects[0]['y'])<3 for r in rects)
        assert columns==(3 if width==1920 else 1 if width==390 else 2),(width,columns)
        page.get_by_test_id('stMain').evaluate('(el,dy)=>el.scrollTop+=dy',page.get_by_test_id('stExpander').filter(has=grid).bounding_box()['y']-60);page.wait_for_timeout(300)
        page.screenshot(path=str(OUT/f'evolucao-{width}.png'))
        report['larguras'].append({'largura':width,'altura':height,'colunas':columns,'sem_overflow':True})
    page.get_by_test_id('stExpandSidebarButton').click()
    expect(page.get_by_role('button',name='Limpar filtros')).to_be_visible()
    page.get_by_test_id('stSidebarCollapseButton').get_by_role('button').click()
    report['sidebar_movel_abre_recolhe']=True
    clean()
    assert not errors,errors
    assert not external,external
    report['browser_errors']=errors;report['requisicoes_externas']=external
    (ROOT/'docs/validacao_evolucao.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    browser.close()
