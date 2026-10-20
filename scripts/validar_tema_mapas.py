"""Navegador real: tema, modos, filtros, escala temporal e números do Parquet."""
import json
import time
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--width",type=int,default=None,help="Diagnóstico opcional de uma largura")
args=parser.parse_args()
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/screenshots'
report={'telas':[],'mapas':[],'tooltips':[],'erros':[],'externos':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1366,'height':768})
    page.on('pageerror',lambda e:report['erros'].append(str(e)))
    page.on('console',lambda m:report['erros'].append(m.text) if m.type=='error' else None)
    page.on('request',lambda r:report['externos'].append(r.url) if not r.url.startswith(('http://127.0.0.1:8501/','ws://127.0.0.1:8501/','blob:','data:')) else None)
    page.goto('http://127.0.0.1:8501/')
    page.locator('.js-plotly-plot').first.wait_for(timeout=60000)

    def idle():
        page.wait_for_timeout(400)
        page.locator('.stApp[data-test-script-state="notRunning"]').wait_for(timeout=60000)
        expect(page.get_by_test_id('stException')).to_have_count(0)
        assert not any('Não foi possível concluir' in t for t in page.get_by_test_id('stAlert').all_text_contents())

    def nav(label):
        page.locator('.st-key-pagina').get_by_text(label,exact=True).click();idle()
        page.get_by_test_id('stMain').evaluate('el=>el.scrollTop=0')

    def sidebar():
        button=page.get_by_test_id('stExpandSidebarButton')
        if button.is_visible():button.click();idle()

    def choose(label,needle):
        sidebar()
        box=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True)).get_by_role('combobox')
        if box.input_value()==needle:return
        box.fill(needle)
        page.get_by_role('option',name=needle,exact=True).click();idle()

    def indicator(number):
        sidebar()
        box=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Indicador',exact=True)).get_by_role('combobox')
        needle=f'Indicador {int(number):02d} —'
        box.fill(needle)
        page.get_by_role('option').filter(has_text=needle).first.click();idle()
        assert box.input_value().startswith(needle),box.input_value()

    def mode(label):
        if page.viewport_size['width']<600 and page.get_by_test_id('stSidebarCollapseButton').is_visible():
            page.get_by_test_id('stSidebarCollapseButton').click();idle()
        page.locator('.st-key-map_mode').get_by_role('radio',name=label,exact=True).click();idle()

    def graph_main():
        g=page.locator('.st-key-map_main .js-plotly-plot')
        g.locator('.choroplethlayer path').first.wait_for(timeout=60000)
        return g

    def hover_belém():
        g=graph_main();g.scroll_into_view_if_needed()
        xy=g.evaluate('(gd)=>gd._fullLayout.geo._subplot.projection([-48.45,-1.4])')
        rect=g.bounding_box();page.mouse.move(rect['x']+xy[0],rect['y']+xy[1])
        expect(g.locator('.hoverlayer')).to_contain_text('Belém')
        text=g.locator('.hoverlayer').text_content();report['tooltips'].append(text)
        page.mouse.move(1,1)
        return text

    for width,height in [(1920,1080),(1440,900),(1366,768),(1024,768),(768,1024),(390,844)]:
        if args.width and width!=args.width:continue
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(650);idle()
        for label in ['Visão Geral','Estados','Mapas','Histórico','Dados','Sobre']:
            nav(label)
            overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth+2')
            assert not overflow,(width,label)
            main=page.get_by_test_id('stMain').evaluate('el=>({left:el.scrollLeft,sw:el.scrollWidth,cw:el.clientWidth})')
            assert main['left']==0 and main['sw']<=main['cw']+2,(width,label,main)
            primary=page.locator('.stApp').evaluate('el=>getComputedStyle(el).getPropertyValue("--primary").trim()')
            assert primary=='#176B78'
            page.screenshot(path=str(OUT/f'tema-{label.lower().replace(" ","-")}-{width}.png'))
            report['telas'].append({'largura':width,'pagina':label,'sem_overflow':True})
        nav('Mapas');sidebar();choose('UF','PA · mapa municipal');indicator('1')
        toggle=page.get_by_text('Comparar mapas no tempo',exact=True)
        if not page.locator('.st-key-mapa_historico input').is_checked():toggle.click();idle()
        grid=page.locator('.st-key-map_history_grid')
        expect(grid.locator('.js-plotly-plot')).to_have_count(5,timeout=60000)
        years_before=grid.get_by_role('heading').all_text_contents()
        mode('Grau de alcance (%)')
        expect(grid.locator('.js-plotly-plot')).to_have_count(5,timeout=60000)
        assert grid.get_by_role('heading').all_text_contents()==years_before
        assert page.locator('.st-key-mapa_uf').get_by_role('combobox').input_value()=='PA · mapa municipal'
        for graph in grid.locator('.js-plotly-plot').all():
            graph.locator('.choroplethlayer path').first.wait_for(timeout=60000)
            traces=graph.evaluate('gd=>gd.data.filter(t=>t.showscale===false && t.colorscale?.length===5).map(t=>[t.zmin,t.zmax])')
            assert traces==[[0,100]],traces
        main=graph_main()
        controls=page.locator('.st-key-map_mode').bounding_box()
        assert controls['width']<=width and controls['x']>=0,(width,controls)
        main_size=page.get_by_test_id('stMain').evaluate('el=>({left:el.scrollLeft,sw:el.scrollWidth,cw:el.clientWidth})')
        assert main_size['left']==0 and main_size['sw']<=main_size['cw']+2,main_size
        if width==1366:
            t=hover_belém();assert '139,7%' in t and '≥100%' in t and '125,73%' in t
            for number,expected in [('2','88,4%'),('4','0,0%'),('7','60,0%')]:
                indicator(number);t=hover_belém();assert expected in t,(number,t)
            indicator('1')
        # Recolher a sidebar no celular para conferir canvas e controles úteis.
        if width==390 and page.get_by_test_id('stSidebarCollapseButton').is_visible():
            page.get_by_test_id('stSidebarCollapseButton').click();idle()
        page.get_by_test_id('stMain').evaluate('el=>el.scrollTop=0')
        page.screenshot(path=str(OUT/f'grau-mapa-{width}.png'))
        if width==1366:
            page.locator('.st-key-map_main').screenshot(path=str(OUT/'grau-detalhe-1366.png'))
        expander=page.get_by_test_id('stExpander').filter(has=grid)
        page.get_by_test_id('stMain').evaluate('(el,dy)=>el.scrollTop+=dy',expander.bounding_box()['y']-60)
        page.wait_for_timeout(200);page.screenshot(path=str(OUT/f'grau-historico-{width}.png'))
        report['mapas'].append({'largura':width,'municipal_continuo':True,'historico_escala_0_100':True,'filtros_preservados':True})
        page.get_by_test_id('stMain').evaluate('el=>el.scrollTop=0');mode('Situação da meta')
        assert grid.get_by_role('heading').all_text_contents()==years_before
        page.screenshot(path=str(OUT/f'situacao-mapa-{width}.png'))
        # Limpar histórico e recorte para próxima sequência de páginas.
        sidebar();page.get_by_role('button',name='Limpar filtros',exact=True).click();idle()
    page.set_viewport_size({'width':1366,'height':768});page.wait_for_timeout(650)
    nav('Mapas');sidebar()
    for uf in ['Brasil · mapa de UFs','PA · mapa municipal','AC · mapa municipal']:
        choose('UF',uf);indicator('14')
        if not page.locator('.st-key-mapa_historico input').is_checked():page.get_by_text('Comparar mapas no tempo',exact=True).click();idle()
        mode('Grau de alcance (%)');graph_main()
        if uf.startswith('Brasil'):
            assert 'Não há resultado estadual validado' in page.get_by_test_id('stAlert').all_text_contents()[0]
        else:
            indicator('8')
            expect(page.locator('.st-key-map_main')).to_contain_text('Grau percentual de alcance não disponível')
            expect(page.locator('.st-key-map_main .js-plotly-plot')).to_have_count(0)
        mode('Situação da meta');graph_main()
    assert not report['erros'] and not report['externos'],report
    (ROOT/('docs/validacao_tema_mapas.json' if not args.width else f'docs/validacao_tema_mapas_{args.width}.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    browser.close()
print(json.dumps(report,ensure_ascii=False,indent=2))
