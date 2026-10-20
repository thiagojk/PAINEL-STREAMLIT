from __future__ import annotations
from html import escape
from io import BytesIO
import json
import textwrap

import pandas as pd
import streamlit as st
from src import charts
from src.data import DATA, STATUS, filter_data
from src.metrics import history, summarize, variation, single_municipality_trajectory
from src.styles import cards, note, empty_state, kpi_grid, indicator_summary, state_card_groups
from src.utils import number, percent, result, description_label

RENAME = {
    'ANO': 'Ano', 'UF': 'UF', 'COD_MUN': 'Código do município', 'NOME_MUN': 'Município', 'POP_ANO': 'População',
    'INDICADOR': 'Indicador', 'DESCRICAO': 'Descrição', 'NUM': 'Numerador', 'DEN': 'Denominador',
    'RES': 'Resultado original', 'RES_EXIBICAO': 'Resultado exibido', 'META': 'Meta na fonte',
    'ALCANCE_META': 'Alcance na fonte', 'LABEL_META': 'Regra da meta', 'SITUACAO': 'Situação',
    'UNIDADE': 'Unidade', 'MUNICIPIOS': 'Municípios', 'OBSERVACOES': 'Observações',
    'ATINGIRAM': 'Atingiram', 'NAO_ATINGIRAM': 'Não atingiram', 'SEM_INFORMACAO': 'Sem informação',
    'AVALIADOS': 'Metas avaliadas', 'CUMPRIMENTO': 'Cumprimento (%)', 'COBERTURA': 'Cobertura (%)', 'POSICAO': 'Posição',
    'SEM_REGISTRO': 'Sem registro', 'FAIXA': 'Faixa de metas atingidas',
    'CONFLITO_META': 'Conflito entre metas', 'META_NUMERICA': 'Meta numérica (%)', 'LABEL_NUM': 'Definição do numerador', 'LABEL_DEN': 'Definição do denominador',
}


def plot(fig):
    st.plotly_chart(fig, width='stretch', config={'displaylogo': False, 'locale': 'pt-BR', 'topojsonURL': 'app/static/maps/un/'})


def table(frame, height=None):
    frame = frame.copy()
    frame = frame.rename(columns=RENAME)
    # Styler muda somente a apresentação; valores numéricos continuam ordenáveis.
    formatters = {}
    result_columns = ['Numerador', 'Denominador', 'Resultado original', 'Resultado exibido', 'Meta numérica (%)']
    for column in frame.select_dtypes(include='number').columns:
        decimals = 2 if column in result_columns else 1 if '(%)' in column else 0
        suffix = '%' if '(%)' in column else ''
        formatters[column] = lambda value, decimals=decimals, suffix=suffix: number(value, decimals) + (suffix if pd.notna(value) else '')
    styled = frame.style.format(formatters, na_rep='—')
    if 'Situação' in frame:
        styled = styled.map(lambda value: f'color:{charts.COLORS[STATUS[0]]};font-weight:600' if ('atingida' in str(value).lower() and 'não' not in str(value).lower()) else f'color:{charts.COLORS[STATUS[1]]};font-weight:600' if 'não atingida' in str(value).lower() else f'background-color:{charts.COLORS[STATUS[2]]};color:{charts.TEXT_PRIMARY}', subset=['Situação'])
    st.dataframe(styled, hide_index=True, width='stretch', height=height or 'auto', column_config={
        'Descrição': st.column_config.TextColumn('Descrição', width='large'),
        'Situação': st.column_config.TextColumn('Situação', width='medium'),
    })


def empty(frame):
    if frame.empty:
        empty_state()
        return True
    return False


