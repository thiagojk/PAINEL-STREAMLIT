from __future__ import annotations
from html import escape
from io import BytesIO
import json

import pandas as pd
import streamlit as st
from src import charts
from src.data import DATA, STATUS, filter_data
from src.metrics import history, summarize, variation, municipal_ranking, single_municipality_trajectory
from src.styles import cards, note
from src.utils import number, percent, result, description_label

RENAME = {
    'ANO': 'Ano', 'UF': 'UF', 'COD_MUN': 'Código do município', 'NOME_MUN': 'Município', 'POP_ANO': 'População',
    'INDICADOR': 'Indicador', 'DESCRICAO': 'Descrição', 'NUM': 'Numerador', 'DEN': 'Denominador',
    'RES': 'Resultado original', 'RES_EXIBICAO': 'Resultado exibido', 'META': 'Meta na fonte',
    'ALCANCE_META': 'Alcance na fonte', 'LABEL_META': 'Regra da meta', 'SITUACAO': 'Situação',
    'UNIDADE': 'Unidade', 'MUNICIPIOS': 'Municípios', 'OBSERVACOES': 'Observações',
    'ATINGIRAM': 'Atingiram', 'NAO_ATINGIRAM': 'Não atingiram', 'SEM_INFORMACAO': 'Sem informação',
    'AVALIADOS': 'Metas avaliadas', 'CUMPRIMENTO': 'Cumprimento (%)', 'COBERTURA': 'Cobertura (%)', 'POSICAO': 'Posição',
    'CONFLITO_META': 'Conflito entre metas', 'META_NUMERICA': 'Meta numérica (%)', 'LABEL_NUM': 'Definição do numerador', 'LABEL_DEN': 'Definição do denominador',
}


def plot(fig):
    st.plotly_chart(fig, width='stretch', config={'displaylogo': False, 'locale': 'pt-BR'})


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
    st.dataframe(styled, hide_index=True, width='stretch', height=height or 'auto', column_config={
        'Descrição': st.column_config.TextColumn('Descrição', width='large'),
        'Situação': st.column_config.TextColumn('Situação', width='medium'),
    })


def empty(frame):
    if frame.empty:
        st.info('Não há dados disponíveis para esta combinação de filtros.')
        return True
    return False


def overview(frame, whole, catalog, filters):
    if empty(frame): return
    cards(frame, summarize(frame))
    note('Cumprimento = metas atingidas ÷ (atingidas + não atingidas). Sem informação fica fora desse denominador. Com vários indicadores, cada par município–indicador conta como uma observação.')
    a, b = st.columns([.85, 1.4])
    with a, st.container(border=True, key='chartpanel_01'):
        st.subheader('Situação das metas')
        plot(charts.donut(frame))
        row = summarize(frame).iloc[0]
        st.caption(f'{number(row.AVALIADOS)} avaliadas · {number(row.SEM_INFORMACAO)} sem informação')
    with b, st.container(border=True, key='chartpanel_02'):
        hist = filter_data(whole, uf=filters['uf'], municipality=filters['municipality'])
        if filters['indicator'] != 'Todos':
            sid = catalog.loc[catalog.ANO.eq(filters['year']) & catalog.INDICADOR.eq(filters['indicator']), 'SERIE']
            hist = filter_data(hist, series=sid.iloc[0]) if len(sid) else hist.iloc[0:0]
        plot(charts.time_line(history(hist)))
        st.caption('Mantém o recorte geográfico. Indicador selecionado: mesma definição; todos: composição de indicadores varia conforme o ano.')
    a, b = st.columns(2)
    with a, st.container(border=True, key='chartpanel_03'):
        plot(charts.ranking(summarize(frame, ['UF']), 'UF', 'Cumprimento por UF · 10 maiores', 10))
    with b, st.container(border=True, key='chartpanel_04'):
        summary = summarize(frame, ['INDICADOR'])
        definitions = catalog.loc[catalog.ANO.eq(filters['year']), ['INDICADOR', 'DESCRICAO']]
        summary = summary.merge(definitions, on='INDICADOR', how='left')
        summary['Rotulo'] = summary.DESCRICAO.str.slice(0, 47) + '…'
        plot(charts.ranking(summary, 'Rotulo', 'Cumprimento por indicador', 15))
    if frame.INDICADOR.nunique() > 1:
        summary = summarize(frame, ['INDICADOR']).merge(catalog.loc[catalog.ANO.eq(filters['year']), ['INDICADOR', 'DESCRICAO']], on='INDICADOR', how='left')
        a, b = st.columns(2)
        with a:
            st.subheader('Maiores cumprimentos')
            table(summary.nlargest(5, 'CUMPRIMENTO')[['INDICADOR', 'DESCRICAO', 'CUMPRIMENTO', 'AVALIADOS']])
        with b:
            st.subheader('Indicadores que exigem atenção')
            table(summary.nsmallest(5, 'CUMPRIMENTO')[['INDICADOR', 'DESCRICAO', 'CUMPRIMENTO', 'AVALIADOS']])


