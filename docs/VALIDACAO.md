# Validação da nona etapa: Mapas fixos e comparação por substituição

Baseline `64fd7f9`, árvore limpa e **95 testes aprovados antes das alterações**. Escopo restrito ao layout de Mapas e aos testes da apresentação alterada.

## Comportamento entregue

- Conteúdo principal: título Mapas, cards e área de visualização. Não há explicações, subtítulo, recorte ou seletor antes dos cards. Cabeçalho institucional e navegação permanecem.
- Comparação desligada: somente mapa atual e ranking. Ligada: somente a grade histórica com legenda compartilhada. Não há expander histórico abaixo do mapa nem duplicação de figuras. Voltar restaura o conteúdo anterior, preservando filtros e anos. A área usa chaves distintas por apresentação/modo para reiniciar a rolagem no topo; legenda e primeiro ano aparecem imediatamente. O ranking ganhou margem para seus rótulos externos e título curto no eixo, sem mudar valores ou ordenação.
- O seletor único da sidebar continua governando os dois modos. Situação usa categorias; Grau mantém transformação, cap visual, ausência separada e escala 0–100% já validados. Brasil/UFs preserva o percentual de municípios que atingiram, explicitamente identificado, sem grau estadual ou média municipal.
- Explicações, definição, alertas, conflitos, quantidades de territórios sem observação, dados e notas de limites estáticos permanecem na sidebar. Sobre mantém a documentação completa. Alertas históricos são apresentados por ano na ajuda.
- Flex/grid delimitam a área ao viewport (`100dvh`), descontando o espaço realmente ocupado pelo cabeçalho, navegação, título e cards. Plotly usa altura nativa `stretch`, com autoenquadramento existente. CSS só é ativado quando a página contém `map_viewport`.
- Em telas estreitas, mapa/ranking empilham-se e a grade passa a uma coluna, com rolagem interna na área dos mapas. Sidebar rola de forma independente. Não se bloqueia o acesso a mapas ou controles para simular ausência de scroll.

## Verificação

**95 testes aprovados**, sem testes removidos/desativados. As expectativas de quantidade de figuras foram atualizadas para a substituição solicitada: cinco históricos em vez de principal + cinco; seleção histórica vazia produz estado informativo sem renderizar o mapa atual; ano indisponível não mantém ranking. O teste de sincronização foi ampliado para ligar/desligar a comparação repetidamente nos dois modos, confirmar restauração e filtros, igualdade de cores/escala e ausência de novas leituras de Parquet/GeoJSON.

`python -m compileall -q .` aprovado; `python -m pip check` sem dependências incompatíveis.

Na revisão móvel foram corrigidas a quebra automática das colunas (que podia sobrepor mapa e ranking) e a altura percentual de células em grades sem altura definida. O teste de navegador verifica também a ausência de sobreposição e que cada canvas histórico fica dentro de seu card.

Navegador Chromium em 1920×1080, 1440×900, 1366×768, 1024×768, 768×1024 e 390×844. Pará e Brasil nos dois modos; cinco anos 2013/2015/2017/2019/2021 da série de ocupação (renumeração respeitada). Verificados: exclusividade dos ramos, restauração dos filtros, escala/paleta dos cinco mapas, geometria renderizada, limites do viewport, rolagem interna em telas pequenas, ausência de rolagem geral/horizontal, sidebar e retorno ao fluxo rolável de Visão Geral. Acre com indicador sem Grau também foi exercitado, tanto no mapa atual quanto no histórico.

Relatório: [validacao_mapas_fixos.json](validacao_mapas_fixos.json). Capturas: `screenshots/mapas-fixos-atual-*.png` e `mapas-fixos-comparacao-*.png`. Reprodução: `python scripts/validar_mapas_fixos.py`, com app local na porta 8501 e Chromium em `/usr/bin/chromium`. Scripts visuais de etapas anteriores permanecem como registro do antigo layout simultâneo; não foram usados para alegar validação da nova apresentação.

Integridade: [integridade_mapas_fixos.json](integridade_mapas_fixos.json) comprova **46 arquivos idênticos** ao baseline: dados, geometrias, regras, Grau de alcance, métricas, preparação/cache histórico, paleta, funções de gráficos e filtros, dependências e configuração Streamlit. `app.py` continua como entrypoint; suas mudanças apenas omitem subtítulo/recorte/rodapé em Mapas. Nenhuma dependência nova.

Limite de validação: aplicativo iniciado e exercitado neste ambiente. URL pública do Streamlit Community Cloud não acessada nesta rodada.

---

## Histórico das etapas anteriores

# Validação da oitava etapa: controle global de Mapas na sidebar

Baseline `d7be117`, árvore limpa e 94 testes aprovados antes das alterações. Escopo: localização e apresentação do seletor, sincronização e configuração das cores dos mapas. Entry point, dependências, cálculo de Grau, regras, dados, cache e geometrias preservados byte a byte.

## Controle e representação

O seletor fica na sidebar de Mapas, depois de Ano, UF e Indicador e antes de Evolução territorial. Foi escolhido `st.radio` vertical nativo com largura estendida: mantém rótulos completos, área de clique de pelo menos 40 px, foco visível e duas opções permanentemente legíveis na sidebar estreita. Não há controle de modo na área principal; somente captions do modo ativo. Limpar filtros restaura Situação sem trocar a página.

`map_mode` é a única fonte de verdade. `views.maps` lê esse estado e envia o mesmo booleano `progress` a `territorial_history`, que governa todos os mapas anuais. Não foram criados estados para mapa principal/histórico. Alternar preserva ano, UF, indicador e anos escolhidos.