def overview(frame, whole, catalog, filters):
    if empty(frame): return
    cards(frame, summarize(frame))
    hist = filter_data(whole, uf=filters['uf'], municipality=filters['municipality'])
    if filters['indicator'] != 'Todos':
        sid = catalog.loc[catalog.ANO.eq(filters['year']) & catalog.INDICADOR.eq(filters['indicator']), 'SERIE']
        hist = filter_data(hist, series=sid.iloc[0]) if len(sid) else hist.iloc[0:0]
    evolution, situation = charts.align_row_figures(charts.time_line(history(hist)), charts.donut(frame))
    with st.container(key='overview_row_1'):
        a, b = st.columns([1.5, 1], gap='small')
        with a, st.container(border=True, key='chartpanel_02', height='stretch'):
            plot(evolution)
            st.caption('Mesma localidade; definições e indicadores podem variar entre anos.')
        with b, st.container(border=True, key='chartpanel_01', height='stretch'):
            plot(situation)
            row = summarize(frame).iloc[0]
            st.caption(f'Situação das metas · {number(row.AVALIADOS)} avaliadas · {number(row.SEM_INFORMACAO)} sem informação')
    summary = summarize(frame, ['INDICADOR'])
    definitions = catalog.loc[catalog.ANO.eq(filters['year']), ['INDICADOR', 'DESCRICAO']]
    summary = summary.merge(definitions, on='INDICADOR', how='left')
    summary['Rotulo'] = summary.INDICADOR.astype('string').str.replace('IND_', '', regex=False) + ' · ' + summary.DESCRICAO.str.replace(r'^Indicador \d+ [-–] ', '', regex=True).str.slice(0, 28) + '…'
    uf_chart, indicator_chart = charts.align_row_figures(
        charts.ranking(summarize(frame, ['UF']), 'UF', 'Cumprimento por UF · 10 maiores', 10),
        charts.ranking(summary, 'Rotulo', 'Cumprimento por indicador', 15, color=charts.SECONDARY))
    with st.container(key='overview_row_2'):
        a, b = st.columns(2, gap='small')
        with a, st.container(border=True, key='chartpanel_03', height='stretch'): plot(uf_chart)
        with b, st.container(border=True, key='chartpanel_04', height='stretch'): plot(indicator_chart)
    with st.expander('Como interpretar os percentuais e o histórico'):
        note('Cumprimento = metas atingidas ÷ (atingidas + não atingidas). Sem informação fica fora desse denominador. Com vários indicadores, cada par município–indicador conta como uma observação.')
        st.write('O histórico mantém o recorte geográfico. Quando há um indicador selecionado, usa a mesma definição; com todos, a composição dos indicadores varia conforme o ano.')
    if frame.INDICADOR.nunique() > 1:
        summary = summarize(frame, ['INDICADOR']).merge(catalog.loc[catalog.ANO.eq(filters['year']), ['INDICADOR', 'DESCRICAO']], on='INDICADOR', how='left')
        a, b = st.columns(2)
        with a:
            st.subheader('Maiores cumprimentos')
            table(summary.nlargest(5, 'CUMPRIMENTO')[['INDICADOR', 'DESCRICAO', 'CUMPRIMENTO', 'AVALIADOS']])
        with b:
            st.subheader('Indicadores que exigem atenção')
            table(summary.nsmallest(5, 'CUMPRIMENTO')[['INDICADOR', 'DESCRICAO', 'CUMPRIMENTO', 'AVALIADOS']])


def states(frame, whole, catalog, filters):
    from src.data import file_signature
    from src.state_analysis import state_dashboard, annual_aggregations
    from src.navigation import open_maps
    if empty(frame): return
    year, uf = filters['year'], filters['uf']
    summary, profiles, distribution, thresholds = state_dashboard(file_signature(), year, uf)
    total = summarize(frame).iloc[0]
    state_card_groups([('Municípios', number(len(profiles)), 'Presentes na base do ano', ''),
              ('Indicadores', number(len(summary)), f'Definições de {year}', ''),
              ('Metas atingidas', percent(total.CUMPRIMENTO), 'Entre situações conhecidas', 'positive'),
              ('Não atingidas', percent(total.NAO_CUMPRIMENTO), 'Entre situações conhecidas', 'negative')], thresholds)
    st.caption('Análise descritiva de situações municipais. Não representa resultado estadual do indicador nem incentivo oficial.')
    with st.container(border=True, key='chartpanel_state_stack'):
        locality = 'Brasil' if uf == 'Todos' else uf
        st.caption('Em telas estreitas, deslize o gráfico lateralmente para ver as barras completas.')
        plot(charts.indicator_stack(summary, st.session_state.get('ordem_estados','Maior não atingimento')))
        st.caption(f'{locality} · municípios observados · {year}. Barras: 100% dos registros de cada indicador, incluindo Sem informação. Ordenação padrão prioriza não atingimento.')
    st.subheader('Distribuição dos municípios por faixa')
    st.caption('Metas atingidas ÷ situações conhecidas em cada município. Aplicabilidade oficial não consta na base; perfil descritivo, sem classificação de incentivo.')
    no_assessment = int(profiles.AVALIADOS.eq(0).sum())
    st.caption(f'{number(no_assessment)} municípios sem qualquer situação conhecida: apresentados à parte, fora dos percentuais dos patamares. Sem informação não equivale a não atingimento.')
    left, right = st.columns(2, gap='small')
    with left, st.container(border=True, key='chartpanel_state_profile'):
        plot(charts.profile_bands(distribution))
    with right, st.container(border=True, key='chartpanel_state_comparison'):
        if uf == 'Todos':
            plot(charts.ranking(summarize(frame,['UF']), 'UF', 'Cumprimento municipal por UF',27))
            st.caption('Pares município–indicador com situação conhecida; não é média dos resultados municipais.')
        else:
            national = state_dashboard(file_signature(),year,'Todos')[0]
            plot(charts.indicator_comparison(summary,national,uf))
            st.caption('Comparação descritiva com Brasil por indicador; denominadores de situações conhecidas.')
    if uf == 'Todos':
        st.subheader('Mapa de calor — cumprimento das metas')
        territorial, definitions = annual_aggregations(file_signature(),year)
        with st.container(border=True,key='chartpanel_state_heatmap'):
            st.caption('Em telas estreitas, deslize o mapa de calor lateralmente para ver todos os indicadores.')
            plot(charts.state_heatmap(territorial,definitions))
        st.caption('Cada célula: percentual de municípios com situação conhecida que atingiu a meta do indicador. Cinza: sem avaliação. Escala fixa 0–100%; não é resultado estadual do indicador.')
    from src.rules import category_summary
    categories = category_summary(frame, year)
    if not categories.empty:
        st.subheader('Universais e específicos · classificação validada do período')
        plot(charts.ranking(categories, 'CATEGORIA', 'Metas atingidas por categoria', len(categories)))
    with st.expander('Denominadores, ausência e aplicabilidade'):
        st.write(f'O catálogo de {year} tem {len(summary)} indicadores. Não usamos 14 como constante histórica. O denominador municipal varia conforme as situações conhecidas disponíveis.')
        st.write('Nas barras 100%, o denominador inclui as três situações registradas. Nos percentuais de cumprimento e no heatmap, apenas atingida + não atingida. No perfil, o denominador é calculado em cada município, sem inferir aplicabilidade oficial.')
        st.write(f'Situações Sem informação: {number(total.SEM_INFORMACAO)}. Pares município–indicador sem registro, entre municípios presentes no ano e indicadores do catálogo: {number(profiles.SEM_REGISTRO.sum())}. A ausência é informada, sem transformá-la em falha ou inventar aplicabilidade.')
        st.write('Municípios ausentes da base daquele ano não são acrescentados a partir da malha geográfica. Denominadores oficiais, regras de missing e abrangência histórica não estão cadastrados; não se calcula incentivo oficial.')
    st.button('Abrir este recorte em Mapas', on_click=open_maps, args=(filters,), icon=':material/map:', key='atalho_mapas')
    st.subheader('Detalhamento por UF e indicador')
    detailed, definitions = annual_aggregations(file_signature(),year)
    if uf != 'Todos': detailed = detailed.loc[detailed.UF.eq(uf)]
    detailed = detailed.merge(definitions[['INDICADOR','DESCRICAO']],on='INDICADOR',how='left')
    detailed['ANO'] = year
    table(detailed[['UF','ANO','INDICADOR','DESCRICAO','AVALIADOS','ATINGIRAM','NAO_ATINGIRAM','SEM_INFORMACAO','CUMPRIMENTO']].rename(columns={'AVALIADOS':'Municípios avaliados','CUMPRIMENTO':'Cumprimento municipal (%)'}),510)


