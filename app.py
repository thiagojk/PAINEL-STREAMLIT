"""Ponto de entrada único: streamlit run app.py."""
import json
from html import escape
import logging

import streamlit as st
from src.data import DATA, file_signature, filter_data, load_data
from src.filters import global_filters, map_filters
from src.styles import apply_styles, header, page_heading
from src.navigation import navigation
from src import views

st.set_page_config(page_title='PQAVS | Painel de Indicadores', page_icon='assets/icon.svg', layout='wide', initial_sidebar_state='collapsed')
apply_styles()
PAGES = {
    'Visão Geral': (views.overview, 'Painel de Indicadores e Metas', 'Uma visão integrada do cumprimento das metas da vigilância em saúde.'),
    'Estados': (views.states, 'Desempenho dos estados', 'Compare o cumprimento das metas nas Unidades da Federação.'),
    'Municípios': (views.municipalities, 'Olhar sobre os municípios', 'Consulte a ficha municipal e identifique prioridades no território.'),
    'Indicadores': (views.indicators, 'Cada indicador, em detalhe', 'Definições, resultados e metas conforme o dicionário de cada ano.'),
    'Mapas': (views.maps, 'Análise geográfica', 'Do Brasil ao município: veja onde as metas foram atingidas.'),
    'Análise Histórica': (views.historical, 'O tempo revela a trajetória', 'Acompanhe o cumprimento das metas e a cobertura da avaliação ao longo dos anos.'),
    'Comparações': (views.comparisons, 'Territórios em perspectiva', 'Compare até cinco localidades em uma mesma definição do indicador.'),
    'Tabela de Dados': (views.data_table, 'Explore os dados', 'Consulte e exporte exatamente o recorte que você precisa.'),
    'Sobre / Metodologia': (views.about, 'Sobre o painel', 'Fonte, critérios de cálculo e limites para interpretar os resultados.'),
}
try:
    signature = file_signature()
    base, catalog = load_data(signature)
    metadata = json.loads((DATA / 'metadata.json').read_text(encoding='utf-8'))
except (OSError, ValueError, KeyError):
    st.error('A base de dados está indisponível ou não pôde ser lida. Prepare os arquivos conforme as instruções do README e tente novamente.')
    st.stop()
header(metadata)
page = navigation()
fn, title, subtitle = PAGES[page]
page_heading(title, subtitle)
is_history = page in ['Análise Histórica', 'Comparações']
if page == 'Sobre / Metodologia':
    filters, period = dict(year=None, uf=None, municipality=None, indicator=None, series=None), None
elif page == 'Mapas':
    filters, period = map_filters(base, catalog)
else:
    filters, period = global_filters(base, catalog, historical=is_history, required_indicator=page == 'Indicadores')
frame = filter_data(base, **filters)
if period:
    frame = frame[frame.ANO.between(*period)]
locality = 'Brasil' if filters['uf'] in ['Todos', None] else filters['uf']
if filters['municipality'] not in ['Todos', None] and not frame.empty:
    locality = f'{frame.NOME_MUN.iloc[0]} · {frame.UF.iloc[0]}'
if page != 'Sobre / Metodologia':
    scope = f'{period[0]}–{period[1]}' if period else str(filters['year'])
    st.html(f'<div class="context">RECORTE ATUAL &nbsp; / &nbsp; <b>{escape(str(locality))}</b> &nbsp; / &nbsp; {scope}</div>')
try:
    fn(frame, base, catalog, filters)
except Exception:
    logging.exception('Falha na página %s', page)
    st.error('Não foi possível concluir esta análise. Tente outro recorte; se persistir, consulte os logs da aplicação.')
st.html('<div class="footer">PQAVS · Painel de Indicadores e Metas &nbsp; | &nbsp; Consulta pública · Consulte os critérios em Sobre / Metodologia.</div>')