Cores categóricas existentes preservadas: Atingida **#147D73**, Não atingida **#B45B44**, Sem informação **#AFBAC4**. Teal versus terracota têm matizes distintos, com texto/símbolos na legenda e no tooltip. Os mapas municipais de Situação usam três cores discretas, sem colorbar. Grau usa a escala sequencial existente **#EDF6F3 → #BDDDD3 → #7DB9AB → #398E80 → #116357**, com `zmin=0`, `zmax=100` em todos os anos. Não há interpolação terracota→teal. Sem grau calculável fica cinza, fora da escala e diferente do zero válido claro. O cap visual e os tooltips permanecem conforme a metodologia validada.

Tokens centrais: `MAP_STATUS_REACHED`, `MAP_STATUS_NOT_REACHED`, `MAP_STATUS_MISSING`, `MAP_STATUS_COLORS`, `MAP_PROGRESS_SCALE`. Mapas principais, mapas históricos e legendas usam os mesmos tokens. O histórico compartilha uma legenda e não repete colorbars em cada mapa.

**Distinção nacional preservada:** o mapa Brasil/UFs continua mostrando % dos municípios que atingiram a meta nos dois modos, com aviso explícito também em Situação e no histórico. Não existe situação oficial única nem grau estadual validado na base. Por isso o mapa de UFs permanece quantitativo; não foi convertido em categorias mediante cortes arbitrários, nem foram calculadas médias municipais. A exigência de representação estritamente categórica no modo Situação aplica-se aos mapas municipais com situação registrada. Selecionar uma UF oferece a alternância categórica/contínua completa. Esta exceção é necessária para preservar os cálculos e a distinção territorial solicitados.

## Evidências

- **95 testes aprovados**: todos os 94 anteriores e um novo teste integrado de sincronização.
- Novo teste opera o rádio real da sidebar quatro vezes. Com PA, indicador 13/14 (ocupação) e 2013/2015/2017/2019/2021, verifica um mapa principal + cinco históricos, cores discretas em Situação, gradiente/escala fixa em Grau e preservação de todos os filtros. Verifica também existência de um único controle na sidebar, ausência de estados separados e zero novas leituras de Parquet/GeoJSON após o preparo inicial.
- Testes anteriores de Grau atualizados para operar o rádio nativo, preservando asserções de valores, ausências, regras indisponíveis e série conceitual. Nenhuma fórmula foi alterada.
- `python -m compileall -q .`: aprovado. `python -m pip check`: sem dependências incompatíveis.
- Navegador Chromium real: 1920×1080, 1440×900, 1366×768, 1024×768, 768×1024 e 390×844; sidebar, rádio, mapa principal e histórico nos dois modos. Sem controles duplicados, cortes dos rótulos ou overflow horizontal da página/área principal. Brasil, Pará e Acre, vários indicadores e anos, inclusive grau indisponível. Sem erros JavaScript nem requisições externas da página.
- `scripts/validar_evolucao.py` também aprovado: renumeração, tooltips, cinco mapas temporais, legendas e responsividade anteriores preservados.
- [integridade_sidebar_mapas.json](integridade_sidebar_mapas.json): **44 arquivos protegidos idênticos** ao baseline, incluindo os três arquivos de dados, 28 GeoJSONs, toda configuração de regras, `target_progress.py`, cálculo e preparação histórica, `app.py`, dependências e configuração Streamlit.

Reprodução: `python scripts/validar_tema_mapas.py` com app local na porta 8501 e Chromium em `/usr/bin/chromium`; `--width 390` restringe o diagnóstico à largura móvel. Relatório: [validacao_sidebar_mapas.json](validacao_sidebar_mapas.json). Capturas: `screenshots/sidebar-situacao-mapa-*.png`, `sidebar-grau-mapa-*.png`, `sidebar-grau-historico-*.png`. Na primeira execução visual, a verificação de área clicável incluiu indevidamente o título do widget; foi restrita aos rótulos das duas opções, mantendo a verificação de 40 px.

Compatibilidade Streamlit Community Cloud preservada: mesma versão, entrypoint e dependências. Aplicação validada no ambiente local; URL pública não acessada nesta rodada.

---

## Histórico das etapas anteriores

# Validação da sétima etapa: tema e grau de alcance nos mapas

Baseline: `fa80798`, árvore limpa e 72 testes aprovados antes de editar. Foram examinados entrada, módulos, testes, scripts, estilos, dependências, documentação, catálogo anual e configurações históricas/2025. A origem `main` estava no mesmo commit. Nenhuma página removida foi recriada.

## Resultado e metodologia

Tema e semântica estão em `src/theme.py`; desenho e hierarquia anteriores preservados. Alterações de cor atingem cards, navbar, sidebar, header, tabelas, donut, séries, barras empilhadas, rankings, cobertura, comparações, mapas e heatmaps. Antes: primária #137C8B, atingida #14887D, não atingida #CA785C, neutra #ACB9C8, escalas divergentes. Agora: primária #176B78, profunda #123E52, atingida #147D73, não atingida #B45B44, neutra #AFBAC4, fundo #F1F5F8 e branco nas superfícies. A primária evolui a identidade teal/azul; terracota complementar é moderada. Os tokens de texto e as duas cores semânticas têm contraste mínimo 4,5:1 sobre branco; escala sequencial tem luminância monotônica. Não é certificação integral WCAG. Legendas/textos e traçados continuam necessários.

O seletor nativo obrigatório, com quebra de linha em telas estreitas, alterna a mesma área atual e histórica. Situação oficial continua intocada. A razão complementar só existe para 92 combinações indicador/ano com meta percentual crescente explícita, escala validada e sem alerta; o registro individual também precisa de resultado e NUM/DEN consistentes. 36 combinações não suportadas. Cadastro completo com tipo, fórmula e justificativa: [GRAU_ALCANCE_INDICADORES.md](GRAU_ALCANCE_INDICADORES.md). Não foram cadastradas fórmulas inversas, de zero, baseline ou compostas sem suporte.