def detail_table(frame, catalog):
    keys = ['ANO', 'INDICADOR']
    d = frame.merge(catalog[keys + ['DESCRICAO', 'LABEL_META']], on=keys, how='left')
    d['SITUACAO'] = d.SITUACAO.astype('string').map({STATUS[0]: '✓ Meta atingida', STATUS[1]: '✕ Meta não atingida', STATUS[2]: '— Sem informação'})
    return d


def historical(frame, whole, catalog, filters):
    if empty(frame): return
    row = catalog[catalog.SERIE.eq(filters['series'])].sort_values('ANO').iloc[-1]
    indicator_summary(row, show_rule=False)
    hist = history(frame)
    change = variation(hist)
    if change:
        valid = hist.dropna(subset=['CUMPRIMENTO'])
        first, last = valid.iloc[0], valid.iloc[-1]
        kpi_grid([(f'Primeiro valor · {change["inicio"]}', percent(first.CUMPRIMENTO), 'Cumprimento entre avaliadas', ''),
                  (f'Último valor · {change["fim"]}', percent(last.CUMPRIMENTO), 'Cumprimento entre avaliadas', ''),
                  ('Variação', f'{"+" if change["pontos_percentuais"] > 0 else ""}{number(change["pontos_percentuais"], 1)} p.p.', 'Pontos percentuais',
                   'positive' if change['pontos_percentuais'] >= 0 else 'negative'),
                  ('Variação relativa', percent(change['variacao_relativa']), 'Não confundir com pontos percentuais', '')], small=True)
        st.caption('A cobertura e a composição territorial podem variar entre anos. A linha mostra os dados observados, sem previsão.')
    else:
        cards(frame, summarize(frame))
    a, b = st.columns(2)
    with a, st.container(border=True, key='chartpanel_09'): plot(charts.time_line(hist))
    with b, st.container(border=True, key='chartpanel_10'): plot(charts.counts_history(hist))
    a, b = st.columns(2)
    with a, st.container(border=True, key='chartpanel_11'):
        plot(charts.coverage(hist))
    with b, st.container(border=True, key='chartpanel_12'):
        if frame.COD_MUN.nunique() == 1:
            trajectory = single_municipality_trajectory(frame, catalog)
            plot(charts.trajectory(trajectory))
            table(trajectory[['ANO', 'RES_EXIBICAO', 'UNIDADE', 'META_NUMERICA', 'SITUACAO']])
        else:
            st.subheader('Resultado do indicador')
            st.write('Selecione um município para acompanhar o resultado e a meta numérica ao longo dos anos.')
            st.caption('Não calculamos uma média simples municipal para representar o Brasil ou uma UF. O histórico agregado usa o cumprimento das metas.')
    with st.expander('Resumo do recorte e critérios da série'):
        cards(frame, summarize(frame))
        note('A série reúne apenas definições iguais após remover número, acentos e pontuação, na mesma unidade validada. Escalas não comprovadas e mudanças de redação interrompem a série. As metas de cada ano continuam próprias daquele ano.')
    st.subheader('Valores por ano')
    table(hist[['ANO', 'MUNICIPIOS', 'ATINGIRAM', 'NAO_ATINGIRAM', 'SEM_INFORMACAO', 'AVALIADOS', 'CUMPRIMENTO']])
    with st.expander('Definições, metas e alertas por ano'):
        table(catalog[catalog.SERIE.eq(filters['series']) & catalog.ANO.isin(hist.ANO)][['ANO', 'INDICADOR', 'DESCRICAO', 'LABEL_META', 'ALERTA']])
    historical_profile_exploration(filters)


