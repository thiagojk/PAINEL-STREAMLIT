"""Plotly com estilo comum e tooltips em português."""
import textwrap
import plotly.express as px
import plotly.graph_objects as go
from src.data import STATUS

COLORS = {'Atingida': '#14887D', 'Não atingida': '#CA785C', 'Sem informação': '#ACB9C8'}
BLUE = '#206A8A'
PALETTE = ['#137C8B', '#4469A0', '#A9794D', '#836BA5', '#648654']


def style(fig, title=None, height=355, percent_axis=False):
    fig.update_layout(
        title=dict(text='<br>'.join(textwrap.wrap(title, 36)) if title else '', font=dict(size=16, color='#18344A'), x=0),
        font=dict(family='Arial, sans-serif', size=12, color='#526578'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=12, r=16, t=(64 if title and len(title) > 36 else 46) if title else 16, b=16), height=height,
        legend=dict(title=None, orientation='h', y=-.20, x=0),
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
                          textinfo='none', sort=False,
                          hovertemplate='%{label}<br>Registros: %{value:,.0f}<br>Participação no total: %{percent}<extra></extra>'))
    return style(fig, height=310)


def ranking(summary, group, title, limit=27):
    table = summary.dropna(subset=['CUMPRIMENTO']).sort_values('CUMPRIMENTO', ascending=False).head(limit).sort_values('CUMPRIMENTO')
    fig = px.bar(table, x='CUMPRIMENTO', y=group, orientation='h',
                 custom_data=['ATINGIRAM', 'NAO_ATINGIRAM', 'AVALIADOS', 'SEM_INFORMACAO'] + (['DESCRICAO'] if 'DESCRICAO' in table else []),
                 color_discrete_sequence=[BLUE])
    fig.update_traces(marker_cornerradius=4, hovertemplate=(
        '%{y}<br>Cumprimento: %{x:.1f}%<br>Atingiram: %{customdata[0]:,.0f}'
        '<br>Não atingiram: %{customdata[1]:,.0f}<br>Avaliados: %{customdata[2]:,.0f}'
        '<br>Sem informação: %{customdata[3]:,.0f}' + ('<br>%{customdata[4]}' if 'DESCRICAO' in table else '') + '<extra></extra>'))
    fig.update_xaxes(title='% de metas atingidas entre avaliadas', ticksuffix='%', range=[0, 105])
    fig.update_yaxes(title=None, categoryorder='array', categoryarray=table[group].tolist())
    return style(fig, title, max(320, len(table) * 23 + 85))


def time_line(summary, title='Evolução do cumprimento das metas', color=None):
    fig = px.line(summary, x='ANO', y='CUMPRIMENTO', color=color, markers=True,
                  color_discrete_sequence=PALETTE,
                  custom_data=['ATINGIRAM', 'NAO_ATINGIRAM', 'AVALIADOS', 'SEM_INFORMACAO'])
    fig.update_traces(line_width=3, marker_size=7,
                      hovertemplate='Ano: %{x}<br>Cumprimento: %{y:.1f}%<br>Atingiram: %{customdata[0]:,.0f}<br>Não atingiram: %{customdata[1]:,.0f}<br>Avaliados: %{customdata[2]:,.0f}<br>Sem informação: %{customdata[3]:,.0f}<extra>%{fullData.name}</extra>')
    fig.update_xaxes(title=None, dtick=1)
    fig.update_yaxes(title='% de metas atingidas', range=[0, 105])
    return style(fig, title, percent_axis=True)


def counts_history(summary):
    data = summary.rename(columns={'ATINGIRAM': 'Atingida', 'NAO_ATINGIRAM': 'Não atingida', 'SEM_INFORMACAO': 'Sem informação'})
    fig = px.bar(data, x='ANO', y=STATUS, color_discrete_map=COLORS, labels={'value': 'Registros', 'variable': 'Situação'}, barmode='stack')
    fig.update_traces(hovertemplate='Ano: %{x}<br>Registros: %{y:,.0f}<extra>%{fullData.name}</extra>')
    fig.update_xaxes(title=None, dtick=1)
    return style(fig, 'Situação das metas ao longo do tempo')


def distribution(frame):
    units = frame.UNIDADE.unique()
    fig = px.histogram(frame, x='RES_EXIBICAO', color='SITUACAO', nbins=35,
                       color_discrete_map=COLORS, category_orders={'SITUACAO': STATUS},
                       labels={'RES_EXIBICAO': 'Resultado (%)' if len(units) == 1 and units[0] == '%' else 'Resultado na escala original', 'SITUACAO': 'Situação'})
    fig.update_traces(hovertemplate='Resultado: %{x}<br>Municípios: %{y}<extra>%{fullData.name}</extra>')
    fig.update_yaxes(title='Municípios')
    return style(fig, 'Distribuição dos resultados municipais')


def trajectory(frame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=frame.ANO, y=frame.RES_EXIBICAO, mode='lines+markers', name='Resultado',
                             line=dict(color=BLUE, width=3), customdata=frame[['SITUACAO']],
                             hovertemplate='Ano: %{x}<br>Resultado: %{y:.2f}<br>Situação: %{customdata[0]}<extra></extra>'))
    if frame.META_NUMERICA.notna().any():
        fig.add_trace(go.Scatter(x=frame.ANO, y=frame.META_NUMERICA, mode='lines', name='Meta do ano',
                                 line=dict(color='#CA785C', dash='dash'), hovertemplate='Ano: %{x}<br>Meta: %{y:.1f}%<extra></extra>'))
    fig.update_xaxes(title=None, dtick=1)
    fig.update_yaxes(title='Resultado (%)' if frame.UNIDADE.iloc[0] == '%' else 'Resultado na escala original')
    return style(fig, 'Trajetória do resultado municipal')
