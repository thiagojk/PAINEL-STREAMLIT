"""Plotly com estilo comum e tooltips em português."""
import textwrap
import pandas as pd
from html import escape
import plotly.express as px
import plotly.graph_objects as go
from src.data import STATUS
from src.utils import number, percent, result

COLORS = {'Atingida': '#14887D', 'Não atingida': '#CA785C', 'Sem informação': '#ACB9C8'}
BLUE = '#206A8A'
PALETTE = ['#137C8B', '#5266A4', '#A66D38', '#835894', '#587A3C']


def style(fig, title=None, height=325, percent_axis=False):
    fig.update_layout(
        title=dict(text='<br>'.join(textwrap.wrap(title, 36)) if title else '', font=dict(size=16, color='#18344A'), x=0),
        font=dict(family='Arial, sans-serif', size=12, color='#526578'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=12, r=16, t=(58 if title and len(title) > 36 else 38) if title else 12, b=16), height=height,
        legend=dict(title=None, orientation='h', y=-.16, x=0),
        hoverlabel=dict(bgcolor='#18344A', font_color='white'),
        separators=',.',
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor='#E6ECF1', zeroline=False)
    if percent_axis:
        fig.update_yaxes(ticksuffix='%', rangemode='tozero')
    return fig


def donut(frame):
    counts = frame.SITUACAO.value_counts().reindex(STATUS, fill_value=0)
    fig = go.Figure(go.Pie(labels=counts.index, values=counts.values, hole=.73,
                          marker=dict(colors=[COLORS[k] for k in STATUS], line=dict(color='white', width=3)),
                          text=[percent(100*v/counts.sum()) if counts.sum() and 100*v/counts.sum() >= 5 else '' for v in counts.values],
                          textinfo='text', textposition='inside', textfont=dict(size=13, color='white'), sort=False,
                          hovertemplate='%{label}<br>Registros: %{value:,.0f}<br>Participação no total: %{percent}<extra></extra>'))
    return style(fig, height=325)


def ranking(summary, group, title, limit=27):
    table = summary.dropna(subset=['CUMPRIMENTO']).sort_values('CUMPRIMENTO', ascending=False).head(limit).sort_values('CUMPRIMENTO')
    fig = px.bar(table, x='CUMPRIMENTO', y=group, orientation='h',
                 custom_data=['ATINGIRAM', 'NAO_ATINGIRAM', 'AVALIADOS', 'SEM_INFORMACAO'] + (['DESCRICAO'] if 'DESCRICAO' in table else []),
                 color_discrete_sequence=[BLUE])
    fig.update_traces(text=[percent(v) for v in table.CUMPRIMENTO], textposition='outside', cliponaxis=False,
                      textfont=dict(size=11, color='#244e62'), marker_cornerradius=4, hovertemplate=(
        '%{y}<br>Cumprimento: %{x:.1f}%<br>Atingiram: %{customdata[0]:,.0f}'
        '<br>Não atingiram: %{customdata[1]:,.0f}<br>Avaliados: %{customdata[2]:,.0f}'
        '<br>Sem informação: %{customdata[3]:,.0f}' + ('<br>%{customdata[4]}' if 'DESCRICAO' in table else '') + '<extra></extra>'))
    fig.update_xaxes(title='% de metas atingidas entre avaliadas', ticksuffix='%', range=[0, 116])
    fig.update_yaxes(title=None, categoryorder='array', categoryarray=table[group].tolist())
    return style(fig, title, max(320, len(table) * 23 + 85))


def time_line(summary, title='Evolução do cumprimento das metas', color=None):
    fig = px.line(summary, x='ANO', y='CUMPRIMENTO', color=color, markers=True,
                  color_discrete_sequence=PALETTE,
                  custom_data=['ATINGIRAM', 'NAO_ATINGIRAM', 'AVALIADOS', 'SEM_INFORMACAO'],
                  line_dash=color, symbol=color)
    fig.update_traces(line_width=3, marker_size=7,
                      hovertemplate='Ano: %{x}<br>Cumprimento: %{y:.1f}%<br>Atingiram: %{customdata[0]:,.0f}<br>Não atingiram: %{customdata[1]:,.0f}<br>Avaliados: %{customdata[2]:,.0f}<br>Sem informação: %{customdata[3]:,.0f}<extra>%{fullData.name}</extra>')
    add_line_labels(fig, '%')
    fig.update_xaxes(title=None, dtick=1)
    fig.update_yaxes(title='% de metas atingidas', range=[0, 112])
    return style(fig, title, percent_axis=True)


