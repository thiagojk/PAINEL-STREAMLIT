# Painel PQAVS

Painel de Indicadores e Metas do Programa de Qualificação das Ações de Vigilância em Saúde. Python + Streamlit + Pandas + Plotly, com dados locais em Parquet. Sem banco de dados, API própria, Node ou serviços pagos.

![Visão geral do painel](docs/screenshots/visao-geral.png)

## O que está disponível

Oito áreas: **Visão Geral**, **Estados**, **Municípios**, **Indicadores**, **Análise Histórica**, **Comparações**, **Tabela de Dados** e **Sobre / Metodologia**. Filtros de ano, UF, município e indicador são dependentes. Comparações permitem até cinco localidades. CSV e XLSX exportam somente o recorte filtrado; a tabela tem paginação.

Base fornecida: `Base_Painel.xlsx`, com **50.112 registros município–ano**, **712.708 observações de indicadores**, **5.570 códigos municipais**, **27 UFs**, **2013–2021** e **15 números de indicador distintos**. O conjunto tem 14 indicadores por ano, exceto 2016–2017, com 15. A numeração muda no tempo; números iguais não garantem conceitos iguais.

O Parquet principal ocupa cerca de **7,54 MiB** (7.903.564 bytes na preparação inicial). Os arquivos tratados estão incluídos no repositório: não é preciso converter o Excel para abrir o painel. O Excel original não é versionado.

## Executar localmente

**Python 3.12 recomendado e validado.** É necessário acesso ao PyPI apenas para instalar dependências. O painel consulta exclusivamente dados locais, sem credenciais ou chamadas externas para exibir análises.

### Windows: dois cliques

Execute `INICIAR_PAINEL.bat`. Ele verifica o Python, cria `.venv`, instala as dependências quando necessário, verifica a instalação e inicia o Streamlit com abertura do navegador. A primeira instalação exige Internet. O BAT foi revisado, mas não executado em uma máquina Windows nesta entrega.

### Windows: manual (Prompt de Comando)

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

No PowerShell, a ativação é `.venv\Scripts\Activate.ps1`. Se a política local impedir ativação, use diretamente `.venv\Scripts\python.exe -m streamlit run app.py`.

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Execute os comandos na raiz do repositório. Interrompa com `Ctrl+C`. Em ambientes remotos, use o encaminhamento de portas oferecido pela plataforma; o onboarding não oferece preview público de localhost.

## Atualizar dados

1. Coloque o novo `Base_Painel.xlsx` na raiz do projeto, mantendo o arquivo original como cópia de segurança. Ele está no `.gitignore`.
2. Com o ambiente virtual ativo, execute:

   ```bash
   python scripts/preparar_dados.py Base_Painel.xlsx
   ```

3. O script lê todas as abas com as dimensões obrigatórias, identifica dinamicamente os campos `IND_XX_*`, limpa ausentes e gera:

   - `data/base_pqavs.parquet`: uma linha por município × indicador × ano;
   - `data/indicadores.parquet`: dicionário por indicador e ano, unidade, escala e alertas;
   - `data/metadata.json`: hash SHA-256 da fonte, data de preparação, contagens e auditoria de todas as colunas.

4. Confira os totais, alertas e o tamanho dos arquivos. Execute os testes. Atualize os valores de referência dos testes de integração **somente após conferir a nova base**. `docs/auditoria_excel.json` descreve o arquivo inicial e não é atualizado automaticamente; a auditoria atual sempre está em `data/metadata.json`.
5. Faça commit dos **três arquivos em `data/`** e envie ao GitHub na branch usada no deploy. Mantenha-os na mesma atualização. O Streamlit Community Cloud acompanha o repositório e atualiza a aplicação; se necessário, reinicie-a no painel de gerenciamento.

A leitura usa `st.cache_data` com assinatura dos arquivos (nome, modificação e tamanho), invalidada ao trocar os dados. A conversão é feita fora do ciclo de interação. O Parquet usa compressão Zstandard e categorias para textos repetidos. O app mantém uma cópia em cache da base tratada; não lê o Excel a cada filtro. Exportações só são preparadas ao solicitar, para poupar memória.

O script valida as novas saídas antes da substituição dos arquivos. Se ele falhar durante a leitura ou transformação, os Parquets anteriores permanecem. Não execute atualizações concorrentes no mesmo diretório. `--saida caminho` permite preparar e conferir em outro diretório antes de substituir o conjunto.

## Metodologia e cuidados

**Cumprimento = atingidas / (atingidas + não atingidas) × 100**. Sem informação é apresentado separadamente e não entra no denominador. Um indicador/ano representa o percentual de municípios que atingiu a meta; com vários indicadores, a unidade passa a ser o par município–indicador. O painel não interpreta esse percentual como municípios que atingiram todas as metas.

