"""Validação de alinhamento, cards e análises históricas contra o Parquet."""
import argparse
import json
from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/screenshots'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url',default='http://127.0.0.1:8501/')
parser.add_argument('--chromium',default='/usr/bin/chromium')
args=parser.parse_args()
base=pd.read_parquet(ROOT/'data/base_pqavs.parquet')
catalog=pd.read_parquet(ROOT/'data/indicadores.parquet')
raw=base.loc[base.UF.eq('PA')&base.ANO.eq(2021)]
counts=raw.assign(A=raw.SITUACAO.eq('Atingida'),N=raw.SITUACAO.eq('Não atingida')).groupby('COD_MUN',observed=True).agg(A=('A','sum'),N=('N','sum'))
counts['SHARE']=100*counts.A/(counts.A+counts.N).replace(0,float('nan'))
thresholds={t:{'municipios':int(counts.SHARE.ge(t).sum()),'denominador':int(counts.SHARE.notna().sum()),'percentual':float(100*counts.SHARE.ge(t).sum()/counts.SHARE.notna().sum())} for t in [30,50,70,90]}
bands=pd.cut(counts.SHARE,[-float('inf'),30,50,70,90,float('inf')],right=False,labels=['< 30%','30% a < 50%','50% a < 70%','70% a < 90%','≥ 90%']).astype('string').fillna('Sem avaliação')
report={'pa_2021':{'municipios':len(counts),'patamares':thresholds,'faixas':{label:int(bands.eq(label).sum()) for label in ['< 30%','30% a < 50%','50% a < 70%','70% a < 90%','≥ 90%','Sem avaliação']},
                   'amostra_individual':counts.loc[['150140','150060','150680']].reset_index().to_dict('records')},'larguras':[]}
