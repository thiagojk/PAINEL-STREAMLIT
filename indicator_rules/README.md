# Registro temporal

- `historical.json`: 2013–2021, `source_only`; usa o catálogo anual e as situações da fonte. Não cadastra incentivo, aplicabilidade ou classificação universal/específica.
- `2025.json`: a partir de 2025, `reference_only`; contém apenas informações transcritas no pedido. Não é cadastro operacional validado.

Configurações não podem se sobrepor. Para registrar uma revisão futura, delimite o fim da versão anterior. A função `version_for_year` rejeita períodos ambíguos.

Um cadastro futuro validado pode conter, em cada item de `indicators`:

- `concept_id`, `number`, `name` e `series_ids` (identificadores exatos aceitos naquele período);
- `category` (`universal` ou `specific`), `target` e `source`;
- `evaluation.direction`: `GREATER_EQUAL`, `LESS_EQUAL`, `REDUCTION_FROM_BASELINE`, `MAINTAIN_ZERO` ou `COMPOSITE`, com parâmetros, referência do ano-base e componentes quando necessários.

Esses tipos representam a regra, sem um avaliador que transforme todas as metas em `resultado >= alvo`. A camada histórica continua usando `SITUACAO`, calculada pelo pipeline original: flag válida `ALCANCE_META`, depois Sim/Não de `META`. Nenhuma regra nova recalcula retrospectivamente os dados.

A API `classify_state_incentive` exige estado `validated`, fonte, `applicability_policy_validated=true` e política explícita `missing_policy=require_complete`. O chamador deve fornecer:

1. observações de um único estado e ano, sem duplicatas e com séries aceitas;
2. universo municipal oficial completo;
3. tabela `COD_MUN`, `INDICADOR`, `APLICAVEL`, com booleano explícito para cada combinação do universo e indicadores cadastrados, inclusive não aplicáveis;
4. situações conhecidas para todas as combinações aplicáveis e ao menos um indicador aplicável por município.

Qualquer ausência impede a classificação. O maior patamar estadual satisfeito é retornado apenas depois dessas validações. A referência distribuída não satisfaz os requisitos e não produz classificação. Os testes de funcionamento futuro usam configurações e dados sintéticos, não aplicados ao dashboard histórico.

`category_summary` também exige versão validada, ano correto e correspondência de indicador **e série**. Não há classificação por mera coincidência do número.

Referência informada: Ministério da Saúde, Programa de Qualificação das Ações de Vigilância em Saúde — PQA-VS, cartilha com indicadores/metas aplicáveis a partir de 2025, Portaria GM/MS nº 6.878/2025. A referência atual não comprova a regra de incentivo de 2013–2021 nem fornece, nesta tarefa, um cadastro completo de aplicabilidade.

## Proximidade complementar 2013–2021

`progress_rules` é separado de `indicators`: não modifica os gates oficiais. Cada entrada anual fixa número, série, descrição, unidade, meta, direção, fórmula, suporte, grupo de comparação e justificativa. O cadastro atual habilita somente `GREATER_EQUAL` + `ratio_to_positive_target` para proporções percentuais sustentadas no catálogo e no pipeline. Não deriva suporte do número do indicador. Não modificar o status `source_only` para habilitar esta visualização.

`src/target_progress.py` confere o cadastro e os dados do registro. O resultado é proximidade descritiva, com cap visual, e não avaliação oficial. Direções inversas, baseline, zero e composição continuam sem transformação habilitada. Tabela completa em `docs/GRAU_ALCANCE_INDICADORES.md`; auditoria reproduzível: `python scripts/auditar_grau_alcance.py`.