- `ALCANCE_META` válido (0/1) tem prioridade; o fallback aceita apenas `META` com “Sim”/“Não”. Zero isolado no campo `META` não é “Não”.
- Foram encontradas **4.784 divergências**, todas no indicador 8 de 2013: `ALCANCE_META=1`, `META=Não`. A origem da divergência não está documentada na planilha. A prioridade é explícita, e ambos os campos mais o sinalizador `CONFLITO_META` estão disponíveis para auditoria/exportação.
- Há **30.261 resultados numéricos ausentes**, embora uma situação da meta possa estar explicitamente registrada. Não se deduz sucesso a partir da ausência de casos ou de denominador zero.
- Códigos municipais são texto. Não criamos o sétimo dígito a partir dos códigos de seis dígitos fornecidos.
- Resultados originais permanecem no Parquet e nas exportações. Uma proporção só é exibida em % quando a definição e a comparação entre resultado e NUM/DEN sustentam a conversão. Outras escalas permanecem originais, com indicação explícita. Nenhuma conversão usa apenas o máximo observado ou o fato de um valor ser menor que 1.
- Não usamos média simples dos resultados municipais como resultado Brasil/UF. Agregações de resultado por soma de numeradores/denominadores não são publicadas sem comprovação de compatibilidade estatística. As comparações de UF usam cumprimento.
- Séries históricas ligam definições textuais iguais após remover número, acentos e pontuação, na mesma unidade validada. Isso permite mudanças de numeração sem unir conceitos diferentes. Por segurança, redações distintas e escalas originais não comprovadas são separadas; estas últimas ficam isoladas por ano. O alcance da série é mostrado no seletor.
- A linha de meta numérica aparece somente para regras percentuais simples com unidade comprovada. Ela não substitui a classificação oficial da fonte.
- Diferenças de cumprimento são expressas em **pontos percentuais**; a variação relativa é identificada separadamente. Alterações do conjunto de indicadores e da cobertura territorial limitam a comparação histórica.

### Limitações da fonte

O dicionário cita 2022, mas **não há dados de observações de 2022**. O indicador 15 só possui observações em 2016–2017; as demais colunas de preenchimento desse indicador foram descartadas. O indicador 8 de 2020–2021 não tem resultado numérico, mas possui alcance informado. Em 2013 e de 2018 em diante, o indicador 6 combina descrição de proporção com rótulo de meta de semanas: a divergência fica sinalizada, sem correção presumida. Valores extremos e denominadores zero são preservados. Em 2019 e 2021 há 5.561 municípios; nos demais anos, 5.570. Não foi imputada a ausência dos nove registros.

A data de atualização da fonte e a procedência institucional do arquivo não foram informadas. O cabeçalho informa a **data de preparação**, e não uma data presumida de atualização dos dados. Mais detalhes em [análise da base](docs/ANALISE_BASE.md) e na página Sobre / Metodologia.

## Estrutura

```text
app.py                       # Entrada e navegação entre oito páginas
src/
  data.py                    # Leitura, limpeza, escalas, dicionário e cache
  filters.py                 # Filtros dependentes e séries históricas
  metrics.py                 # Cumprimento, rankings e variação histórica
  charts.py                  # Plotly e tooltips
  styles.py                  # Identidade visual e cards
  views.py                   # Oito páginas e exportações
  utils.py                   # Formatação brasileira
scripts/
  preparar_dados.py           # Excel → Parquet e auditoria
  iniciar_local.py            # Auxiliar do BAT
assets/                      # CSS e ícone local
.streamlit/config.toml       # Tema claro e configurações
requirements.txt             # Dependências de execução com versões fixadas
requirements-dev.txt         # pytest e Playwright
INICIAR_PAINEL.bat            # Inicialização Windows
data/                       # Parquets e metadados versionados
docs/                       # Auditoria, validação e screenshots
tests/                      # Testes de dados e páginas
```

As oito páginas são funções organizadas em `src/views.py`, com navegação única em `app.py`. Isso permite filtros e estilo compartilhados sem repetir código em oito scripts. Não há um backend separado.

## Publicar no Streamlit Community Cloud

1. Envie o projeto e os três arquivos de `data/` ao GitHub.
2. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte sua conta GitHub.
3. Selecione o repositório **thiagojk/PAINEL-STREAMLIT**.
4. Selecione a branch **main** e o arquivo **app.py**.
5. Nas opções avançadas, selecione **Python 3.12**.
6. Faça o deploy.

O app não exige banco, Docker, segredos, servidor externo ou plano pago. O Parquet principal tem menos de 8 MiB, abaixo do limite de 100 MiB por arquivo Git comum do GitHub. O mapa foi omitido para priorizar ranking estável, sem downloads de geometria. XLSX fica limitado a recortes de 100 mil linhas para reduzir consumo de memória; CSV permanece disponível. A validação foi feita neste ambiente Linux; o deploy real no Community Cloud depende da sua conta e não foi executado aqui.

## Testes

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall .
```

Os testes cobrem limpeza, detecção de novos indicadores, códigos com zeros iniciais, status e conflitos, filtros, conversão Excel/Parquet, repetibilidade, agregações, rankings, séries/renumeração e as oito páginas via `streamlit.testing.v1.AppTest`. Os testes da base real verificam contagens específicas do arquivo inicial; atualizações legítimas exigem revisar essas expectativas.

A validação em navegador Chromium cobre navegação, filtros, trajetória, comparação, downloads CSV/XLSX e tamanhos de tela. Veja [validação](docs/VALIDACAO.md) e [screenshots](docs/screenshots/).

Para repetir a validação de navegador, inicie o app na porta 8502 e, em outro terminal:

```bash
python -m playwright install chromium
python scripts/validar_interface.py
```

Se já houver Chromium instalado, use `python scripts/validar_interface.py --chromium /caminho/do/chromium` e dispense o download. A porta pode ser alterada com `--url`. As capturas são gravadas em `docs/screenshots/` e o relatório em `docs/validacao_navegador.json`.