Grau real = 100 × resultado (%) / meta positiva anual; grau visual = min(100, grau real). Resultado acima de 100% pode ocorrer em razões com estimativas no denominador (como óbitos esperados); não é apagado ou corrigido. A situação da fonte é independente, preservada no tooltip. Zero válido é claro; grau indisponível é cinza, nunca zero. Motivo é apresentado. Brasil / UFs continua sendo percentual de municípios que atingiram a meta, explicitamente rotulado, com aviso de ausência de grau estadual no modo Grau. Não foi feita média municipal.

Histórico usa a mesma série conceitual, inclusive renumeração, com grupo de transformação compatível, escala 0–100 e legenda compartilhada. Regras anuais e mudanças de limite permanecem no tooltip; proximidade relativa não implica resultados absolutos idênticos. Anos sem transformação apresentam indisponibilidade; incompatibilidade de transformação impede comparação. Cache de camadas derivadas não contém novas geometrias, usa assinatura dos dados e regras; os caches existentes de geometria/séries são reutilizados.

## Conferência numérica independente

Parquet original, Belém/PA, código 150140, 2021. Esperados calculados por `100 × (100 × NUM/DEN) / limite literal do catálogo`, sem usar a função da métrica. Diferenças < 1e-8. Valores reais foram conferidos também no tooltip do navegador (arredondamento a uma casa no grau).

| Indicador | NUM | DEN | Resultado (%) | Meta (%) | Grau real (%) | Cor (%) |
|---|---:|---:|---:|---:|---:|---:|
| IND_01 | 11865 | 9437 | 125.72851542 | 90 | 139.69835046 | 100.00000000 |
| IND_02 | 16621 | 20898 | 79.53392669 | 90 | 88.37102966 | 88.37102966 |
| IND_04 | 0 | 4 | 0.00000000 | 100 | 0.00000000 | 0.00000000 |
| IND_07 | 21 | 50 | 42.00000000 | 70 | 60.00000000 | 60.00000000 |

A exigência de três tipos matemáticos diferentes não pode ser satisfeita com segurança nesta base: apenas a família percentual crescente tem suporte. Foram conferidos quatro indicadores reais, incluindo metas de 90%, 100% e 70%, com ultrapassagem, proximidade parcial e zero. Aumento de HIV foi auditado como indisponível por baseline não identificado; ciclos/cobertura e meta em semanas permanecem indisponíveis. Não se inventaram casos reais decrescentes, de baseline ou compostos para preencher essa validação. Os testes sintéticos verificam que esses tipos retornam motivo de indisponibilidade.

Auditoria reproduzível: `python scripts/auditar_grau_alcance.py`; [auditoria_grau_alcance.json](auditoria_grau_alcance.json) contém valores, cobertura PA/AC por indicador, tempo de preparo/cache e SHA-256 de 40 arquivos comparados byte a byte ao baseline. Inclui dados, 28 GeoJSONs, entrada, dependências e módulos de cálculos anteriores. Só o cadastro histórico ganhou metadados complementares; status `source_only`, regras oficiais e referência 2025 permanecem intactos.

## Verificações

- `python -m pytest -q`: **94 testes aprovados** (72 anteriores + 22 novos), sem testes removidos ou desativados.
- `python -m compileall -q .`: aprovado.
- `python -m pip check`: sem dependências incompatíveis.
- Testes da métrica: crescente, abaixo/igual/acima da meta, cap, zero, ausências/não finitos, metas não positivas, negativos, baseline ausente, baseline sem regra, direção inversa, manutenção de zero, regra composta e sem suporte.
- Testes de mapas: geometrias PA/AC, camada vazia, ausência diferente de zero, tooltip, cores, escala, renumeração 15→14, série incompatível, modo categórico/contínuo, histórico e preservação dos filtros. Nenhum dado ou situação é alterado.
- Contraste, coerência de tokens e luminância sequencial são verificados numericamente.
- Navegador Chromium real, seis páginas e 1920×1080, 1440×900, 1366×768, 1024×768, 768×1024, 390×844. Modos principal/histórico, Brasil, Pará, Acre, diferentes indicadores e anos, casos indisponíveis e tooltips reais. Sem overflow da página, erros JS ou requisições externas. Capturas e relatórios abaixo.
- Regressões: `scripts/validar_interface.py`, `scripts/validar_estados.py`, `scripts/validar_evolucao.py` e `scripts/validar_refinamento.py`. Exportações CSV/XLSX, navegação, sidebar e explorações anteriores preservadas.

Foi corrigida uma fuga horizontal no celular: os inputs invisíveis dos rádios nativos da navbar escapavam de seus rótulos e ampliavam a área rolável principal. `position:relative` nos rótulos estabelece o bloco correto para os inputs; navegação/teclado nativos e rolagem interna da navbar permanecem. O novo script verifica também `stMain.scrollLeft == 0` e largura rolável limitada ao viewport em todas as páginas e nos novos modos.

O teste antigo de cores dos mapas temporais foi atualizado para consultar o registro central, mantendo as verificações de constância entre anos. A validação inicial do novo script detectou seletores de automação incorretos (indicador com zero à esquerda e `role=radio` do segmented control); e recolhimento da sidebar sobreposta no celular; foram corrigidos sem relaxar as asserções de dados, filtros ou escala.

Relatórios: [tema e mapas](validacao_tema_mapas.json), [interface](validacao_navegador.json), [Estados](validacao_estados.json), [histórico territorial](validacao_evolucao.json), [refinamentos anteriores](validacao_refinamento.json). Capturas: `screenshots/tema-*.png`, `grau-mapa-*.png`, `grau-historico-*.png` e `situacao-mapa-*.png`.

Compatibilidade: mesmas dependências, entrypoint e configuração de arquivos estáticos, sem Node, Docker, banco ou serviço externo. O aplicativo foi iniciado e validado localmente no ambiente de trabalho; **a URL publicada do Streamlit Community Cloud não foi acessada nem verificada**. Os tempos de preparo registrados são locais, não garantias de latência do hosting.

---

## Histórico de validações anteriores