def export_frame(frame, catalog):
    d = frame.merge(catalog[['ANO', 'INDICADOR', 'DESCRICAO', 'LABEL_META']], on=['ANO', 'INDICADOR'], how='left')
    return d[['ANO', 'UF', 'COD_MUN', 'NOME_MUN', 'POP_ANO', 'INDICADOR', 'DESCRICAO', 'NUM', 'DEN', 'RES', 'RES_EXIBICAO', 'UNIDADE', 'META', 'ALCANCE_META', 'LABEL_META', 'SITUACAO', 'CONFLITO_META']].rename(columns=RENAME)


def data_table(frame, whole, catalog, filters):
    with st.sidebar:
        situation = st.multiselect('Situação da meta', STATUS, default=STATUS, key='situacao')
    selected = frame[frame.SITUACAO.isin(situation)]
    if empty(selected): return
    st.caption(f'{number(len(selected))} observações no resultado filtrado. Downloads incluem todo esse recorte.')
    with st.sidebar:
        page_size = st.selectbox('Linhas por página', [100, 500, 1000], key='linhas_por_pagina')
    pages = max(1, (len(selected) + page_size - 1) // page_size)
    with st.sidebar:
        if st.session_state.get('pagina_tabela', 1) > pages:
            st.session_state['pagina_tabela'] = 1
        page = st.number_input('Página da tabela', min_value=1, max_value=pages, value=1, step=1, key='pagina_tabela')
    begin = (page - 1) * page_size
    display = export_frame(selected.iloc[begin:begin + page_size], catalog)
    decimals = {'Numerador', 'Denominador', 'Resultado original', 'Resultado exibido'}
    formats = {c: (lambda value, places=2 if c in decimals else 0: number(value, places))
               for c in display.select_dtypes(include='number').columns}
    st.dataframe(display.style.format(formats, na_rep='—'), hide_index=True, width='stretch', height=510)
    st.caption(f'Página {page} de {pages}. A ordenação do componente aplica-se à página exibida.')
    a, b = st.columns(2)
    with a:
        if st.button('Preparar CSV do recorte', width='stretch'):
            csv = export_frame(selected, catalog).to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button('Baixar CSV', csv, file_name='pqavs_recorte.csv', mime='text/csv', width='stretch')
    with b:
        if len(selected) <= 100_000:
            if st.button('Preparar Excel do recorte', width='stretch'):
                buffer = BytesIO()
                export_frame(selected, catalog).to_excel(buffer, index=False, engine='openpyxl')
                st.download_button('Baixar XLSX', buffer.getvalue(), file_name='pqavs_recorte.xlsx',
                                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', width='stretch')
        else:
            st.caption('Para XLSX, reduza o recorte a até 100 mil linhas. CSV permanece disponível.')


def about(frame, whole, catalog, filters):
    metadata = json.loads((DATA / 'metadata.json').read_text(encoding='utf-8'))
    st.subheader('Dados claros. Decisões informadas.')
    st.write('O painel apresenta os indicadores e o cumprimento das metas do Programa de Qualificação das Ações de Vigilância em Saúde (PQAVS), por município, UF e ano.')
    a, b = st.columns(2)
    with a, st.container(border=True, key='chartpanel_13'):
        st.subheader('Fonte e abrangência')
        st.write(f'Arquivo fornecido: **{metadata["fonte_arquivo"]}**. Descrições e metas vêm da aba “Indicadores e Metas por Ano”.')
        st.write(f'Observações: **{number(metadata["observacoes"])}** · Registros município–ano: **{number(metadata["registros_municipio_ano"])}** · Período: **{min(metadata["anos"])}–{max(metadata["anos"])}**.')
        st.write('A data de atualização da fonte e a procedência institucional do arquivo não foram informadas. A data no cabeçalho corresponde à preparação dos dados.')
        st.caption(f'SHA-256 da fonte: {metadata["fonte_sha256"]}')
    with b, st.container(border=True, key='chartpanel_14'):
        st.subheader('Como ler o cumprimento')
        st.write('**Metas atingidas ÷ metas avaliadas × 100**. Avaliadas = atingidas + não atingidas. Ausentes não entram no denominador; são apresentados separadamente.')
        st.write('Um indicador/ano: percentual de municípios que atingiram a meta. Vários indicadores: percentual de pares município–indicador. Não representa a fração de municípios que atingiu todas as metas.')
        st.write('O ranking ordena esse cumprimento, com posições iguais para empates. Não pressupõe que resultados mais altos sejam sempre melhores.')
    st.subheader('Como o PQA-VS avalia os estados')
    st.write('A avaliação estadual considera a proporção de municípios que alcança determinada proporção dos indicadores, conforme as regras vigentes no período. Isso difere da distribuição descritiva de cumprimento apresentada neste painel.')
    from src.rules import version_for_year
    reference = version_for_year(2025)
    st.dataframe(pd.DataFrame([{'Municípios do território':f'{t["municipal_share"]}%', 'Metas dos indicadores':f'≥{t["indicator_share"]}%', 'Faixa de incentivo':f'{t["incentive"]}%'} for t in reference['state_incentive']]),hide_index=True,width='stretch')
    st.info('As metas e indicadores da configuração apresentada na cartilha oficial utilizada como referência são aplicáveis a partir de 2025. A análise histórica respeita as definições vigentes em cada período e os dados disponíveis.')
    st.write('A referência atual apresenta 14 indicadores, sendo 7 universais e 7 específicos. Não atribuímos essas categorias aos indicadores de 2013–2021 apenas por número. Não há cadastro operacional completo de aplicabilidade ou incentivo para os anos da base.')
    st.caption('Referência metodológica informada: Ministério da Saúde · Programa de Qualificação das Ações de Vigilância em Saúde — PQA-VS · cartilha atualizada a partir de 2025 · Portaria GM/MS nº 6.878/2025. A transcrição fornecida não substitui a documentação completa das regras de cada período.')
    st.write('Adesão estadual: a referência informa pelo menos 60% dos municípios com adesão formalizada. Essa é uma regra de adesão, distinta de desempenho e cumprimento; a base não contém dados de adesão e não gera esse indicador.')
    st.subheader('Regras de tratamento')
    st.markdown('''- `ALCANCE_META` com 0 ou 1 tem prioridade. Sem flag válida, usamos somente “Sim”/“Não” de `META`. Valor 0 isolado em `META` não é interpretado como “Não”.
- Situações: **Atingida**, **Não atingida**, **Sem informação**. Resultado numérico ausente não invalida uma situação explicitamente registrada na fonte.
- `NULL`, `NA`, `N/A`, espaços e campos vazios são ausentes. Valores não numéricos em campos numéricos tornam-se ausentes; os totais constam na auditoria.
- Códigos municipais são texto, sem criar dígitos verificadores. O arquivo usa códigos de seis dígitos.
- Valores originais de resultado, numerador, denominador e meta são preservados nos dados tratados e nas exportações. A exibição em % só ocorre com evidência de escala em NUM/DEN e definição percentual.
- Não há média simples de percentuais para representar Brasil/UF. Não publicamos razão agregada sem comprovação de compatibilidade estatística.
- Séries históricas usam a descrição normalizada e a unidade validada; escalas originais não comprovadas ficam isoladas por ano, sem depender da numeração do indicador. Redações diferentes são separadas de forma conservadora. Metas e cobertura podem variar entre anos.
- A linha de meta só aparece quando o dicionário fornece uma regra percentual simples e a unidade foi validada. Não recalculamos o alcance a partir dessa linha.''')
    st.subheader('Limitações encontradas na fonte')
    st.warning('O dicionário cita 2022, mas as abas de observações terminam em 2021. Nenhum dado de 2022 foi criado. O indicador 15 só tem observações em 2016–2017. Em 2020–2021, o indicador 8 não tem resultado numérico, mas possui alcance da meta informado.')
    st.info('A partir de 2018, a numeração de vários indicadores muda. O indicador 6 tem descrição de proporção e rótulo de meta “50 semanas” (também há conflito em 2013); essa inconsistência permanece sinalizada, sem correção presumida. Há valores extremos e denominadores zero na fonte, preservados para auditoria.')
    st.warning('Em 2013, o indicador 8 concentra 4.784 divergências: ALCANCE_META=1 e META=Não. A fonte não explica a divergência. Os dois campos e o sinalizador de conflito estão disponíveis na exportação.')
    st.caption(f'Conflitos entre flag e Sim/Não: {number(metadata["conflitos_meta"])}. Resultados numéricos ausentes: {number(metadata["resultados_ausentes"])}. Ausência de casos não foi reinterpretada como sucesso.')
    st.subheader('Situação e grau de alcance da meta')
    st.write('Situação da meta indica se a meta foi atingida segundo o registro do indicador/período: prioridade de ALCANCE_META e fallback Sim/Não. Grau de alcance é uma medida contínua complementar de proximidade, disponível apenas com transformação metodologicamente válida. Não substitui a situação oficial.')
    st.write('Nos municípios com regra percentual crescente explícita e escala validada: grau real = 100 × resultado percentual ÷ meta positiva anual. O mapa limita a cor a 100%, preservando resultado, meta e grau real no tooltip. Numerador e denominador precisam sustentar o resultado; ausências, denominadores não positivos e inconsistências ficam cinza, sem imputar zero. Atingir 100% na razão não altera a classificação da fonte.')
    st.write('Metas inversas, manutenção de zero, regras compostas, escalas não comprovadas e variações sem baseline identificado não recebem fórmula presumida. O mapa de UFs continua mostrando % dos municípios que atingiram a meta; não é grau estadual nem média dos graus municipais.')
    st.write('O histórico conserva série conceitual, regras anuais e escala 0–100% compartilhada. Metas diferentes são informadas em cada tooltip; proximidade relativa não equivale a resultado absoluto constante. Transformações incompatíveis bloqueiam a comparação e anos sem suporte exibem indisponibilidade.')
    with st.expander('Disponibilidade do grau de alcance por indicador e ano'):
        from src.rules import load_versions
        records = [r for v in load_versions() for r in v.get('progress_rules',[])]
        table(pd.DataFrame([{'Ano':r['year'],'Indicador':r['number'],'Descrição':r['description'],'Meta':r['target_label'],'Disponível':'Sim' if r['supports_progress_map'] else 'Não','Justificativa':r['justification']} for r in records]))
    st.subheader('Semântica das cores')
    st.write('Azul petróleo e azul profundo estruturam a interface. Teal = meta atingida; terracota = meta não atingida; cinza = sem informação ou grau indisponível, conforme a legenda. Escalas sequenciais claras → escuras representam valores crescentes, sem oposição vermelho–verde. Séries temporais também usam marcadores e traçados distintos.')
    st.subheader('Análise geográfica')
    from src.geography import map_metadata
    geo = map_metadata()
    st.write('O mapa estadual mostra o percentual de municípios que atingiram a meta: atingiram ÷ (atingiram + não atingiram). Sem informação fica fora do denominador. Não há média simples de resultados municipais.')
    st.write('O mapa municipal usa ✓ Meta atingida (verde azulado), ✕ Meta não atingida (laranja discreto) e — Sem informação (cinza). Um território da malha sem observação também aparece cinza, com aviso próprio; ele não é acrescentado à base ou aos totais.')
    st.write('Geometrias locais de origem IBGE, redistribuídas no repositório público luizpedone/municipal-brazilian-geodata, sob licença MIT do espelho. Não há downloads em tempo de execução. A revisão e os hashes estão no manifesto dos mapas.')
    st.write('Relacionamento: o GeoJSON tem código municipal de sete dígitos; os seis primeiros são comparados ao COD_MUN textual da fonte, junto com a UF. A relação foi validada como única, sem calcular dígitos ou alterar os dados.')
    report = geo['correspondencia']
    st.caption(f'Cobertura: {number(report["associados"])} de {number(report["municipios_base"])} municípios ({percent(report["taxa_percentual"])}); não associados: {number(report["nao_associados"])}. Revisão do espelho: {geo["revisao"]}.')
    st.info('A malha é estática e foi simplificada para visualização. O ano específico da malha não está declarado no arquivo do espelho; seus limites não devem ser interpretados como limites históricos de cada ano analisado. Não usar para medição de áreas, limites legais ou georreferenciamento de precisão.')
    if report['municipios_nao_associados']:
        table(pd.DataFrame(report['municipios_nao_associados']))
    with st.expander('Indicadores disponíveis por ano'):
        table(catalog[['ANO', 'INDICADOR', 'DESCRICAO', 'LABEL_META', 'UNIDADE', 'ALERTA']])
    with st.expander('Auditoria do processamento'):
        st.json({k: v for k, v in metadata.items() if k != 'auditoria_abas'})
    st.download_button('Baixar metadados e auditoria', (DATA / 'metadata.json').read_bytes(), 'metadata_pqavs.json', 'application/json')


def map_plot(fig, continuous=False):
    """Altura nativa stretch: o canvas acompanha a área disponível, sem JS."""
    fig.update_layout(height=None, autosize=True, margin=dict(l=8,r=8,t=8,b=42 if continuous else 8))
    if continuous:
        fig.update_traces(colorbar=dict(y=0,yanchor='top',title=dict(side='top')),selector=dict(type='choropleth'))
    st.plotly_chart(fig,width='stretch',height='stretch',config={'displaylogo':False,'locale':'pt-BR','topojsonURL':'app/static/maps/un/'})


def maps(frame, whole, catalog, filters):
    from src.geography import load_geojson, map_signature, state_summary, municipality_layer
    from src.target_progress import progress_rule, progress_layer, progress_signature
    if empty(frame): return
    entry=catalog.loc[catalog.ANO.eq(filters['year']) & catalog.INDICADOR.eq(filters['indicator'])]
    if entry.empty:
        empty_state('Este indicador não está disponível no ano selecionado.'); return
    row=entry.iloc[0]
    progress=st.session_state.get('map_mode','Situação da meta')=='Grau de alcance (%)'
    comparing=st.session_state.get('mapa_historico',False)
    nationwide=filters['uf']=='Todos'
    total=summarize(frame).iloc[0]
    kpi_grid([('Municípios avaliados',number(total.AVALIADOS),f'{number(total.SEM_INFORMACAO)} sem informação',''),
              ('Atingiram a meta',number(total.ATINGIRAM),'✓ Meta atingida','positive'),
              ('Não atingiram',number(total.NAO_ATINGIRAM),'✕ Meta não atingida','negative'),
              ('Cumprimento',percent(total.CUMPRIMENTO),'Entre municípios avaliados','')],small=True)
    with st.sidebar:
        help_panel=st.expander('Ajuda e metodologia dos mapas')
        with help_panel:
            st.write(description_label(row));st.write(row.LABEL_META)
            st.write('Situação usa ALCANCE_META, com fallback Sim/Não. Grau é proximidade complementar, quando validada: 100 × resultado percentual ÷ meta positiva anual. Cor limitada a 100%; valor real no tooltip. A situação da fonte não é recalculada.')
            if nationwide:
                st.info('Brasil / UFs: % dos municípios que atingiram. Não há situação oficial única nem resultado estadual validado; não se calcula média dos graus municipais.')
            st.write('Cinza: sem informação/avaliação em Situação ou grau indisponível em Grau; não significa zero. Territórios sem observação não entram nos denominadores. Malha IBGE estática e simplificada, sem representar mudanças históricas de limites. Consulte Sobre para fontes e cobertura.')
            st.write('Histórico: mesma série conceitual e transformação compatível; metas anuais podem variar. Escala compartilhada 0–100%. Até seis anos. Anos sem suporte permanecem explicitamente indisponíveis.')
            st.write('Ranking: cumprimento das situações conhecidas, independente do modo. Empates não indicam diferença de desempenho; resultados municipais não são promediados.')
            if frame.CONFLITO_META.any():st.warning(f'{number(frame.CONFLITO_META.sum())} conflitos META/ALCANCE_META; prioridade da flag preservada.')
            if row.ALERTA:st.warning(row.ALERTA)
            selected=catalog.loc[catalog.SERIE.eq(row.SERIE)]
            table(selected[['ANO','INDICADOR','LABEL_META','ALERTA']],240)
        with st.expander('Dados territoriais e definição'):
            table(detail_table(frame,catalog)[['COD_MUN','NOME_MUN','RES_EXIBICAO','UNIDADE','LABEL_META','SITUACAO']],260)
    with st.container(key=f'map_viewport_{"history" if comparing else "current"}_{progress}',height='stretch'):
        if comparing:
            territorial_history(catalog,filters,progress=progress,help_panel=help_panel)
        else:
            with st.container(key='map_current',height='stretch'):
                a,b=st.columns([2.1,1],gap='small')
                label='<br>'.join(escape(line) for line in textwrap.wrap(description_label(row),55))
                geometry=load_geojson(map_signature(None if nationwide else filters['uf']))
                with a,st.container(border=True,key='map_main',height='stretch'):
                    if nationwide:
                        st.caption('% dos municípios da UF que atingiram · não é grau estadual')
                        map_plot(charts.state_map(state_summary(frame),geometry,filters['year'],label),True)
                    else:
                        layer=municipality_layer(frame,geometry)
                        with help_panel:
                            st.caption(f'{number((~layer.TEM_OBSERVACAO).sum())} territórios da malha sem observação no recorte; fora dos denominadores.')
                            missing=frame.loc[~frame.COD_MUN.isin(layer.COD_MUN),['COD_MUN','NOME_MUN']]
                            if len(missing):
                                st.warning(f'{number(len(missing))} municípios sem geometria. Permanecem nos totais e no ranking.');table(missing)
                        if progress:
                            rule=progress_rule(row)
                            if rule and rule['supports_progress_map']:
                                prepared=progress_layer(layer,row,progress_signature())
                                with help_panel:st.caption(f'{number(prepared.GRAU_VALIDO.sum())} municípios com grau calculável; {number((~prepared.GRAU_VALIDO).sum())} sem grau válido.')
                                map_plot(charts.target_progress_map(prepared,geometry,filters['year'],label,str(row.LABEL_META)),True)
                            else:
                                empty_state('Grau percentual de alcance não disponível para este indicador.','Consulte Situação da meta. '+(rule or {}).get('justification','Regra não cadastrada.'))
                        else:
                            map_plot(charts.municipality_map(layer,geometry,filters['year'],label,str(row.LABEL_META)))
                            map_legend()
                with b,st.container(border=True,key='map_ranking',height='stretch'):
                    fig=charts.ranking(state_summary(frame),'UF','Ranking de cumprimento por UF',27) if nationwide else charts.ranking(summarize(frame,['NOME_MUN']),'NOME_MUN','Municípios com maior cumprimento',15)
                    fig.update_layout(height=None,autosize=True,margin=dict(l=4,r=44,t=54,b=38))
                    fig.update_yaxes(tickfont_size=10)
                    fig.update_xaxes(title='Cumprimento (%)')
                    st.plotly_chart(fig,width='stretch',height='stretch',config={'displaylogo':False,'locale':'pt-BR'})


def map_legend():
    st.html('<div class="map-legend">'+''.join(f'<span><i style="background:{charts.MAP_STATUS_COLORS[status]}"></i>{text}</span>' for status,text in zip(STATUS,['✓ Meta atingida','✕ Meta não atingida','— Sem informação']))+'</div>')


def territorial_history(catalog,filters,progress=False,help_panel=None):
    from src.data import file_signature
    from src.territorial_history import prepare_history
    from src.geography import map_signature,load_geojson
    from src.target_progress import progress_rule,progress_layer,progress_signature,continuous_compatibility
    entry=catalog.loc[catalog.ANO.eq(filters['year']) & catalog.INDICADOR.eq(filters['indicator'])].iloc[0]
    years=st.session_state.get(f'mapa_anos_{entry.SERIE}',[])
    with st.container(key='map_comparison',height='stretch'):
        st.markdown('**Evolução territorial** · '+('Grau de alcance (%)' if progress else 'Situação da meta'))
        if not years:
            st.info('Selecione até 6 anos para comparação territorial na sidebar.');return
        nationwide=filters['uf']=='Todos'
        if nationwide or progress:
            st.html('<div class="shared-scale"><b>'+('% dos municípios que atingiram · não é grau estadual' if nationwide else 'Grau de alcance da meta')+'</b><div></div><span>0%</span><span>50%</span><span>100%</span></div>')
        else:map_legend()
        if progress and not nationwide:
            entries=catalog.loc[catalog.SERIE.eq(entry.SERIE) & catalog.ANO.isin(years)]
            supported=entries.loc[entries.apply(lambda r:bool((progress_rule(r) or {}).get('supports_progress_map')),axis=1)]
            if not supported.empty and not continuous_compatibility(supported)[0]:
                st.warning('Transformações incompatíveis para comparação contínua.');return
        signature=map_signature(None if nationwide else filters['uf'])
        geometry=load_geojson(signature)
        prepared=prepare_history(file_signature(),entry.SERIE,filters['uf'],tuple(years),signature)
        with st.container(key='map_history_grid',height='stretch'):
            columns=st.columns(len(prepared),gap='small')
            for column,item in zip(columns,prepared):
                with column,st.container(border=True,height='stretch',key=f'map_year_{item["year"]}'):
                    row=item['entry']
                    st.markdown(f'**{item["year"]}** · {"Brasil" if nationwide else filters["uf"]} · {row.INDICADOR.replace("IND_","")}')
                    if help_panel is not None and not item['empty']:
                        with help_panel:
                            if item['conflicts']:st.warning(f'{item["year"]}: {number(item["conflicts"])} conflitos META/ALCANCE_META; prioridade da flag preservada.')
                            if not nationwide:st.caption(f'{item["year"]}: {number((~item["data"].TEM_OBSERVACAO).sum())} territórios sem observação; fora dos denominadores.')
                    if item['empty']:
                        st.info('Sem dados disponíveis.');continue
                    label='<br>'.join(escape(line) for line in textwrap.wrap(description_label(row),55))
                    if nationwide:fig=charts.state_map(item['data'],geometry,item['year'],label)
                    elif progress:
                        rule=progress_rule(row)
                        if not rule or not rule['supports_progress_map']:
                            st.info('Grau percentual de alcance não disponível para este indicador. Consulte Situação da meta.');continue
                        fig=charts.target_progress_map(progress_layer(item['data'],row,progress_signature()),geometry,item['year'],label,str(row.LABEL_META))
                    else:fig=charts.municipality_map(item['data'],geometry,item['year'],label,str(row.LABEL_META))
                    fig.update_traces(showscale=False)
                    map_plot(fig)


def historical_profile_exploration(filters):
    from src.data import file_signature
    from src.profile_history import historical_exploration
    enabled = st.session_state.get('hist_explorar',False)
    with st.expander('Explorar evolução dos patamares e persistência', expanded=enabled):
        if not enabled:
            st.caption('Ative Explorar perfil e persistência na sidebar para carregar estas análises.'); return
        if filters['municipality'] not in ['Todos',None]:
            st.info('Estas análises são coletivas por Brasil ou UF. Selecione Todos os municípios para explorar; a trajetória municipal permanece disponível acima.'); return
        period = st.session_state['hist_perfil_periodo']
        evolution,coverage,series,excluded = historical_exploration(file_signature(),filters['uf'],period)
        st.warning('Perfil descritivo das metas com situação conhecida em cada período. Catálogo, metas e conjunto municipal podem mudar. Não representa incentivo oficial, painel de indicadores fixos ou efeito causal do programa.')
        st.caption(f'Período próprio: {period[0]}–{period[1]} · território do filtro. A evolução usa todas as metas de cada ano, independentemente do indicador selecionado para os gráficos acima.')
        st.subheader('Evolução do perfil de alcance municipal')
        with st.container(border=True,key='chartpanel_profile_evolution'):
            plot(charts.profile_evolution(evolution))
        st.caption('Cada patamar: percentual de municípios com ao menos uma situação conhecida que atingiu aquela proporção dessas metas. Sem avaliação fica à parte. As linhas são interrompidas quando muda o catálogo ou o conjunto municipal.')
        with st.expander('Conferir denominadores e mudanças por ano'):
            data = coverage.rename(columns={'MUNICIPIOS_OBSERVADOS':'Municípios observados','MUNICIPIOS_AVALIADOS':'Municípios com avaliação',
                       'SEM_AVALIACAO':'Municípios sem avaliação','INDICADORES_CATALOGO':'Indicadores no catálogo',
                       'AVALIACOES':'Situações conhecidas','CATALOGO_MUDOU':'Mudança de catálogo/metas',
                       'COORTE_MUDOU':'Mudança do conjunto municipal'})
            table(data)
        st.subheader('Cumprimento por série histórica e ano')
        st.caption('Somente séries analíticas compatíveis com ao menos três anos observados. Anos sem avaliação ficam cinza; escalas originais isoladas por ano não são unidas. Não há classificação de tendência ou significância estatística.')
        if series.empty:
            st.info('Nenhuma série com pelo menos três anos de avaliação neste território/período.')
        else:
            with st.container(border=True,key='chartpanel_persistence'):
                st.caption('Em telas estreitas, deslize a matriz lateralmente para consultar todos os anos.')
                plot(charts.temporal_heatmap(series,sorted(coverage.ANO.tolist())))
            st.caption('Linhas ordenadas pelo maior cumprimento observado, do menor para o maior: isso facilita localizar séries que se mantiveram em níveis baixos sem inferir tendência por primeiro/último ano.')
        st.caption(f'{excluded} séries com menos de três anos observados ou definição anual ambígua foram omitidas desta matriz. A análise individual dessas séries permanece no seletor principal.')
