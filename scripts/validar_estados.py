"""Confere gráficos de Estados contra contagens diretas dos Parquets, no navegador."""
import argparse
import json
import time
from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url',default='http://127.0.0.1:8501/')
parser.add_argument('--chromium',default='/usr/bin/chromium')
args=parser.parse_args()
base=pd.read_parquet(ROOT/'data/base_pqavs.parquet')
report={'cenarios':[],'barras_conferidas':[],'celulas_conferidas':[],'larguras':[]}
errors=[];external=[]
OUT=ROOT/'docs/screenshots'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1366,'height':768})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
    page.on('request',lambda r:external.append(r.url) if not r.url.startswith((args.url.rstrip('/'),args.url.replace('http:','ws:').rstrip('/'),'blob:','data:')) else None)
    page.goto(args.url)
    page.locator('.js-plotly-plot').first.wait_for(timeout=60000)

    def idle():
        page.wait_for_timeout(300)
        page.locator('.stApp[data-test-script-state="notRunning"]').wait_for(timeout=60000)
        expect(page.get_by_test_id('stException')).to_have_count(0)
        assert not any('Não foi possível concluir' in x for x in page.get_by_test_id('stAlert').all_text_contents())

    def choose(label,value):
        box=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True)).get_by_role('combobox')
        if box.input_value()==value:return
        box.fill(value);page.get_by_role('option',name=value,exact=True).click();idle()

    nav=page.locator('.st-key-pagina')
    assert nav.locator('input[type=radio]').count()==6
    assert not any(x in nav.inner_text() for x in ['Municípios','Indicadores','Comparações'])
    nav.get_by_text('Estados',exact=True).click();idle()
    graph=page.locator('.st-key-chartpanel_state_stack .js-plotly-plot')
    for uf in ['Brasil · todas as UFs','PA','AC']:
        choose('UF',uf)
        for year in [2013,2017,2021]:
            choose('Ano',str(year));graph.wait_for();idle()
            expected_count=15 if year==2017 else 14
            assert graph.evaluate('gd=>gd.data[0].y.length')==expected_count
            values=graph.evaluate('gd=>gd._fullData.map(t=>Array.from(t.x))')
            assert all(abs(sum(values[k][i] for k in range(3))-100)<1e-8 for i in range(expected_count))
            labels=graph.evaluate('gd=>Array.from(gd.data[0].y)')
            assert len(set(labels))==expected_count
            assert page.get_by_test_id('stSelectbox').count()==3
            report['cenarios'].append({'uf':uf,'ano':year,'indicadores':expected_count,'soma_barras_100':True})
    choose('UF','PA');choose('Ano','2021')
    stack=graph.evaluate('gd=>({labels:Array.from(gd.data[0].y),custom:gd.data[0].customdata})')
    for indicator in ['IND_01','IND_06','IND_08']:
        i=next(i for i,label in enumerate(stack['labels']) if label.startswith(indicator.removeprefix('IND_')+' ·'))
        source=base.loc[base.ANO.eq(2021)&base.UF.eq('PA')&base.INDICADOR.eq(indicator)]
        expected=[int(source.SITUACAO.eq(status).sum()) for status in ['Atingida','Não atingida','Sem informação']]
        actual=[int(str(stack['custom'][i][k]).replace('.','')) for k in [2,3,4]]
        assert actual==expected,(indicator,actual,expected)
        report['barras_conferidas'].append({'uf':'PA','ano':2021,'indicador':indicator,'atingida':actual[0],'nao_atingida':actual[1],'sem_informacao':actual[2],'conferencia_direta_parquet':True})
    page.get_by_test_id('stMain').evaluate('(el)=>el.scrollTop=0')
    page.screenshot(path=str(OUT/'estados-para.png'))
    page.locator('.st-key-chartpanel_state_profile').scroll_into_view_if_needed()
    page.screenshot(path=str(OUT/'estados-perfil.png'))
    choose('UF','Brasil · todas as UFs')
    heat=page.locator('.st-key-chartpanel_state_heatmap .js-plotly-plot');heat.wait_for()
    heat_data=heat.evaluate('gd=>({x:Array.from(gd._fullData[0].x),y:Array.from(gd._fullData[0].y),z:Array.from(gd._fullData[0].z).map(r=>Array.from(r)),zmin:gd.data[0].zmin,zmax:gd.data[0].zmax})')
    assert heat_data['zmin']==0 and heat_data['zmax']==100
    for uf,indicator in [('AC','IND_01'),('PA','IND_05'),('DF','IND_14')]:
        source=base.loc[base.ANO.eq(2021)&base.UF.eq(uf)&base.INDICADOR.eq(indicator)]
        hits=int(source.SITUACAO.eq('Atingida').sum());misses=int(source.SITUACAO.eq('Não atingida').sum())
        expected=100*hits/(hits+misses)
        value=heat_data['z'][heat_data['y'].index(uf)][heat_data['x'].index(indicator.removeprefix('IND_'))]
        assert abs(value-expected)<1e-10
        report['celulas_conferidas'].append({'uf':uf,'indicador':indicator,'ano':2021,'atingiram':hits,'nao_atingiram':misses,'cumprimento':value,'conferencia_direta_parquet':True})
    heat.scroll_into_view_if_needed();page.screenshot(path=str(OUT/'estados-heatmap.png'))
    table=page.get_by_test_id('stDataFrame').first
    assert table.bounding_box()['y']>heat.bounding_box()['y']+heat.bounding_box()['height']
    # Tooltip real de uma barra, além da conferência de dados serializados.
    graph.scroll_into_view_if_needed();page.wait_for_timeout(200)
    first=graph.locator('.barlayer .point path').first
    rect=first.bounding_box();page.mouse.move(rect['x']+rect['width']/2,rect['y']+rect['height']/2)
    expect(graph.locator('.hoverlayer')).to_contain_text('Meta atingida:')
    report['tooltip_barra_real']=True
    for width,height in [(1920,1080),(1440,900),(1366,768),(1024,768),(768,1024),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(500)
        if width<=768:
            collapse=page.get_by_test_id('stSidebarCollapseButton').get_by_role('button')
            if collapse.is_visible():collapse.click();page.wait_for_timeout(300)
        page.mouse.move(1,1);page.get_by_test_id('stMain').evaluate('(el)=>el.scrollTop=0')
        assert not page.evaluate('document.documentElement.scrollWidth>window.innerWidth')
        page.screenshot(path=str(OUT/f'estados-{width}.png'))
        heat.scroll_into_view_if_needed();page.wait_for_timeout(200)
        if width==390:
            for panel_key in ['chartpanel_state_stack','chartpanel_state_heatmap']:
                panel=page.locator('.st-key-'+panel_key)
                assert panel.evaluate('e=>e.scrollWidth>e.clientWidth')
                panel.evaluate('e=>e.scrollLeft=e.scrollWidth')
                assert panel.evaluate('e=>e.scrollLeft>0')
            report['rolagem_interna_mobile_verificada']=True
        page.screenshot(path=str(OUT/f'heatmap-{width}.png'))
        assert not page.evaluate('document.documentElement.scrollWidth>window.innerWidth')
        report['larguras'].append({'largura':width,'altura':height,'sem_overflow':True})
    assert not errors,errors
    assert not external,external
    report.update(browser_errors=errors,requisicoes_externas=external,tabela_apos_graficos=True)
    (ROOT/'docs/validacao_estados.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    browser.close()
