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
