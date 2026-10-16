# Validação da entrega

Executada em Linux, Python 3.12.14, com as versões de `requirements.txt`.

## Dados e testes

- `python -m pytest -q`: **21 testes aprovados** (12 de dados/métricas/pipeline e 9 de páginas/filtros).
- `python -m compileall .`: concluído sem erros.
- `python -m pip check`: nenhuma dependência quebrada.
- Conversão do Excel real concluída; a conversão foi repetida após a correção da leitura de códigos textuais. O teste de roundtrip também verifica repetibilidade e zeros iniciais.
- 712.708 observações únicas por ano, código municipal e indicador. Totais, 4.784 conflitos de meta, renumeração e ausência de resultados foram conferidos nos testes de integração.
- O dataframe principal ocupa aproximadamente **41,64 MiB** em memória profunda. Isso não mede o consumo total do processo nem garante a cota de uma hospedagem externa.

## Aplicação

O servidor Streamlit foi iniciado e respondeu a requisições HTTP de página e saúde. As oito páginas foram executadas com `AppTest`, verificando ausência de exceções e de mensagens de erro da aplicação. Filtros foram exercitados com PA/Belém, troca para AC, indicador 15 em 2016 e retorno a 2021, e trajetória de Acrelândia.

A validação de navegador em Chromium executou os 12 cenários descritos em `validacao_navegador.json`, com **zero erros JavaScript**:

- navegação nas oito páginas, cards, tabelas e gráficos;
- filtros dependentes com reset de município;
- ficha municipal e série histórica com linha de meta;
- comparações por UF e município;
- downloads CSV e XLSX, lidos novamente e conferidos para conter apenas o município filtrado;
- visualização em 1440px, 768px e 390px, sem transbordamento horizontal da página em celular.

As capturas foram inspecionadas. A checagem revelou colunas de gráficos comprimidas em tablet e o cabeçalho sob a barra superior; o CSS foi corrigido para empilhar análises abaixo de 1100px e reservar espaço no topo. Cards reorganizam-se em grades de seis, três ou duas colunas. O relatório e as capturas são reproduzíveis por `scripts/validar_interface.py`.

## Limites da validação

O BAT foi revisado, mas não foi executado em Windows. A hospedagem real no Streamlit Community Cloud não foi realizada; requer a conta do proprietário. O mapa é opcional e foi omitido para manter o app sem downloads de geometria. Dados de 2022 não estão disponíveis. A publicação do ambiente de desenvolvimento e o deploy do dashboard são ações distintas, e nenhum deles é comprovado apenas por um teste local.
