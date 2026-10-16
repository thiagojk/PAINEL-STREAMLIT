from __future__ import annotations
from html import escape
from io import BytesIO
import json
import textwrap

import pandas as pd
import streamlit as st
from src import charts
from src.data import DATA, STATUS, filter_data
from src.metrics import history, summarize, variation, municipal_ranking, single_municipality_trajectory
from src.styles import cards, note, empty_state, kpi_grid, fact_sheet, indicator_summary
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
        styled = styled.map(lambda value: 'color:#116c65;font-weight:600' if ('atingida' in str(value).lower() and 'não' not in str(value).lower()) else 'color:#a45037;font-weight:600' if 'não atingida' in str(value).lower() else 'color:#596d7e', subset=['Situação'])
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
    a, b = st.columns([1.5, 1], gap='small')
    with a, st.container(border=True, key='chartpanel_02'):
        plot(charts.time_line(history(hist)))
        st.caption('Mesma localidade; definições e indicadores podem variar entre anos.')
    with b, st.container(border=True, key='chartpanel_01'):
        plot(charts.donut(frame))
        row = summarize(frame).iloc[0]
        st.caption(f'Situação das metas · {number(row.AVALIADOS)} avaliadas · {number(row.SEM_INFORMACAO)} sem informação')
    a, b = st.columns(2, gap='small')
    with a, st.container(border=True, key='chartpanel_03'):
        plot(charts.ranking(summarize(frame, ['UF']), 'UF', 'Cumprimento por UF · 10 maiores', 10))
    with b, st.container(border=True, key='chartpanel_04'):
        summary = summarize(frame, ['INDICADOR'])
        definitions = catalog.loc[catalog.ANO.eq(filters['year']), ['INDICADOR', 'DESCRICAO']]
        summary = summary.merge(definitions, on='INDICADOR', how='left')
        summary['Rotulo'] = summary.INDICADOR.astype('string').str.replace('IND_', '', regex=False) + ' · ' + summary.DESCRICAO.str.replace(r'^Indicador \d+ [-–] ', '', regex=True).str.slice(0, 28) + '…'
        plot(charts.ranking(summary, 'Rotulo', 'Cumprimento por indicador', 15))
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
    if empty(frame): return
    cards(frame, summarize(frame))
    from src.navigation import open_maps
    summary = summarize(frame, ['UF']).sort_values('CUMPRIMENTO', ascending=False)
    a, b = st.columns([1, 1.3])
    with a, st.container(border=True, key='chartpanel_05'):
        plot(charts.ranking(summary, 'UF', 'Ranking das Unidades da Federação'))
    with b:
        st.subheader('Desempenho por estado')
        table(summary[['UF', 'MUNICIPIOS', 'AVALIADOS', 'ATINGIRAM', 'NAO_ATINGIRAM', 'SEM_INFORMACAO', 'CUMPRIMENTO']], 680)
        st.caption('Clique no cabeçalho de qualquer coluna para ordenar. Ausência de dados permanece visível.')

    st.button('Abrir este recorte em Mapas', on_click=open_maps, args=(filters,), icon=':material/map:', key='atalho_mapas')
    with st.expander('Critérios do ranking estadual'):
        note('Com um indicador, avaliados corresponde a municípios com situação conhecida. Com todos, corresponde a pares município–indicador. O ranking usa cumprimento das metas, sem média de resultados municipais.')


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
        r = summarize(frame).iloc[0]
        kpi_grid([('Indicadores avaliados', number(r.AVALIADOS), f'{number(r.SEM_INFORMACAO)} sem informação', ''),
                  ('Metas atingidas', number(r.ATINGIRAM), '✓ Meta atingida', 'positive'),
                  ('Não atingidas', number(r.NAO_ATINGIRAM), '✕ Meta não atingida', 'negative'),
                  ('Cumprimento', percent(r.CUMPRIMENTO), 'Entre indicadores avaliados', '')], small=True)
        hist = filter_data(whole, municipality=row.COD_MUN)
        if filters['indicator'] != 'Todos':
            sid = catalog.loc[catalog.ANO.eq(filters['year']) & catalog.INDICADOR.eq(filters['indicator']), 'SERIE']
            hist = filter_data(hist, series=sid.iloc[0]) if len(sid) else hist.iloc[:0]
        with st.container(border=True, key='chartpanel_municipal_history'):
            plot(charts.time_line(history(hist), 'Cumprimento das metas no município'))
            st.caption('Com todos os indicadores, o conjunto avaliado pode mudar entre anos. Consulte Histórico para uma definição específica.')
        st.subheader('Desempenho por indicador')
        table(detail_table(frame, catalog)[['INDICADOR', 'DESCRICAO', 'NUM', 'DEN', 'RES_EXIBICAO', 'UNIDADE', 'LABEL_META', 'SITUACAO']])
    else:
        st.info('Selecione um município na sidebar de filtros para abrir sua ficha. Abaixo, consulte o ranking do recorte.')
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
    indicator_summary(row)
    if row.ALERTA: st.warning(row.ALERTA)
    conflicts = int(frame.CONFLITO_META.sum())
    if conflicts:
        st.warning(f'{number(conflicts)} registros divergem entre ALCANCE_META e META. A classificação exibida prioriza ALCANCE_META, conforme a metodologia.')
    cards(frame, summarize(frame))
    s = summarize(frame).iloc[0]

    hist = filter_data(whole, uf=filters['uf'], municipality=filters['municipality'], series=row.SERIE)
    a, b = st.columns(2)
    with a, st.container(border=True, key='chartpanel_06'): plot(charts.time_line(history(hist)))
    with b, st.container(border=True, key='chartpanel_07'):
        if frame.RES_EXIBICAO.notna().any(): plot(charts.distribution(frame))
        else: st.info('A fonte não fornece resultados numéricos para este indicador/ano. A situação da meta foi preservada conforme ALCANCE_META.')
    with st.expander('Ver detalhes do indicador'):
        st.write(description_label(row))
        fact_sheet('Definição e regra de avaliação', [('Regra informada', str(row.LABEL_META)),
                   ('Numerador', str(row.LABEL_NUM)), ('Denominador', str(row.LABEL_DEN))], eyebrow='FICHA DO INDICADOR')
        st.caption(row.ESCALA_NOTA)
    st.caption('Histórico limitado à mesma definição e unidade validada. Escalas originais não comprovadas ficam separadas por ano; veja a metodologia.')
    a, b = st.columns(2)
    with a, st.container(border=True, key='chartpanel_08'): plot(charts.ranking(summarize(frame, ['UF']), 'UF', 'Ranking de estados', 27))
    with b:
        st.subheader('Ranking municipal')
        table(municipal_ranking(frame)[['POSICAO', 'NOME_MUN', 'UF', 'RES_EXIBICAO', 'UNIDADE', 'SITUACAO', 'CUMPRIMENTO']], 650)


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
                  ('Variação', f'{number(change["pontos_percentuais"], 1)} p.p.', 'Pontos percentuais',
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


def comparisons(frame, whole, catalog, filters):
    if empty(frame): return
    row = catalog[catalog.SERIE.eq(filters['series'])].sort_values('ANO').iloc[-1]
    indicator_summary(row, show_rule=False)
    with st.sidebar:
        mode = st.radio('Comparar localidades', ['Estados', 'Municípios'], key='comparar_modo')
    if mode == 'Estados':
        options = sorted(frame.UF.unique().tolist())
        labels = {x: x for x in options}
        column = 'UF'
    else:
        local = frame[['COD_MUN', 'NOME_MUN', 'UF']].drop_duplicates().sort_values(['NOME_MUN', 'UF'])
        labels = {str(r.COD_MUN): f'{r.NOME_MUN} · {r.UF}' for r in local.itertuples()}
        options, column = list(labels), 'COD_MUN'
    with st.sidebar:
        chosen = st.multiselect('Localidades (até 5)', options, default=options[:min(3, len(options))],
                                format_func=lambda x: labels[x], max_selections=5, key=f'comparar_{mode}_{filters["series"]}_{filters["uf"]}_{filters["municipality"]}')
    if not chosen:
        st.info('Selecione pelo menos uma localidade.'); return
    selected = frame[frame[column].isin(chosen)]
    summary = summarize(selected, ['ANO', column])
    summary['Localidade'] = summary[column].astype('string').map(labels)
    plot(charts.time_line(summary, 'Cumprimento das metas · localidades selecionadas', color='Localidade'))
    if mode == 'Municípios':
        detail = selected.assign(Localidade=selected.COD_MUN.astype('string').map(labels))
        plot(charts.municipal_comparison(detail, row.UNIDADE))
    note('Comparação restrita a até cinco localidades, na mesma definição e no período selecionado. Para municípios, cumprimento anual é 0% ou 100% quando a situação está informada.')
    table(summary[['ANO', 'Localidade', 'MUNICIPIOS', 'ATINGIRAM', 'NAO_ATINGIRAM', 'SEM_INFORMACAO', 'AVALIADOS', 'CUMPRIMENTO']])


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


def maps(frame, whole, catalog, filters):
    # Importação tardia: nenhuma geometria municipal é lida em outras páginas.
    from src.geography import load_geojson, map_signature, state_summary, municipality_layer, map_metadata
    if empty(frame): return
    entry = catalog.loc[catalog.ANO.eq(filters['year']) & catalog.INDICADOR.eq(filters['indicator'])]
    if entry.empty:
        empty_state('Este indicador não está disponível no ano selecionado.'); return
    row = entry.iloc[0]
    label = str(row.DESCRICAO)
    # Tooltips podem quebrar linhas, sem repetir descrições extensas no eixo.
    hover_label = '<br>'.join(escape(line) for line in textwrap.wrap(label, 55))
    if frame.CONFLITO_META.any():
        st.warning(f'{number(frame.CONFLITO_META.sum())} registros têm divergência entre META e ALCANCE_META; a prioridade de ALCANCE_META foi preservada. Consulte a metodologia.')
    total = summarize(frame).iloc[0]
    kpi_grid([('Municípios avaliados', number(total.AVALIADOS), f'{number(total.SEM_INFORMACAO)} sem informação', ''),
              ('Atingiram a meta', number(total.ATINGIRAM), '✓ Meta atingida', 'positive'),
              ('Não atingiram', number(total.NAO_ATINGIRAM), '✕ Meta não atingida', 'negative'),
              ('Cumprimento', percent(total.CUMPRIMENTO), 'Entre municípios avaliados', '')], small=True)
    nationwide = filters['uf'] == 'Todos'
    a, b = st.columns([2.1, 1], gap='small')
    with a, st.container(border=True, key='map_main'):
        with st.spinner('Carregando mapa do Brasil…' if nationwide else 'Carregando mapa municipal…'):
            geometry = load_geojson(map_signature(None if nationwide else filters['uf']))
            if nationwide:
                summary = state_summary(frame)
                plot(charts.state_map(summary, geometry, filters['year'], hover_label))
                st.caption('Escala fixa de 0 a 100%. Cinza: UF sem avaliação disponível.')
            else:
                layer = municipality_layer(frame, geometry)
                plot(charts.municipality_map(layer, geometry, filters['year'], hover_label, str(row.LABEL_META)))
                st.html('<div class="map-legend">' + ''.join(
                    f'<span><i style="background:{charts.COLORS[status]}"></i>{text}</span>' for status, text in
                    zip(STATUS, ['✓ Meta atingida','✕ Meta não atingida','— Sem informação'])) + '</div>')
                no_record = int((~layer.TEM_OBSERVACAO).sum())
                st.caption(f'{number(no_record)} territórios da malha sem observação no recorte (cinza). Não entram no denominador nem são acrescentados à base.')
                missing = frame.loc[~frame.COD_MUN.isin(layer.COD_MUN), ['COD_MUN','NOME_MUN']]
                if len(missing):
                    st.warning(f'{number(len(missing))} municípios sem geometria. Permanecem no ranking e nos totais.')
                    table(missing)
    with b, st.container(border=True, key='map_ranking'):
        if nationwide:
            plot(charts.ranking(state_summary(frame), 'UF', 'Ranking de cumprimento por UF', 27))
        else:
            ranks = summarize(frame, ['NOME_MUN'])
            plot(charts.ranking(ranks, 'NOME_MUN', 'Municípios com maior cumprimento', 15))
        st.caption('Ranking por cumprimento; empates não indicam diferença de desempenho. Resultados municipais não são promediados.')
    note('Cumprimento = atingiram ÷ (atingiram + não atingiram). Sem informação fica fora do denominador. O mapa usa um único indicador e ano, preservando a prioridade de ALCANCE_META e os conflitos documentados.')
    metadata = map_metadata()
    report = metadata['correspondencia']
    st.caption(f'Geometrias: IBGE via espelho público versionado · {number(report["associados"])} de {number(report["municipios_base"])} códigos associados ({percent(report["taxa_percentual"])}). Malha estática e simplificada; consulte Sobre / Metodologia.')
    with st.expander('Definição do indicador e regra da meta'):
        st.write(label)
        st.write(row.LABEL_META)
        if row.ALERTA:
            st.warning(row.ALERTA)
    with st.expander('Dados territoriais do mapa'):
        if nationwide:
            table(state_summary(frame)[['UF','MUNICIPIOS','AVALIADOS','ATINGIRAM','NAO_ATINGIRAM','SEM_INFORMACAO','CUMPRIMENTO']])
        else:
            table(detail_table(frame, catalog)[['COD_MUN','NOME_MUN','RES_EXIBICAO','UNIDADE','LABEL_META','SITUACAO']])