# Validação da sexta etapa: hierarquia dos cards e explorações históricas

A `main` em `43ada3f` estava limpa e seus **64 testes passaram antes das alterações**. A navegação segue Visão Geral, Estados, Mapas, Histórico, Dados, Sobre; nenhuma página removida foi recriada.

## Resultado atual

- **72 testes aprovados**, preservando os 64 anteriores. Novos casos cobrem denominadores históricos, ausência/ano vazio, mudanças de catálogo e coorte, renumeração, não junção de séries anuais inseguras, período mínimo, todos os anos intermediários, paridade com os patamares já validados em Brasil/PA/AC, alinhamento por linha, cards únicos, carregamento sob demanda e bloqueio da exploração coletiva para município individual.
- `python -m compileall .`: sem erros. `python -m pip check`: nenhuma dependência quebrada.
- SHA-256 de Parquets, metadados, 28 GeoJSONs, `data.py`, `metrics.py`, `state_analysis.py`, `rules.py` e configurações metodológicas: idênticos ao início. Metodologia e regras de 2025 não foram alteradas.
- Chromium: seis páginas, navegação, sidebar, filtros, downloads CSV/XLSX, mapas e evolução territorial preservados. Relatórios existentes atualizados: `validacao_navegador.json`, `validacao_estados.json`, `validacao_evolucao.json`.
- Validação nova em **1920×1080, 1440×900, 1366×768, 1024×768, 768×1024 e 390×844**, com medições de borda, cards e análise histórica. Resultado em `validacao_refinamento.json`.
- Nenhum erro JavaScript ou requisição externa nos cenários; sem overflow horizontal da página. Gráficos densos mantêm rolagem interna em telas estreitas.

## Cards e primeira dobra de Estados

Um único bloco HTML contém dois grupos semânticos: Resumo do recorte e Perfil de alcance, cada um com quatro cards. Os cards de patamar foram retirados da posição inferior; aparecem uma única vez, antes das barras principais. A distribuição por faixa permanece abaixo do gráfico, sem repetir cards ou criar outra distribuição.

A hierarquia usa títulos pequenos, espaçamentos contidos, valores legíveis e tooltip de método com foco/aria-label. Cada patamar informa municípios no patamar e denominador com avaliação. A explicação distingue perfil descritivo de incentivo oficial.

A validação mediu oito cards, dois grupos, ausência de duplicação, largura mínima de 130 px e gráfico principal antes de y=600 em 1366×768. Os cards quebram em duas colunas no celular. Compare `screenshots/cards-estados-1366-antes.png` e `screenshots/cards-estados-1366.png`.

## Alinhamento da Visão Geral

`ranking_height` preserva a altura necessária para categorias; `align_row_figures` harmoniza somente os gráficos de cada linha. Constantes compartilhadas representam tamanhos comuns e mapas, sem forçar um tamanho único. Containers nativos `height="stretch"` completam o alinhamento de borda, inclusive com captions quebradas em mais linhas. O donut usa título e legenda centralizada, com melhor ocupação de sua área.

Em 1366×768, os dois painéis da primeira linha mediram aproximadamente **385,8 px** e os dois da segunda, **439 px**. As medições verificaram diferença inferior a 2 px entre bordas inferiores em todas as larguras nas quais os painéis estavam lado a lado. No celular eles empilham naturalmente. Valores, rótulos e agregações anteriores foram preservados.

Capturas: `alinhamento-geral-1366.png`, `alinhamento-rankings-1366.png` e equivalentes nas seis larguras.

## Conferência direta de Pará / 2021

Contagem independente no Parquet: **144 municípios**, cada um com 14 situações conhecidas.

| Faixa | Municípios | Percentual |
|---|---:|---:|
| <30% | 16 | 11,1% |
| 30% a <50% | 51 | 35,4% |
| 50% a <70% | 67 | 46,5% |
| 70% a <90% | 10 | 6,9% |
| ≥90% | 0 | 0,0% |
| Sem avaliação | 0 | 0,0% |

Patamares: **≥30%: 128/144 (88,9%)**, **≥50%: 77/144 (53,5%)**, **≥70%: 10/144 (6,9%)**, **≥90%: 0/144**. Cards, distribuição e pontos de 2021 da evolução no navegador coincidiram com essas contagens, sem reutilizar o helper de cálculo na conferência independente.

Amostras individuais: Belém `150140`, 5/14 = 35,7%; Altamira `150060`, 8/14 = 57,1%; Santarém `150680`, 6/14 = 42,9%. Os números completos e contagens estão em `validacao_refinamento.json`.

Também foi conferida uma linha renumerada do heatmap no Pará: 2016/IND_15 = 70/(70+74) = 48,61%; 2021/IND_14 = 103/(103+41) = 71,53%. Ambos ocupam a mesma série/linha válida, com números anuais corretos. Nenhuma regra de 2025 é consultada nessa análise.

## Análises avaliadas e decisões

1. **Distribuição do alcance:** já estava implementada e validada. Foi preservada, sem segundo gráfico ou donut redundante.
2. **Evolução dos patamares:** implementada sob demanda, com período próprio e todas as metas do ano. O denominador municipal usa apenas situações conhecidas, exatamente como o perfil anterior. Município sem avaliação permanece separado; ano sem avaliação fica sem percentual. A composição anual não é tratada como painel fixo.
3. **Mudanças temporais:** tabela informa indicadores, municípios observados/com avaliação, situações desconhecidas, ausência de registro e mudanças. A assinatura compara definição conceitual/unidade e texto da meta; alterações do conjunto municipal também interrompem as linhas. Renumeração isolada não quebra um conceito válido.
4. **Persistência:** implementada por heatmap SERIE×ano, escala 0–100, sem preencher lacunas. Com 2013–2021, há 15 séries elegíveis e 48 omitidas por terem menos de três anos observados; séries anuais Original continuam separadas. Exige uma única definição/número por série em cada ano, recusando casos ambíguos.
5. **Classificações automáticas de tendência/persistência:** não implementadas. O heatmap já comunica padrões; classificar melhora/piora pelas pontas, impor corte não validado de “baixo” ou alegar significância/causalidade seria inadequado. Todos os pontos intermediários permanecem visíveis e são testados.