def states(frame, *_):
    if empty(frame): return
    cards(frame, summarize(frame))
    note('Com um indicador, avaliados corresponde a municípios com situação conhecida. Com todos, corresponde a pares município–indicador. O ranking usa cumprimento das metas, sem média de resultados municipais.')
    summary = summarize(frame, ['UF']).sort_values('CUMPRIMENTO', ascending=False)
    a, b = st.columns([1, 1.3])
    with a, st.container(border=True, key='chartpanel_05'):
        plot(charts.ranking(summary, 'UF', 'Ranking das Unidades da Federação'))
    with b:
        st.subheader('Desempenho por estado')
        table(summary[['UF', 'MUNICIPIOS', 'AVALIADOS', 'ATINGIRAM', 'NAO_ATINGIRAM', 'SEM_INFORMACAO', 'CUMPRIMENTO']], 680)
        st.caption('Clique no cabeçalho de qualquer coluna para ordenar. Ausência de dados permanece visível.')


def detail_table(frame, catalog):
    keys = ['ANO', 'INDICADOR']
    d = frame.merge(catalog[keys + ['DESCRICAO', 'LABEL_META']], on=keys, how='left')
    d['SITUACAO'] = d.SITUACAO.astype('string').map({STATUS[0]: '✓ Meta atingida', STATUS[1]: '✕ Meta não atingida', STATUS[2]: '— Sem informação'})
    return d


def municipalities(frame, whole, catalog, filters):
    if empty(frame): return
    if frame.COD_MUN.nunique() == 1:
        row = frame.iloc[0]
        st.subheader(f'{row.NOME_MUN} · {row.UF}')
        st.caption(f'Código {row.COD_MUN} · População: {number(row.POP_ANO)} · Ano: {row.ANO}')
        cards(frame, summarize(frame))
        r = summarize(frame).iloc[0]
        st.caption(f'Indicadores avaliados: {number(r.AVALIADOS)} · Atingiram: {number(r.ATINGIRAM)} · Não atingiram: {number(r.NAO_ATINGIRAM)} · Sem informação: {number(r.SEM_INFORMACAO)}')
        table(detail_table(frame, catalog)[['INDICADOR', 'DESCRICAO', 'NUM', 'DEN', 'RES_EXIBICAO', 'UNIDADE', 'LABEL_META', 'SITUACAO']])
    else:
        st.info('Selecione um município na barra lateral para abrir sua ficha. Abaixo, consulte o ranking do recorte.')
    st.subheader('Ranking municipal')
    note('Ordenação por percentual de metas atingidas. Empates têm a mesma posição. Resultados de escalas diferentes não são misturados no ranking.')
    ranking = municipal_ranking(frame)
    cols = ['POSICAO', 'NOME_MUN', 'UF', 'CUMPRIMENTO', 'AVALIADOS', 'SEM_INFORMACAO']
    if 'RES_EXIBICAO' in ranking:
        ranking = ranking.merge(catalog[['ANO', 'INDICADOR', 'LABEL_META']].loc[lambda x: x.ANO.eq(filters['year']) & x.INDICADOR.eq(filters['indicator'])][['LABEL_META']], how='cross')
        cols += ['RES_EXIBICAO', 'UNIDADE', 'LABEL_META', 'SITUACAO', 'POP_ANO']
    table(ranking[cols], 510)