def counts_history(summary):
    data = summary.rename(columns={'ATINGIRAM': 'Atingida', 'NAO_ATINGIRAM': 'Não atingida', 'SEM_INFORMACAO': 'Sem informação'})
    fig = px.bar(data, x='ANO', y=STATUS, color_discrete_map=COLORS, labels={'value': 'Registros', 'variable': 'Situação'}, barmode='stack')
    for trace in fig.data:
        trace.update(text=[number(v) if v and len(summary) <= 10 else '' for v in trace.y], textposition='inside', textfont=dict(size=11),
                     hovertemplate='Ano: %{x}<br>Registros: %{y:,.0f}<extra>%{fullData.name}</extra>')
    fig.update_xaxes(title=None, dtick=1)
    return style(fig, 'Situação das metas ao longo do tempo')


def trajectory(frame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=frame.ANO, y=frame.RES_EXIBICAO, mode='lines+markers', name='Resultado',
                             line=dict(color=BLUE, width=3), customdata=frame[['SITUACAO']],
                             hovertemplate='Ano: %{x}<br>Resultado: %{y:.2f}<br>Situação: %{customdata[0]}<extra></extra>'))
    if frame.META_NUMERICA.notna().any():
        fig.add_trace(go.Scatter(x=frame.ANO, y=frame.META_NUMERICA, mode='lines', name='Meta do ano',
                                 line=dict(color='#CA785C', dash='dash'), hovertemplate='Ano: %{x}<br>Meta: %{y:.1f}%<extra></extra>'))
    add_line_labels(fig, '%' if frame.UNIDADE.iloc[0] == '%' else 'Original', max_points=12, ignore_names={'Meta do ano'})
    fig.update_xaxes(title=None, dtick=1)
    fig.update_yaxes(title='Resultado (%)' if frame.UNIDADE.iloc[0] == '%' else 'Resultado na escala original')
    return style(fig, 'Trajetória do resultado municipal')


def add_line_labels(fig, unit='%', max_points=12, ignore_names=None):
    candidates = [t for t in fig.data if t.type == 'scatter' and t.name not in (ignore_names or set())]
    last_positions = []
    for index, trace in enumerate(candidates):
        values = list(trace.y)
        if not values:
            continue
        labels = [''] * len(values)
        if len(candidates) == 1 and len(values) <= max_points:
            labels = [percent(v) if unit == '%' else number(v, 2) for v in values]
        elif len(candidates) <= 5:
            last = values[-1]
            if last is not None and all(abs(last - old) >= 5 for old in last_positions):
                labels[-1] = percent(last) if unit == '%' else number(last, 2)
                last_positions.append(last)
        trace.update(mode='lines+markers+text', text=labels,
                     textposition=['top center' if i % 2 == 0 else 'bottom center' for i in range(len(values))] if len(candidates) == 1 else 'top right',
                     textfont=dict(size=11, color=trace.line.color), cliponaxis=False)
    return fig


def coverage(summary):
    fig = px.bar(summary, x='ANO', y='AVALIADOS', color_discrete_sequence=[BLUE])
    fig.update_traces(text=[number(v) for v in summary.AVALIADOS], textposition='outside', cliponaxis=False,
                      hovertemplate='Ano: %{x}<br>Municípios avaliados: %{y:,.0f}<extra></extra>')
    fig.update_xaxes(title=None, dtick=1)
    fig.update_yaxes(title='Municípios avaliados', rangemode='tozero')
    return style(fig, 'Cobertura da avaliação por ano')