A exploração coletiva usa Brasil/UF, nunca ignora silenciosamente um município selecionado: nesse caso explica a restrição e mantém a trajetória individual acima. O indicador/período principal continua controlando os gráficos originais; a nova exploração tem período lateral próprio, explicitamente identificado. Inicialmente desativada, só prepara dados após o toggle. Fechar o expander recolhe a apresentação; desligar o toggle suspende o preparo/renderização.

## Cache e compatibilidade

O recorte é resumido por município/ano e série/ano, e o cache guarda apenas resultados pequenos, limitado por assinatura dos Parquets, UF e período. Preparação isolada: cerca de 0,30 s para Brasil incluindo leitura inicial dos dados e 0,08 s para PA/AC reutilizando a base; medianas de cópia do cache inferiores a 1 ms. Medidas em `desempenho_perfil_historico.json`, sem frontend ou garantia de latência no Cloud.

Mesmo `app.py`, dependências e arquitetura do aplicativo existente do Streamlit Community Cloud. Sem novo serviço, banco, Node ou Docker. Deploy público não foi acessado; a atualização efetiva deve ser acompanhada no aplicativo existente depois do push à `main`.

As seções abaixo registram entregas anteriores; relatórios e capturas compartilhados foram atualizados pela rodada vigente.

---

# Validação da quinta etapa: Estados e apresentação metodológica

A `main` em `341d427` foi examinada, incluindo navegação, views, filtros, métricas, pipeline, catálogos, mapas, configurações e testes. **46 testes passaram antes das mudanças**. O arquivo original tem 14 indicadores por ano, exceto 2016–2017, com 15. Todas as 712.708 observações possuem situação conhecida; 30.261 resultados numéricos ausentes não foram convertidos em ausência de avaliação. As 4.784 divergências de 2013 continuam seguindo `ALCANCE_META`.

## Resultado atual

- **64 testes aprovados**. Casos exclusivos das páginas retiradas foram removidos/adaptados; testes de granularidade municipal, pipeline, geografia e séries foram preservados. Novos testes verificam três situações, somas, denominadores, ausência de registro, patamares e seus limites exatos, UF/ano, heatmap, configuração temporal, classificação futura com todos os bloqueios e não aplicação de regras de 2025 ao histórico.
- `python -m compileall .`: sem erros. `python -m pip check`: nenhuma dependência quebrada.
- Parquets, metadados, 28 GeoJSONs, `src/data.py` e `src/metrics.py` preservados por SHA-256. Nenhuma dependência de execução nova; mesmo entrypoint `app.py`.
- Chromium: **seis páginas**, teclado, navegação superior aderente, sidebar recolhível, filtros PA/Belém → AC, série municipal, exportações CSV/XLSX baixadas e relidas, mapas/hover/anos e ausência territorial. Resultado em `validacao_navegador.json`.
- Estados: Brasil, Pará e Acre × 2013, 2017 e 2021; contagens de 14/15 indicadores e barras somando 100% verificadas. Tooltip real, tabela abaixo dos gráficos e rolagem interna móvel exercitados. Resultado em `validacao_estados.json`.
- Histórico de mapas preservado: cinco mapas do Brasil, cinco do Pará, tooltips de Pará/Belém, cores constantes, escala fixa, grade 3/2/1 e controles nativos. Resultado em `validacao_evolucao.json`.
- Resoluções **1920×1080, 1440×900, 1366×768, 1024×768, 768×1024 e 390×844**. Sem overflow horizontal da página. Barras e heatmap densos rolam dentro do próprio painel em telas estreitas; rótulos e matriz mantêm largura legível.
- **Zero erros JavaScript e zero requisições externas** nos cenários.

## Conferência numérica direta

Barras do Pará/2021, extraídas do objeto Plotly no navegador e comparadas a contagens diretas de `SITUACAO` nos registros do Parquet:

| Indicador | Meta atingida | Meta não atingida | Sem informação |
|---|---:|---:|---:|
| 01 | 138 | 6 | 0 |
| 06 | 56 | 88 | 0 |
| 08 | 144 | 0 | 0 |

O indicador 08 confirma que ausência de resultado numérico não invalida o alcance informado. As células AC/01, PA/05 e DF/14 do heatmap de 2021 foram conferidas como `atingiram / (atingiram + não atingiram) × 100`, sem média de resultados. Os números completos estão no relatório. A conferência foi reproduzida por inspeção do gráfico e agregação independente da fonte, não só por presença de elementos na tela.

## Denominadores e nomenclatura

- Barras: três situações sobre todos os registros observados daquele indicador; sem informação permanece segmento próprio. O tooltip informa tanto os avaliados quanto o denominador da barra e a ausência de registro.
- Cumprimento/heatmap: atingida ÷ (atingida + não atingida). Não é resultado estadual do indicador.
- Perfil: proporção de situações atingidas entre situações conhecidas de cada município. O número de indicadores segue o catálogo do ano. Município sem avaliação tem faixa própria e fica fora dos percentuais dos patamares; isso é explicitado.
- Ausência de registro é contabilizada separadamente entre municípios presentes no ano e indicadores do catálogo; não é imputada como falha ou aplicabilidade. A malha não expande a coorte analítica. A base não fornece aplicabilidade oficial universal/específica; o perfil permanece **descritivo**.
- Não se mostra incentivo oficial, adesão ou categorias atuais para 2013–2021.

## Reestruturação e dependências