def indicators(frame, whole, catalog, filters):
    if empty(frame): return
    entry = catalog[catalog.ANO.eq(filters['year']) & catalog.INDICADOR.eq(filters['indicator'])]
    if entry.empty:
        st.info('Definição indisponível neste ano.'); return
    row = entry.iloc[0]
    st.subheader(description_label(row))
    a, b, c = st.columns(3)
    a.caption('REGRA INFORMADA'); a.write(row.LABEL_META)
    b.caption('NUMERADOR'); b.write(row.LABEL_NUM)
    c.caption('DENOMINADOR'); c.write(row.LABEL_DEN)
    if row.ALERTA: st.warning(row.ALERTA)
    st.caption(row.ESCALA_NOTA)
    conflicts = int(frame.CONFLITO_META.sum())
    if conflicts:
        st.warning(f'{number(conflicts)} registros divergem entre ALCANCE_META e META. A classificação exibida prioriza ALCANCE_META, conforme a metodologia.')
    cards(frame, summarize(frame))
    s = summarize(frame).iloc[0]
    st.caption(f'Municípios avaliados: {number(s.AVALIADOS)} · Atingiram: {number(s.ATINGIRAM)} · Não atingiram: {number(s.NAO_ATINGIRAM)} · Sem informação: {number(s.SEM_INFORMACAO)}')
    hist = filter_data(whole, uf=filters['uf'], municipality=filters['municipality'], series=row.SERIE)
    a, b = st.columns(2)
    with a, st.container(border=True, key='chartpanel_06'): plot(charts.time_line(history(hist)))
    with b, st.container(border=True, key='chartpanel_07'):
        if frame.RES_EXIBICAO.notna().any(): plot(charts.distribution(frame))
        else: st.info('A fonte não fornece resultados numéricos para este indicador/ano. A situação da meta foi preservada conforme ALCANCE_META.')
    st.caption('Histórico limitado à mesma definição e unidade validada. Escalas originais não comprovadas ficam separadas por ano; veja a metodologia.')
    a, b = st.columns(2)
    with a, st.container(border=True, key='chartpanel_08'): plot(charts.ranking(summarize(frame, ['UF']), 'UF', 'Ranking de estados', 27))
    with b:
        st.subheader('Ranking municipal')
        table(municipal_ranking(frame)[['POSICAO', 'NOME_MUN', 'UF', 'RES_EXIBICAO', 'UNIDADE', 'SITUACAO', 'CUMPRIMENTO']], 650)


def historical(frame, whole, catalog, filters):
    if empty(frame): return
    row = catalog[catalog.SERIE.eq(filters['series'])].sort_values('ANO').iloc[-1]
    st.subheader(description_label(row))
    note('A série reúne apenas definições iguais após remover número, acentos e pontuação, na mesma unidade validada. Escalas não comprovadas e mudanças de redação interrompem a série. As metas de cada ano continuam próprias daquele ano.')
    cards(frame, summarize(frame))
    hist = history(frame)
    change = variation(hist)
    if change:
        st.metric(f'Variação do cumprimento · {change["inicio"]} → {change["fim"]}',
                  f'{number(change["pontos_percentuais"], 1)} pontos percentuais',
                  help='Diferença entre o percentual final e o inicial; não é crescimento percentual.')
        relative = change['variacao_relativa']
        st.caption(f'Variação relativa: {percent(relative)}. Composição territorial pode variar entre os anos.')
    a, b = st.columns(2)
    with a, st.container(border=True, key='chartpanel_09'): plot(charts.time_line(hist))
    with b, st.container(border=True, key='chartpanel_10'): plot(charts.counts_history(hist))
    a, b = st.columns(2)
    with a, st.container(border=True, key='chartpanel_11'):
        import plotly.express as px
        fig = px.bar(hist, x='ANO', y='AVALIADOS', color_discrete_sequence=['#206A8A'])
        fig.update_traces(hovertemplate='Ano: %{x}<br>Municípios avaliados: %{y:,.0f}<extra></extra>')
        fig.update_xaxes(title=None, dtick=1); fig.update_yaxes(title='Municípios avaliados')
        plot(charts.style(fig, 'Cobertura da avaliação por ano'))
    with b, st.container(border=True, key='chartpanel_12'):
        if frame.COD_MUN.nunique() == 1:
            trajectory = single_municipality_trajectory(frame, catalog)
            plot(charts.trajectory(trajectory))
            table(trajectory[['ANO', 'RES_EXIBICAO', 'UNIDADE', 'META_NUMERICA', 'SITUACAO']])
        else:
            st.subheader('Resultado do indicador')
            st.write('Selecione um município para acompanhar o resultado e a meta numérica ao longo dos anos.')
            st.caption('Não calculamos uma média simples municipal para representar o Brasil ou uma UF. O histórico agregado usa o cumprimento das metas.')
    st.subheader('Valores por ano')
    table(hist[['ANO', 'MUNICIPIOS', 'ATINGIRAM', 'NAO_ATINGIRAM', 'SEM_INFORMACAO', 'AVALIADOS', 'CUMPRIMENTO']])
    with st.expander('Definições, metas e alertas por ano'):
        table(catalog[catalog.SERIE.eq(filters['series']) & catalog.ANO.isin(hist.ANO)][['ANO', 'INDICADOR', 'DESCRICAO', 'LABEL_META', 'ALERTA']])