def _map_layout(fig, geojson, title):
    # Autoenquadramento nativo considera o tamanho real do canvas, inclusive no celular.
    fig.update_geos(fitbounds='locations', visible=False, projection_type='mercator')
    fig.update_layout(dragmode='pan', uirevision=title)
    style(fig, height=590)
    fig.update_layout(margin=dict(l=0,r=0,t=6,b=0), legend=dict(orientation='h', y=-.02))
    return fig


def state_map(summary, geojson, year, indicator_label):
    properties = pd.DataFrame([f['properties'] for f in geojson['features']])
    data = properties.merge(summary, on='UF', how='left', validate='one_to_one')
    fig = go.Figure()
    known = data[data.CUMPRIMENTO.notna()]
    custom = [[r.NOME_UF, str(year), indicator_label, number(r.AVALIADOS), number(r.ATINGIRAM),
               number(r.NAO_ATINGIRAM), number(r.SEM_INFORMACAO), percent(r.CUMPRIMENTO)] for r in known.itertuples()]
    fig.add_trace(go.Choropleth(geojson=geojson, locations=known.UF, featureidkey='properties.UF',
        z=known.CUMPRIMENTO, zmin=0, zmax=100,
        colorscale=[[0,'#B96750'],[.25,'#D7A18A'],[.5,'#EEE9DC'],[.75,'#7AB5AC'],[1,'#15796F']],
        marker_line_color='#ffffff', marker_line_width=1, customdata=custom,
        colorbar=dict(title='Cumprimento', orientation='h', x=.5, y=-.07, len=.78, thickness=10,
                      tickvals=[0,20,40,60,80,100], ticktext=['0%','20%','40%','60%','80%','100%']),
        hovertemplate='<b>%{customdata[0]}</b><br>Ano: %{customdata[1]}<br>Indicador: %{customdata[2]}<br>Municípios avaliados: %{customdata[3]}<br>Atingiram: %{customdata[4]}<br>Não atingiram: %{customdata[5]}<br>Sem informação: %{customdata[6]}<br>Cumprimento: %{customdata[7]}<extra></extra>'))
    unknown = data[data.CUMPRIMENTO.isna()]
    if len(unknown):
        fig.add_trace(go.Choropleth(geojson=geojson, locations=unknown.UF, featureidkey='properties.UF',
            z=[0]*len(unknown), colorscale=[[0,COLORS[STATUS[2]]],[1,COLORS[STATUS[2]]]], showscale=False,
            marker_line_color='white', customdata=[[r.NOME_UF, str(year), indicator_label, number(r.AVALIADOS), number(r.ATINGIRAM), number(r.NAO_ATINGIRAM), number(r.SEM_INFORMACAO)] for r in unknown.itertuples()],
            hovertemplate='<b>%{customdata[0]}</b><br>Ano: %{customdata[1]}<br>Indicador: %{customdata[2]}<br>Municípios avaliados: %{customdata[3]}<br>Atingiram: %{customdata[4]}<br>Não atingiram: %{customdata[5]}<br>Sem informação: %{customdata[6]}<br>Cumprimento: — (sem avaliação disponível)<extra></extra>'))
    return _map_layout(fig, geojson, f'UF-{year}-{indicator_label}')


def municipality_map(layer, geojson, year, indicator_label, rule):
    fig = go.Figure()
    for status in STATUS:
        rows = layer[layer.SITUACAO_MAPA.eq(status)]
        if rows.empty:
            continue
        custom = [[r.NOME_EXIBICAO, r.UF, r.COD_MUN, str(year), indicator_label,
                   result(r.RES_EXIBICAO, r.UNIDADE), rule,
                   ('✓ Meta atingida' if status == STATUS[0] else '✕ Meta não atingida' if status == STATUS[1] else '— Sem informação'),
                   'Observação presente' if r.TEM_OBSERVACAO else 'Sem observação neste recorte'] for r in rows.itertuples()]
        fig.add_trace(go.Choropleth(geojson=geojson, locations=rows.COD_MUN, featureidkey='properties.COD_MUN',
            z=[0]*len(rows), colorscale=[[0,COLORS[status]],[1,COLORS[status]]],
            marker_line_color='white', marker_line_width=.45, showscale=False, name=status,
            customdata=custom,
            hovertemplate='<b>%{customdata[0]} · %{customdata[1]}</b><br>Código da base: %{customdata[2]}<br>Ano: %{customdata[3]}<br>Indicador: %{customdata[4]}<br>Resultado: %{customdata[5]}<br>Meta: %{customdata[6]}<br>Situação: %{customdata[7]}<br>%{customdata[8]}<extra></extra>'))
    return _map_layout(fig, geojson, f'MUN-{layer.UF.iloc[0]}-{year}-{indicator_label}')


