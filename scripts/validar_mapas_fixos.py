"""Layout fixo de Mapas: alternância exclusiva, filtros, escalas e seis telas."""
import json
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--width",type=int)
args=parser.parse_args()
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
report={'telas':[],'erros':[],'externos':[]}
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
    def sidebar():
        if page.get_by_test_id('stExpandSidebarButton').is_visible():page.get_by_test_id('stExpandSidebarButton').click();idle()
    def close():
        if page.viewport_size['width']<800 and page.get_by_test_id('stSidebarCollapseButton').is_visible():page.get_by_test_id('stSidebarCollapseButton').click();idle()
    def choose(label,value):
        sidebar()
        box=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True)).get_by_role('combobox')
        box.fill(value);page.get_by_role('option').filter(has_text=value).first.click();idle()
    def mode(value):
        sidebar();page.locator('.st-key-map_mode').get_by_text(value,exact=True).click();idle();close()
    def toggle():
        sidebar();page.get_by_text('Comparar mapas no tempo',exact=True).click();idle();close()
    def measure(comparison,width):
        main=page.get_by_test_id('stMain').evaluate('e=>({h:e.clientHeight,sh:e.scrollHeight,w:e.clientWidth,sw:e.scrollWidth,top:e.scrollTop})')
        assert main['sh']<=main['h']+2 and main['sw']<=main['w']+2,main
        viewport=page.locator('[class*=st-key-map_viewport_]')
        assert viewport.evaluate('e=>e.scrollTop')==0
        rect=viewport.bounding_box()
        assert rect['height']>100 and rect['y']+rect['height']<=page.viewport_size['height']+2,rect
        expect(page.locator('.st-key-map_main')).to_have_count(0 if comparison else 1)
        expect(page.locator('.st-key-map_ranking')).to_have_count(0 if comparison else 1)
        expect(page.locator('.st-key-map_comparison')).to_have_count(1 if comparison else 0)
        graphs=viewport.locator('.js-plotly-plot')
        expect(graphs).to_have_count(5 if comparison else 2,timeout=60000)
        for graph in graphs.all():
            if graph.evaluate('g=>g.data[0].type')=='choropleth':
                graph.locator('.choroplethlayer path').first.wait_for(timeout=60000)
                size=graph.bounding_box();assert size['height']>=95 and size['width']>=120,size
        if not comparison:
            a=page.locator('.st-key-map_main').bounding_box();b=page.locator('.st-key-map_ranking').bounding_box()
            assert a['x']+a['width']<=b['x']+2 or a['y']+a['height']<=b['y']+2,(a,b)
        else:
            for cell in page.locator('[class*=st-key-map_year_]').all():
                figure=cell.locator('.js-plotly-plot')
                if figure.count():
                    a=cell.bounding_box();b=figure.bounding_box()
                    assert b['y']>=a['y'] and b['y']+b['height']<=a['y']+a['height']+2,(a,b)
        internal=viewport.evaluate('e=>({h:e.clientHeight,sh:e.scrollHeight,w:e.clientWidth,sw:e.scrollWidth})')
        assert internal['sw']<=internal['w']+2,internal
        if width>=1024:assert internal['sh']<=internal['h']+3,internal
        # O cabeçalho da página não contém explicações ou controles antes dos cards.
        assert page.locator('.page-heading p').inner_text()==''
        report['telas'].append({'largura':width,'comparacao':comparison,'main':main,'area_mapas':internal})
    page.locator('.st-key-pagina').get_by_text('Mapas',exact=True).click();idle()
    choose('Indicador','Indicador 13 —')
    for width,height in [(1920,1080),(1440,900),(1366,768),(1024,768),(768,1024),(390,844)]:
        if args.width and width!=args.width:continue
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(600);idle()
        for uf in ['PA · mapa municipal','Brasil · mapa de UFs']:
            choose('UF',uf);close()
            for selected_mode in ['Situação da meta','Grau de alcance (%)']:
                mode(selected_mode);measure(False,width)
                page.screenshot(path=str(ROOT/f'docs/screenshots/mapas-fixos-atual-{width}-{uf[:2]}-{selected_mode[:1]}.png'))
                toggle();measure(True,width)
                grid=page.locator('.st-key-map_history_grid')
                labels=grid.get_by_test_id('stMarkdownContainer').all_text_contents()
                assert all(str(y) in ' '.join(labels) for y in [2013,2015,2017,2019,2021]),labels
                for graph in grid.locator('.js-plotly-plot').all():
                    traces=graph.evaluate('g=>g.data.map(t=>({scale:t.colorscale,min:t.zmin,max:t.zmax,show:t.showscale}))')
                    for t in traces:
                        assert not t['show']
                        if uf.startswith('Brasil') or selected_mode.startswith('Grau'):
                            assert t['min']==0 and t['max']==100
                        else:assert len(t['scale'])==2 and t['scale'][0][1]==t['scale'][1][1]
                page.screenshot(path=str(ROOT/f'docs/screenshots/mapas-fixos-comparacao-{width}-{uf[:2]}-{selected_mode[:1]}.png'))
                if width<800:
                    page.locator('[class*=st-key-map_viewport_]').evaluate('e=>e.scrollTop=e.scrollHeight');idle()
                    assert page.get_by_test_id('stMain').evaluate('e=>e.scrollTop')==0
                toggle();measure(False,width)
                sidebar()
                assert page.locator('.st-key-mapa_ano').get_by_role('combobox').input_value()=='2021'
                assert page.locator('.st-key-mapa_uf').get_by_role('combobox').input_value()==uf
                assert page.locator('.st-key-mapa_indicador').get_by_role('combobox').input_value().startswith('Indicador 13 —')
                close()
    # Indisponibilidade e transição de volta ao fluxo normal das outras páginas.
    choose('UF','AC · mapa municipal');choose('Indicador','Indicador 08 —');mode('Grau de alcance (%)')
    expect(page.locator('.st-key-map_main')).to_contain_text('Grau percentual de alcance não disponível')
    toggle();expect(page.locator('.st-key-map_history_grid')).to_contain_text('Grau percentual de alcance não disponível')
    expect(page.locator('[class*=st-key-map_viewport_] .js-plotly-plot')).to_have_count(0)
    close();page.locator('.st-key-pagina').get_by_text('Visão Geral',exact=True).click();idle()
    assert page.get_by_test_id('stMain').evaluate('e=>getComputedStyle(e).overflowY')!='hidden'
    assert not report['erros'] and not report['externos'],report
    (ROOT/('docs/validacao_mapas_fixos.json' if not args.width else f'docs/validacao_mapas_fixos_{args.width}.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    browser.close()
print(json.dumps(report,ensure_ascii=False,indent=2))