def comparisons(frame, whole, catalog, filters):
    if empty(frame): return
    row = catalog[catalog.SERIE.eq(filters['series'])].sort_values('ANO').iloc[-1]
    st.subheader(description_label(row))
    mode = st.radio('Comparar localidades', ['Estados', 'Municípios'], horizontal=True)
    if mode == 'Estados':
        options = sorted(frame.UF.unique().tolist())
        labels = {x: x for x in options}
        column = 'UF'
    else:
        local = frame[['COD_MUN', 'NOME_MUN', 'UF']].drop_duplicates().sort_values(['NOME_MUN', 'UF'])
        labels = {str(r.COD_MUN): f'{r.NOME_MUN} · {r.UF}' for r in local.itertuples()}
        options, column = list(labels), 'COD_MUN'
    chosen = st.multiselect('Localidades (até 5)', options, default=options[:min(3, len(options))],
                            format_func=lambda x: labels[x], max_selections=5, key=f'comparar_{mode}_{filters["series"]}_{filters["uf"]}_{filters["municipality"]}')
    if not chosen:
        st.info('Selecione pelo menos uma localidade.'); return
    selected = frame[frame[column].isin(chosen)]
    summary = summarize(selected, ['ANO', column])
    summary['Localidade'] = summary[column].astype('string').map(labels)
    plot(charts.time_line(summary, 'Cumprimento das metas · localidades selecionadas', color='Localidade'))
    if mode == 'Municípios':
        import plotly.express as px
        detail = selected.assign(Localidade=selected.COD_MUN.astype('string').map(labels))
        fig = px.line(detail.sort_values('ANO'), x='ANO', y='RES_EXIBICAO', color='Localidade', markers=True,
                      color_discrete_sequence=charts.PALETTE, custom_data=['SITUACAO'])
        fig.update_traces(hovertemplate='Ano: %{x}<br>Resultado: %{y:.2f}<br>Situação: %{customdata[0]}<extra>%{fullData.name}</extra>')
        fig.update_xaxes(title=None, dtick=1); fig.update_yaxes(title='Resultado (%)' if row.UNIDADE == '%' else 'Resultado original')
        plot(charts.style(fig, 'Resultado municipal · mesma definição'))
    note('Comparação restrita a até cinco localidades, na mesma definição e no período selecionado. Para municípios, cumprimento anual é 0% ou 100% quando a situação está informada.')
    table(summary[['ANO', 'Localidade', 'MUNICIPIOS', 'ATINGIRAM', 'NAO_ATINGIRAM', 'SEM_INFORMACAO', 'AVALIADOS', 'CUMPRIMENTO']])


def export_frame(frame, catalog):
    d = frame.merge(catalog[['ANO', 'INDICADOR', 'DESCRICAO', 'LABEL_META']], on=['ANO', 'INDICADOR'], how='left')
    return d[['ANO', 'UF', 'COD_MUN', 'NOME_MUN', 'POP_ANO', 'INDICADOR', 'DESCRICAO', 'NUM', 'DEN', 'RES', 'RES_EXIBICAO', 'UNIDADE', 'META', 'ALCANCE_META', 'LABEL_META', 'SITUACAO', 'CONFLITO_META']].rename(columns=RENAME)


def data_table(frame, whole, catalog, filters):
    situation = st.multiselect('Situação da meta', STATUS, default=STATUS)
    selected = frame[frame.SITUACAO.isin(situation)]
    if empty(selected): return
    st.caption(f'{number(len(selected))} observações no resultado filtrado. Downloads incluem todo esse recorte.')
    page_size = st.selectbox('Linhas por página', [100, 500, 1000])
    pages = max(1, (len(selected) + page_size - 1) // page_size)
    page = st.number_input('Página da tabela', min_value=1, max_value=pages, value=1, step=1)
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
    with st.expander('Indicadores disponíveis por ano'):
        table(catalog[['ANO', 'INDICADOR', 'DESCRICAO', 'LABEL_META', 'UNIDADE', 'ALERTA']])
    with st.expander('Auditoria do processamento'):
        st.json({k: v for k, v in metadata.items() if k != 'auditoria_abas'})
    st.download_button('Baixar metadados e auditoria', (DATA / 'metadata.json').read_bytes(), 'metadata_pqavs.json', 'application/json')