def _indicator_labels(data):
    labels = {}
    for row in data.itertuples():
        name = str(row.DESCRICAO)
        import re
        name = re.sub(r'^indicador\s*\d+\s*[-–—:]?\s*','',name,flags=re.I).strip()
        name = re.sub(r'^(?:Proporção|Percentual|Número) de\s+', '', name, flags=re.I)
        name = name[:1].upper()+name[1:]
        short = name if len(name) <= 32 else name[:29].rstrip()+'…'
        labels[row.INDICADOR] = str(row.INDICADOR).removeprefix('IND_')+' · '+short
    return labels


def indicator_stack(summary, order='Maior não atingimento'):
    column, ascending = {'Número do indicador':('INDICADOR',True), 'Maior cumprimento':('CUMPRIMENTO',False),
                         'Menor cumprimento':('CUMPRIMENTO',True)}.get(order,('PCT_NAO_ATINGIRAM',False))
    data = summary.sort_values([column] + ([] if column=='INDICADOR' else ['INDICADOR']),
                               ascending=[ascending] + ([] if column=='INDICADOR' else [True]),na_position='last')
    labels = _indicator_labels(data)
    custom = [[ '<br>'.join(textwrap.wrap(escape(str(r.DESCRICAO)),55)), number(r.AVALIADOS), number(r.ATINGIRAM),
                number(r.NAO_ATINGIRAM), number(r.SEM_INFORMACAO), percent(r.PCT_ATINGIRAM),
                percent(r.PCT_NAO_ATINGIRAM), percent(r.PCT_SEM_INFORMACAO), number(r.OBSERVACOES),
                number(r.SEM_REGISTRO)] for r in data.itertuples()]
    hover = ('<b>%{customdata[0]}</b><br>Municípios com situação conhecida: %{customdata[1]}'
             '<br>Meta atingida: %{customdata[2]} (%{customdata[5]})'
             '<br>Meta não atingida: %{customdata[3]} (%{customdata[6]})'
             '<br>Sem informação: %{customdata[4]} (%{customdata[7]})'
             '<br>Registros no denominador da barra: %{customdata[8]}'
             '<br>Sem registro neste indicador: %{customdata[9]}<extra></extra>')
    fig = go.Figure()
    for name,column,key in [('Meta atingida','PCT_ATINGIRAM',STATUS[0]),('Meta não atingida','PCT_NAO_ATINGIRAM',STATUS[1]),('Sem informação','PCT_SEM_INFORMACAO',STATUS[2])]:
        fig.add_trace(go.Bar(x=data[column],y=data.INDICADOR.astype(str).map(labels),orientation='h',name=name,
                             marker_color=COLORS[key],customdata=custom,hovertemplate=hover,
                             text=[percent(v) if v>=6 else '' for v in data[column]],textposition='inside',
                             textfont=dict(size=11,color='#fff' if key!=STATUS[2] else '#18344A')))
    style(fig,'Cumprimento das metas por indicador',height=max(410,min(850,125+len(data)*30)))
    fig.update_layout(barmode='stack',bargap=.2,legend=dict(y=-.1))
    fig.update_xaxes(title='Distribuição municipal por situação da meta',range=[0,100],ticksuffix='%')
    fig.update_yaxes(title=None,autorange='reversed',categoryorder='array',categoryarray=[labels[x] for x in data.INDICADOR])
    return fig