Navegação final: Visão Geral, Estados, Mapas, Histórico, Dados, Sobre. Rotas/views de Municípios, Indicadores e Comparações foram removidas de `app.py`, `navigation.py` e `views.py`. Sessões que guardavam página antiga voltam à Visão Geral. Views eram funções no mesmo arquivo, não módulos exclusivos: nenhum módulo Python inteiro precisou ser apagado.

Foram removidos os gráficos órfãos `distribution`/`municipal_comparison`, o helper `fact_sheet` e seu CSS. Cinco capturas exclusivas aposentadas foram retiradas: `comparacoes.png`, `indicador.png`, `municipio.png`, `municipios.png`, `series-comparações.png`. Scripts de validação/desempenho e testes foram atualizados para a navegação vigente.

Preservados por dependência: `detail_table` (mapas), `municipal_ranking` (perfil municipal e testes de métricas), `single_municipality_trajectory`/`trajectory` (Histórico), exportação, resumo, séries e todos os módulos de dados/geografia/cache. Visão Geral já concentra cards, evolução, situação e resumo territorial, sem incorporar outra página longa.

Estados agora prioriza cards, barras empilhadas, patamares/perfil e comparação. Brasil mostra ranking por cumprimento descritivo e heatmap UF×indicador; uma UF mostra comparação com Brasil por indicador. O gráfico empilhado já identifica os indicadores críticos, evitando duplicar um ranking de indicadores. A tabela UF/ano/indicador vem depois dessas análises.

## Versionamento e proteção temporal

`indicator_rules/historical.json` é `source_only` (2013–2021); `2025.json` é `reference_only` a partir de 2025. O segundo contém somente a transcrição estrutural fornecida no pedido, com 14 indicadores, 7 universais/7 específicos, patamares de incentivo e referência de adesão. Não foram inventados nomes, metas ou classificações individuais de 2025. A cartilha completa não foi anexada/verificada nesta rodada.

`src/rules.py` resolve períodos sem sobreposição e exige conceito, número e série compatíveis. Os tipos de avaliação previstos incluem maior/menor, redução a partir do ano-base, manutenção de zero e regra composta; o histórico não é recalculado por esses metadados. Categorias só são oferecidas para configurações validadas, catálogo completo e correspondência de todas as observações.

A API de faixa estadual exige configuração validada, fonte, quantidade completa de indicadores, política explícita de ausência, universo municipal e aplicabilidade booleana completa, incluindo não aplicáveis. Dados/séries incompletos, situações desconhecidas ou categorias/períodos incompatíveis não habilitam classificação. As configurações distribuídas não atendem a esses requisitos. Os testes operacionais usam apenas fixtures sintéticas; não geram resultados oficiais para a base.

O teste crítico percorre 2013–2021 com uma configuração sintética de 2025 que contém os mesmos números: nenhum nome/meta/categoria/incentivo futuro é aplicado; catálogo e observações históricas permanecem íntegros.

Sobre apresenta a tabela de incentivo atual e o aviso de vigência a partir de 2025. A regra de adesão de 60% dos municípios é documentada separadamente, sem produzir indicador inexistente.

Referência informada: **Ministério da Saúde — Programa de Qualificação das Ações de Vigilância em Saúde — PQA-VS; cartilha atualizada com indicadores/metas aplicáveis a partir de 2025; Portaria GM/MS nº 6.878/2025**. Não comprova retrospectivamente as regras de 2013–2021.

## Desempenho e deploy

Agregações UF×indicador por ano e perfis ano/UF ficam em `st.cache_data`, com invalidação por assinatura dos Parquets e limites de entradas. Mapas e seus caches foram preservados. Dados do perfil são usados para métricas, sem serializar uma tabela municipal grande em todo rerun. Medições de nove recortes, com três reruns por recorte, estão em `desempenho_estados.json`: incluem execução/serialização em Python e excluem frontend, concorrência e latência do Cloud; não são promessa de tempo da hospedagem.

Mesmo repositório, `app.py`, versões de dependências e arquitetura. Sem banco, servidor adicional, Node, Docker ou serviço externo. Compatível com o aplicativo existente do Streamlit Community Cloud. O deploy público não foi acessado; acompanhar a atualização no mesmo aplicativo após o push.

Capturas principais: `screenshots/estados-1366.png`, `estados-para.png`, `estados-perfil.png` e `estados-heatmap.png`. As seções abaixo registram rodadas anteriores e sua navegação histórica; não descrevem rotas atuais. Screenshots compartilhados e relatórios reproduzíveis refletem a rodada vigente.

---

# Validação da quarta etapa: identidade, séries e evolução territorial

Inspeção da `main` em `b64841c`, incluindo a configuração de Dev Container já existente: árvore limpa, **34 testes aprovados antes de alterar**. A preparação dos dados, métricas, malhas, dependências e `app.py` foram preservados.

## Resultado atual

- **46 testes aprovados**, incluindo os 34 anteriores. Cobertura nova: conceitos únicos no Histórico/Comparações, definições diferentes separadas, renumeração, preservação de séries anuais inseguras, seleção correta, anos representativos/limite/incompatibilidade, mapa Brasil, PA e AC, cores/escala, ausência sem imputação, carregamento sob demanda e limpeza dos controles.
- `python -m compileall .`: sem erros; `python -m pip check`: nenhuma dependência quebrada.
- SHA-256 de Parquets, metadados, 28 GeoJSONs, `src/data.py` e `src/metrics.py`: idênticos ao início desta rodada.
- Chromium: nove páginas, filtros dependentes, navegação por teclado/sticky, exportações CSV/XLSX relidas e mapas atuais continuam funcionando. Relatório em `validacao_navegador.json`.
- Validação adicional dos seletores conceituais em Histórico e Comparações, e cinco mapas históricos do Brasil e cinco mapas municipais do Pará. Tooltips reais de Pará/Belém, limites de escala 0–100, cores categóricas iguais e abertura/recolhimento nativos da sidebar móvel conferidos. Relatório em `validacao_evolucao.json`.
- Resoluções 1920×1080, 1440×900, 1366×768, 1024×768, 768×1024 e 390×844: sem overflow horizontal. A evolução apresentou três colunas em 1920, duas nas intermediárias e uma em 390; malhas enquadradas.
- Console sem erros JavaScript e zero requisições externas durante os cenários.

