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