def profile_bands(distribution):
    custom = [[number(r.MUNICIPIOS),percent(r.PERCENTUAL)] for r in distribution.itertuples()]
    fig=go.Figure(go.Bar(x=distribution.MUNICIPIOS,y=distribution.FAIXA,orientation='h',
                        marker_color=[BLUE]*5+[COLORS[STATUS[2]]],customdata=custom,
                        text=[f'{number(r.MUNICIPIOS)} · {percent(r.PERCENTUAL)}' for r in distribution.itertuples()],
                        textposition='outside',cliponaxis=False,
                        hovertemplate='Faixa de metas atingidas: %{y}<br>Municípios: %{customdata[0]}<br>Participação nos municípios observados: %{customdata[1]}<extra></extra>'))
    style(fig,'Distribuição do perfil municipal',height=420)
    fig.update_yaxes(autorange='reversed',title=None)
    fig.update_xaxes(title='Municípios observados',range=[0,max(1,distribution.MUNICIPIOS.max())*1.4])
    return fig


def indicator_comparison(local, national, uf):
    fig=go.Figure()
    for data,name,color in [(national,'Brasil','#8299ad'),(local,uf,BLUE)]:
        data=data.sort_values('INDICADOR')
        custom=[[escape(str(r.DESCRICAO)),number(r.AVALIADOS),percent(r.CUMPRIMENTO)] for r in data.itertuples()]
        fig.add_trace(go.Scatter(x=data.CUMPRIMENTO,y=data.INDICADOR.astype(str).str.removeprefix('IND_'),
                                 mode='markers',name=name,marker=dict(size=9,color=color),customdata=custom,
                                 hovertemplate='%{customdata[0]}<br>Municípios avaliados: %{customdata[1]}<br>Cumprimento: %{customdata[2]}<extra>%{fullData.name}</extra>'))
    style(fig,f'{uf} · comparação com Brasil',height=420)
    fig.update_xaxes(title='Metas atingidas entre situações conhecidas',range=[0,105],ticksuffix='%')
    fig.update_yaxes(title='Indicador',autorange='reversed',type='category')
    return fig


def state_heatmap(territorial, definitions):
    data=territorial.merge(definitions[['INDICADOR','DESCRICAO']],on='INDICADOR',how='left',validate='many_to_one')
    pivot=data.pivot(index='UF',columns='INDICADOR',values='CUMPRIMENTO').sort_index().sort_index(axis=1)
    lookup={(str(r.UF),str(r.INDICADOR)):r for r in data.itertuples()}
    custom=[]
    for uf in pivot.index:
        line=[]
        for indicator in pivot.columns:
            r=lookup.get((str(uf),str(indicator)))
            line.append([escape(str(r.DESCRICAO)),number(r.AVALIADOS),number(r.ATINGIRAM),number(r.NAO_ATINGIRAM),number(r.SEM_INFORMACAO),percent(r.CUMPRIMENTO)] if r else ['Sem registro','—','—','—','—','—'])
        custom.append(line)
    fig=go.Figure(go.Heatmap(x=[str(x).removeprefix('IND_') for x in pivot.columns],y=pivot.index,z=pivot.values,
                            zmin=0,zmax=100,colorscale=[[0,'#B96750'],[.5,'#EEE9DC'],[1,'#15796F']],
                            customdata=custom,hoverongaps=True,xgap=1,ygap=1,
                            colorbar=dict(title='Cumprimento municipal',orientation='h',thickness=10,len=.7,x=.5,y=-.13,
                                          tickvals=[0,25,50,75,100],ticktext=['0%','25%','50%','75%','100%']),
                            hovertemplate='UF: %{y}<br>%{customdata[0]}<br>Municípios avaliados: %{customdata[1]}<br>Atingiram: %{customdata[2]}<br>Não atingiram: %{customdata[3]}<br>Sem informação: %{customdata[4]}<br>Cumprimento: %{customdata[5]}<extra></extra>'))
    style(fig,height=max(380,90+len(pivot)*24))
    fig.update_layout(plot_bgcolor=COLORS[STATUS[2]])
    fig.update_xaxes(title='Indicador · definição do ano selecionado',type='category',side='top',tickfont_size=11)
    fig.update_yaxes(title=None,type='category',autorange='reversed')
    return fig