## Correção investigada

O catálogo tem 128 definições anuais, 63 `SERIE` e 34 conceitos estritos (descrição sem numeração, normalização textual existente e unidade). A repetição aparente vinha principalmente do sufixo anual deliberado em escalas `Original`: o seletor antigo expunha cada série anual com descrições semelhantes. Não há duplicação de observações nem foi aplicada deduplicação por número.

O novo seletor agrupa somente a apresentação e oferece uma opção por conceito. As 63 séries analíticas permanecem; quando há séries anuais isoladas, uma segunda seleção explicita o ano e a restrição de escala. Conceitos de vacina com redações diferentes não foram unidos. Malária 08→07, ocupação 14→13 e outros casos válidos continuam seguindo as séries existentes. Ciclos da dengue aparece uma única vez como conceito, mas seus resultados de escala original não são ligados entre anos. O mapeamento integral está em `series_historicas.json`.

## Interface e primeira dobra

CSS restrito às ações `stToolbarActions`, `stAppDeployButton` e `MainMenu`. A inspeção do DOM mostrou que ocultar `stToolbar` inteiro também ocultaria o botão de reabrir a sidebar; o contêiner e esse botão foram preservados. `stHeader` fica transparente, sem capturar cliques fora dos botões. Não há JavaScript da aplicação, fork ou alteração do Streamlit.

Cabeçalho e navbar ganharam tamanho moderado; metadata permanece, inclusive no celular. Sidebar com ícone de filtro em CSS, fundo integrado, labels, bordas, hover/foco e botão outline. Estilos usam chaves próprias e atributos sem depender de classes geradas. Esses atributos internos ainda podem mudar: conferir novamente ao atualizar Streamlit. CSS interno não controla elementos externos à página/iframe da hospedagem.

Em **1366×768**, o primeiro gráfico começa em aproximadamente **358 px**, ante 384 px na terceira etapa. Navbar, resumo, seis cards e os dois gráficos principais completos continuam visíveis sem rolar. Compare `screenshots/visao-geral-1366-etapa3.png` com `screenshots/visao-geral-1366x768.png`; medidas em `densidade_etapa3.json` e `densidade_layout.json`.

## Mapas históricos e desempenho

O controle lateral próprio seleciona no máximo seis anos da `SERIE` do indicador atual. Padrão: até cinco posições igualmente distribuídas entre primeiro/último ano compatível. A grade aparece em expander depois do mapa atual/ranking e só é preparada quando o toggle está ligado. Fechar apenas o expander não suspende o cálculo; desligar o toggle suspende.

Brasil usa escala 0–100 fixa e legenda comum; municípios mantêm cores categóricas constantes. Cada painel traz ano e número anual correto. Tooltips preservam definição, resultado/meta/situação ou contagens de avaliação. Dados ausentes, conflitos e malha estática continuam explicitados, sem alterar denominadores.

`historical_slice` filtra a base uma vez por série/UF; `prepare_history` prepara as camadas para os anos escolhidos, ambos em `st.cache_data` com limites e invalidação por assinatura. As geometrias locais reutilizam `load_geojson`; nenhum arquivo geográfico novo. A medição isolada de cinco mapas em Python/Linux, com a base já carregada, registrou aproximadamente 0,09 s no Brasil e 0,06 s no Pará na primeira preparação; medianas de cache de 0,001 s. Isso exclui frontend, concorrência e hospedagem. Dados brutos em `desempenho_evolucao.json`; tempo observado no navegador em `validacao_evolucao.json` não é garantia de latência no Cloud.

## Deploy

Mesmo `app.py`, mesmas dependências e arquitetura, sem serviços adicionais. Compatível com o aplicativo existente do Streamlit Community Cloud. O deploy público e seus controles externos não foram acessados; a atualização efetiva do aplicativo deve ser acompanhada no mesmo app após o push à `main`.

As seções seguintes registram etapas anteriores; os screenshots compartilhados foram atualizados pela validação atual.

---

# Validação da terceira etapa: densidade e UX

## Primeira dobra em 1366×768

Antes, o primeiro gráfico começava em **y=767 px**, praticamente fora da tela. Agora começa em **y=384 px**, com a sidebar aberta: redução de **383 px (50%)**. Sem rolagem, ficam visíveis a navbar, identificação da página, seis cards e os dois primeiros gráficos completos, incluindo suas legendas e notas. A série histórica e a situação das metas compartilham a primeira linha; rankings ficam na segunda.

Compare [antes](screenshots/visao-geral-1366-antes.png) e [depois](screenshots/visao-geral-1366x768.png). Medidas reproduzíveis em `densidade_antes.json` e `densidade_layout.json`.

## Mudanças e verificação

Filtros dependentes passaram para a sidebar nativa recolhível, exclusivamente contextual. Estados não oferece UF; Visão Geral não oferece município; Histórico usa definição/período; Mapas usa ano/UF/indicador. Seleções de comparação e controles de situação/paginação também ficam na lateral. Limpar filtros mantém a página atual. Filtros ocultos não restringem silenciosamente o resultado.

O CSS compartilhado reduz padding, margens e gaps do cabeçalho, navbar, títulos e cards. As grades respondem à largura disponível após abrir/recolher a sidebar. Os gráficos simples usam 325 px; rankings longos e mapas mantêm alturas apropriadas. Rótulos de séries únicas alternam acima/abaixo para evitar aglomeração no celular; valores completos seguem nos tooltips. Fichas e explicações extensas foram movidas para expanders, preservando os alertas metodológicos visíveis.

