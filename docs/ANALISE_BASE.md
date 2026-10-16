# Análise do arquivo fornecido

A interface foi implementada após examinar todas as abas e as 86 colunas de cada aba anual. A auditoria inicial por coluna, com tipos, ausentes, frequências dos campos textuais e distribuição/escala dos resultados, está em `auditoria_excel.json`. A auditoria corrente do pipeline fica em `data/metadata.json`.

## Abrangência

| Ano | Registros município–ano | Indicadores com dados/definição | Observações longas |
|---|---:|---|---:|
| 2013 | 5.570 | 01–14 | 77.980 |
| 2014 | 5.570 | 01–14 | 77.980 |
| 2015 | 5.570 | 01–14 | 77.980 |
| 2016 | 5.570 | 01–15 | 83.550 |
| 2017 | 5.570 | 01–15 | 83.550 |
| 2018 | 5.570 | 01–14 | 77.980 |
| 2019 | 5.561 | 01–14 | 77.854 |
| 2020 | 5.570 | 01–14 | 77.980 |
| 2021 | 5.561 | 01–14 | 77.854 |
| **Total** | **50.112** | **15 códigos distintos** | **712.708** |

São 5.570 códigos municipais distintos e 27 UFs. As chaves ano–município são únicas nas abas anuais. O dicionário tem 142 linhas, incluindo 14 definições de 2022 sem observações. O catálogo efetivamente publicado no app possui 128 definições indicador–ano.

## Estrutura

Dimensões: `ANO`, `UF`, `COD_MUN`, `NOME_MUN`, `POP_ANO`. Códigos vêm com seis dígitos e são preservados como texto. População vem da própria linha anual; o painel não soma populações repetidas por indicador.

Campos de cada indicador: `NUM`, `DEN`, `RES`, `META`, `ALCANCE_META`, identificados genericamente por expressão regular. Ausentes incluem a string literal `NULL` e células vazias. O pipeline também aceita NA, N/A, None, espaços e formatos numéricos brasileiros. Há campos com tipos mistos; a conversão numérica é explícita e valores não convertíveis tornam-se ausentes.

Colunas auxiliares da fonte: `VL_PQA_VS`, `METAS_ALCANCADAS`, `METAS_NAO_ALCANCADAS`, `QTDE_INDICADORES`, `QTDE_AUSENCIA_CASOS`, `PERCENTUAL`. Elas foram auditadas e não integram o Parquet analítico porque não são necessárias aos recortes solicitados e seus conceitos não estão completamente documentados. O painel calcula seus próprios totais com denominador explícito a partir dos indicadores disponíveis, sem reinterpretar `PERCENTUAL` como cumprimento. Em anos iniciais, `QTDE_INDICADORES` pode contar 15 enquanto o dicionário e os dados utilizáveis só sustentam 14. Não se cria uma observação para o preenchimento estrutural do indicador 15.

## Regras e achados relevantes

- O indicador 15 só tem dados/definição observacional em 2016–2017. Fora desses anos, NUM/DEN/RES e alcance estão ausentes e META tem um preenchimento 0. Essas colunas não criam um indicador disponível.
- Em 2020–2021, o indicador 8 tem RES totalmente ausente, mas alcance informado: situação e resultado são campos diferentes. Ele continua disponível para análise de cumprimento, com aviso de ausência de resultado.
- Em 2013, o indicador 9 não tem RES, embora possua situação da meta.
- Existem 4.784 conflitos no indicador 8 de 2013: flag de alcance 1 e META “Não”. Ambos os campos são preservados. A classificação prioriza a flag, de modo explícito e com aviso, sem deduzir o motivo do conflito.
- O tratamento final possui 30.261 resultados ausentes. Todos os registros remanescentes do arquivo inicial têm uma classificação fornecida pela flag 0/1; isso não significa que todos tenham resultado numérico ou ausência de limitações.
- Há mudança de conceitos e numeração em 2018. Por exemplo, o conceito de raça/cor do indicador 15 de 2017 passa ao indicador 14 em 2018. Não se liga uma série só pelo número.
- Algumas descrições e metas mudam mesmo sem renumeração. O histórico conserva somente redações normalizadas iguais e unidade validada; pode ser interrompido quando a redação muda.
- Em 2013, diversos resultados são percentuais de 0–100, enquanto outros são razões; a partir de 2014, muitas proporções usam 0–1. Valores acima de 1 não implicam erro de escala: há razões acima de 100% na própria fonte. A validação compara RES com NUM/DEN, sem inferir escala a partir do máximo.
- O indicador 6 em 2013 e a partir de 2018 combina uma descrição de proporção com meta de semanas. Sua escala não é convertida nem sua meta recalculada. O conflito do dicionário fica visível.
- Há resultados negativos e extremos em indicadores de variação e outros campos. Permanecem no conjunto, sem winsorização ou recálculo não documentado.

## Estratégia

Formato longo com tipos categóricos, numeradores/denominadores/resultados em float64 e ano inteiro. O arquivo principal usa Parquet/Zstandard, ocupando 7.903.564 bytes (aproximadamente 7,54 MiB). O dicionário fica separado para não repetir descrições extensas em centenas de milhares de linhas. O arquivo Excel de cerca de 20,9 MiB permanece fora do repositório.

A métrica de agregação apresentada é a fração de metas atingidas entre avaliadas. Não se publica uma média simples dos resultados municipais nem uma razão somada sem estabelecer a validade estatística da operação para cada conceito. Séries com escala original não demonstrada ficam isoladas por ano para impedir uma falsa comparabilidade.

Nenhuma descrição, município, meta ou observação de ano inexistente foi criada. Não foi presumida origem institucional ou data de atualização da fonte além do arquivo fornecido pelo usuário.