errors=[];external=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1366,'height':768})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
    page.on('request',lambda r:external.append(r.url) if not r.url.startswith((args.url.rstrip('/'),args.url.replace('http:','ws:').rstrip('/'),'blob:','data:')) else None)
    page.goto(args.url);page.locator('.js-plotly-plot').first.wait_for(timeout=60000)

    def idle():
        page.wait_for_timeout(300)
        page.locator('.stApp[data-test-script-state="notRunning"]').wait_for(timeout=60000)
        expect(page.get_by_test_id('stException')).to_have_count(0)
        assert not any('Não foi possível concluir' in s for s in page.get_by_test_id('stAlert').all_text_contents())

    def nav(name):
        page.locator('.st-key-pagina').get_by_text(name,exact=True).click();idle()
        page.get_by_test_id('stMain').evaluate('(e)=>e.scrollTop=0')

    def choose(label,value):
        box=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True)).get_by_role('combobox')
        if box.input_value()==value:return
        box.fill(value);page.get_by_role('option',name=value,exact=True).click();idle()

    def show_panel(key):
        panel=page.locator('.st-key-'+key)
        panel.scroll_into_view_if_needed()
        page.get_by_test_id('stMain').evaluate('(e,dy)=>e.scrollTop+=dy',panel.bounding_box()['y']-65)
        page.wait_for_timeout(250)
        return panel

    for width,height in [(1920,1080),(1440,900),(1366,768),(1024,768),(768,1024),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(350)
        if width<=768:
            close=page.get_by_test_id('stSidebarCollapseButton').get_by_role('button')
            if close.is_visible():close.click();page.wait_for_timeout(250)
        nav('Visão Geral')
        overview=[]
        for a,b in [('chartpanel_02','chartpanel_01'),('chartpanel_03','chartpanel_04')]:
            left=page.locator('.st-key-'+a).bounding_box();right=page.locator('.st-key-'+b).bounding_box()
            paired=abs(left['y']-right['y'])<2
            if paired:
                assert abs(left['y']+left['height']-right['y']-right['height'])<2,(width,a,left,right)
            overview.append({'linha':a,'lado_a_lado':paired,'esquerdo':left,'direito':right})
        page.screenshot(path=str(OUT/f'alinhamento-geral-{width}.png'))
        show_panel('chartpanel_03');page.screenshot(path=str(OUT/f'alinhamento-rankings-{width}.png'))
        nav('Estados')
        expect(page.locator('.state-card-groups .kpi')).to_have_count(8)
        expect(page.locator('.state-card-groups section')).to_have_count(2)
        expect(page.locator('.state-card-groups .kpi-label').filter(has_text='≥30%')).to_have_count(1)
        assert page.locator('.metric-help').get_attribute('title') and page.locator('.metric-help').get_attribute('aria-label')
        cards=page.locator('.state-card-groups .kpi').all()
        assert min(c.bounding_box()['width'] for c in cards)>=130
        first_chart=page.locator('.st-key-chartpanel_state_stack').bounding_box()
        assert page.locator('.state-card-groups').bounding_box()['y']<first_chart['y']
        if width==1366:assert first_chart['y']<600
        page.screenshot(path=str(OUT/f'cards-estados-{width}.png'))
        assert not page.evaluate('document.documentElement.scrollWidth>window.innerWidth')
        report['larguras'].append({'largura':width,'altura':height,'alinhamento':overview,'oito_cards_sem_duplicacao':True,'primeiro_grafico_estados_y':first_chart['y'],'sem_overflow':True})
    page.set_viewport_size({'width':1366,'height':768});page.wait_for_timeout(600);idle()
    expand=page.get_by_test_id('stExpandSidebarButton')
    if expand.is_visible():expand.click();page.wait_for_timeout(300)
    choose('UF','PA')
    grid=page.locator('section[aria-label="Perfil de alcance"]')
    notes=grid.locator('.kpi-note').all_text_contents()
    values=grid.locator('.kpi-value').all_text_contents()
    for i,t in enumerate([30,50,70,90]):
        assert str(thresholds[t]['municipios']) in notes[i].replace('.','')
        assert values[i]==f"{thresholds[t]['percentual']:.1f}%".replace('.',',')
    distribution=page.locator('.st-key-chartpanel_state_profile .js-plotly-plot')
    fig=distribution.evaluate('gd=>({labels:Array.from(gd.data[0].y),values:Array.from(gd._fullData[0].x)})')
    for label,value in zip(fig['labels'],fig['values']):assert int(value)==report['pa_2021']['faixas'].get(label,0)
    nav('Histórico')
    page.get_by_text('Explorar perfil e persistência',exact=True).click();idle()
    evolution=page.locator('.st-key-chartpanel_profile_evolution .js-plotly-plot')
    evolution.wait_for(timeout=60000)
    points=evolution.evaluate('gd=>gd.data.map(t=>({name:t.name,x:Array.from(t.x),custom:t.customdata}))')
    for trace,t in zip(points,[30,50,70,90]):
        i=next(i for i,x in enumerate(trace['x']) if x==2021)
        assert int(trace['custom'][i][0])==thresholds[t]['municipios']
        assert int(trace['custom'][i][1])==thresholds[t]['denominador']
    report['evolucao_2021_confere_com_parquet']=True
    matrix=page.locator('.st-key-chartpanel_persistence .js-plotly-plot');matrix.wait_for(timeout=60000)
    cells=matrix.evaluate('gd=>({x:Array.from(gd.data[0].x),custom:gd.data[0].customdata,z:Array.from(gd._fullData[0].z).map(r=>Array.from(r)),min:gd.data[0].zmin,max:gd.data[0].zmax})')
    assert cells['min']==0 and cells['max']==100
    series=catalog.loc[catalog.ANO.eq(2021)&catalog.INDICADOR.eq('IND_14'),'SERIE'].iloc[0]
    audit=[]
    for year,number in [(2016,'IND_15'),(2021,'IND_14')]:
        column=cells['x'].index(str(year))
        row=next(i for i,line in enumerate(cells['custom']) if line[column][2]==number)
        source=base.loc[base.UF.eq('PA')&base.ANO.eq(year)&base.SERIE.eq(series)]
        hits=int(source.SITUACAO.eq('Atingida').sum());misses=int(source.SITUACAO.eq('Não atingida').sum())
        expected=100*hits/(hits+misses)
        assert abs(cells['z'][row][column]-expected)<1e-10
        audit.append({'ano':year,'numero':number,'linha':row,'atingiram':hits,'nao_atingiram':misses,'cumprimento':expected})
    assert audit[0]['linha']==audit[1]['linha']
    report['renumeracao_conferida']=audit
    for width,height in [(1920,1080),(1440,900),(1366,768),(1024,768),(768,1024),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(350)
        if width<=768:
            close=page.get_by_test_id('stSidebarCollapseButton').get_by_role('button')
            if close.is_visible():close.click();page.wait_for_timeout(250)
        show_panel('chartpanel_profile_evolution');page.screenshot(path=str(OUT/f'perfil-historico-{width}.png'))
        show_panel('chartpanel_persistence');page.screenshot(path=str(OUT/f'persistencia-{width}.png'))
        assert not page.evaluate('document.documentElement.scrollWidth>window.innerWidth')
    assert not errors,errors
    assert not external,external
    report.update(browser_errors=errors,requisicoes_externas=external)
    (ROOT/'docs/validacao_refinamento.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    browser.close()