- `python -m pytest -q`: **34 testes aprovados**, incluindo localização/contexto dos filtros e limpeza sem navegação.
- `python -m compileall .`: sem erros; `python -m pip check`: nenhuma dependência quebrada.
- Chromium: nove páginas, navegação por teclado/sticky, filtros PA/Belém → AC, comparação UF/município, CSV/XLSX baixados e relidos, mapas/hover de Pará e Belém, indicador indisponível e territórios sem observação.
- Layouts **1920×1080, 1440×900, 1366×768, 1024×768, 768×1024 e 390×844**, além dos mapas nas seis larguras: sem overflow horizontal; mapas enquadrados. Capturas em `screenshots/` e relatório em `validacao_navegador.json`.
- Console JavaScript sem erros e nenhuma requisição externa nos cenários.
- Hashes de Parquets, metadados, leitura/cache, métricas e geografia idênticos ao início desta etapa. Os testes conferem os hashes das malhas locais. Dependências de execução e `app.py` preservados, compatíveis com o mesmo aplicativo no Community Cloud; deploy público não verificado neste ambiente.

As medições de desempenho abaixo pertencem à segunda etapa; não são um novo benchmark desta rodada. Esta rodada preserva integralmente os módulos de dados, métricas e geografia/cache.

---

# Validação da segunda etapa

A versão anterior da `main` foi inspecionada e seus **21 testes passaram antes das alterações**. A entrega preserva esses casos e acrescenta testes de navegação e geografia. Dados, regras estatísticas e o entrypoint `app.py` foram preservados.

## Resultado atual

- `python -m pytest -q`: **33 testes aprovados**.
- `python -m compileall .`: concluído sem erros.
- `python -m pip check`: nenhuma dependência quebrada.
- SHA-256 dos dois Parquets, `data/metadata.json`, `src/data.py` e `src/metrics.py`: **idênticos aos da primeira etapa**.
- Cobertura geográfica: **5.570/5.570 municípios, 100%, sem códigos sem associação**; 27 UFs.
- Todos os 28 GeoJSONs tiveram contagens, hashes, códigos, anéis fechados, orientação e coordenadas verificados. O preparo também valida a topologia após simplificar e arredondar.
- A geometria municipal de cada UF é carregada somente ao abrir essa análise. Shapely e a obtenção de malhas são opcionais, fora da execução do dashboard. `requirements.txt` não mudou.

## Validação visual obrigatória

Aplicação iniciada com Streamlit e validada em Chromium. O relatório reproduzível está em `validacao_navegador.json`; capturas em `screenshots/`.

Foram exercitadas as nove áreas, Brasil, Pará, Belém e Acrelândia; filtros dependentes; troca de ano e indicador; indicador 15 e sua indisponibilidade em 2021; situações ausentes e sete territórios do Piauí sem observação; comparação por UF/município; downloads CSV/XLSX lidos novamente para confirmar o recorte. Os tooltips do Pará e de Belém foram abertos com o ponteiro e seus campos conferidos.

A barra superior permaneceu em posição aderente durante a rolagem e funcionou por teclado. As larguras **1920, 1440, 1366, 1024, 768 e 390 px** foram verificadas, com mapa e ranking empilhados quando necessário, rolagem interna da navegação e sem transbordamento horizontal da página. O teste verifica também se os polígonos ocupam área legível e cabem no gráfico, além da mera ausência de overflow da página.

A primeira inspeção detectou falha de enquadramento na renderização MapLibre disponível no frontend do Streamlit, embora o schema Python aceitasse o recurso. A versão final usa o coroplético SVG estável, `geo.fitbounds="locations"`, sem WebGL. Os anéis foram orientados para D3 sem alterar limites, e o TopoJSON auxiliar do motor é servido localmente. Isso corrigiu os mapas pequenos e o corte no celular. Nenhuma lógica de resultado ou de meta foi adaptada para resolver a visualização.

**Console: sem erros JavaScript. Requisições externas durante os cenários: zero.** O TopoJSON é obtido do mesmo host do aplicativo, via serviço estático nativo; não depende do CDN Plotly.

## Desempenho

Medição com Python 3.12.14/Linux e `AppTest`: três reruns por página, mediana em segundos. Mede execução/serialização no Python, não rasterização de navegador, carga simultânea ou tempo do Community Cloud. Variações pequenas não provam ganho ou regressão. Os dados brutos estão em `desempenho_antes.json` e `desempenho_depois.json`.

| Página | Antes (s) | Depois (s) |
|---|---:|---:|
| Visão Geral | 0.225 | 0.228 |
| Estados | 0.101 | 0.102 |
| Municípios | 0.299 | 0.330 |
| Indicadores | 0.407 | 0.453 |
| Análise Histórica | 0.204 | 0.180 |
| Comparações | 0.137 | 0.129 |
| Tabela de Dados | 0.079 | 0.069 |
| Sobre / Metodologia | 0.036 | 0.040 |

Primeira execução medida: 0.869s antes e 0.787s depois. Nova página Mapas: mediana 0.123s para Brasil e 0.299s para o Pará. As páginas existentes continuam abaixo de um segundo no cenário medido. Houve oscilações nos tempos, documentadas acima; isso não é uma garantia da latência da hospedagem. A execução final da medição foi feita sem o navegador de validação rodando em paralelo.

## Limitações e publicação

A malha é estática, simplificada e de ano não declarado nos arquivos do espelho; não representa necessariamente limites históricos nem serve para medir áreas. Treze geometrias de origem foram reparadas topologicamente, com identificadores auditáveis. Valores extremos, conflitos de meta e demais limites da fonte continuam documentados na metodologia anterior.

O dashboard já está publicado pelo proprietário. Esta entrega mantém a aplicação, a branch `main`, o entrypoint e as dependências de execução, sem exigir novo app ou URL. O deploy remoto/URL pública não foi acessado nesta máquina; a atualização efetiva no Community Cloud deve ser acompanhada no app existente. O BAT permanece disponível, mas não foi executado em Windows neste ambiente Linux.
