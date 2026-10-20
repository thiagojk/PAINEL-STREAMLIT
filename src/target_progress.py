"""Proximidade complementar da meta: nunca substitui SITUACAO/ALCANCE_META.

Regras são explicitamente cadastradas por ano, número E série. Fonte primária:
catálogo anual; unidades foram verificadas em NUM/DEN no pipeline existente.
Nenhuma agregação estadual ou média municipal é produzida aqui.
"""
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd
import streamlit as st
from src.data import file_signature
from src.rules import version_for_year

@dataclass(frozen=True)
class Progress:
    actual: float | None
    visual: float | None
    valid: bool
    reason: str


def progress_rule(entry):
    version = version_for_year(int(entry.ANO))
    if not version:
        return None
    rules = [r for r in version.get('progress_rules', []) if
             (r['year'],r['number'],r['series_id'],r['target_label'],r['unit'],r['description']) ==
             (int(entry.ANO),entry.INDICADOR,entry.SERIE,entry.LABEL_META,entry.UNIDADE,entry.DESCRICAO)]
    if len(rules) > 1:
        raise ValueError('Regra de proximidade ambígua.')
    if not rules:
        return None
    rule=rules[0]
    if rule['supports_progress_map'] and (pd.isna(entry.META_NUMERICA) or entry.META_NUMERICA != rule['target']):
        return None
    return rule


def calculate_target_progress(result, target, rule, baseline=None):
    """Retorna valor real, cap visual e motivo; direção inversa não é inferida.

    O baseline é aceito para extensibilidade, mas não há fórmula de redução,
    crescimento temporal, manutenção de zero ou composta validada na base.
    """
    def unavailable(reason): return Progress(None,None,False,reason)
    if not rule or not rule.get('supports_progress_map'):
        return unavailable((rule or {}).get('justification','Indicador sem transformação validada.'))
    direction = rule.get('target_rule')
    if direction == 'REDUCTION_FROM_BASELINE':
        return unavailable('Baseline ausente.' if baseline is None else 'Transformação de baseline não validada.')
    if direction != 'GREATER_EQUAL' or rule.get('progress_rule') != 'ratio_to_positive_target':
        return unavailable('Direção inversa, manutenção de zero ou regra composta sem transformação validada.')
    def finite(value):
        try: return value is not None and math.isfinite(float(value))
        except (TypeError,ValueError): return False
    if not finite(result): return unavailable('Resultado ausente ou não finito.')
    if not finite(target) or target <= 0: return unavailable('Meta ausente ou não positiva.')
    if result < 0: return unavailable('Resultado negativo incompatível com a proporção.')
    actual = 100 * float(result) / float(target)
    if not math.isfinite(actual): return unavailable('Razão não finita.')
    return Progress(actual,min(100.,actual),True,'')


def continuous_compatibility(entries):
    rules = [progress_rule(row) for row in entries.itertuples()]
    if not rules or any(not r or not r['supports_progress_map'] for r in rules):
        return False, 'Há anos sem transformação validada; cada ano indisponível permanece sinalizado.'
    if entries.SERIE.nunique() != 1 or len({r['comparison_group'] for r in rules}) != 1:
        return False, 'Séries ou transformações incompatíveis para comparação contínua.'
    return True, ''


@st.cache_data(show_spinner=False,max_entries=48)
def progress_layer(layer, entry, signature):
    """Cache sem geometria: usa a camada municipal já associada e a regra anual."""
    rule = progress_rule(entry)
    output = layer.copy()
    values=[]
    for r in layer.itertuples():
        value=calculate_target_progress(r.RES_EXIBICAO,(rule or {}).get('target'),rule)
        if value.valid:
            # Numerador/denominador confirmam a escala deste registro. DEN=0
            # não vira sucesso nem zero; RES original continua na exportação.
            expected = r.NUM / r.DEN * 100 if pd.notna(r.DEN) and np.isfinite(r.DEN) and r.DEN>0 and pd.notna(r.NUM) and np.isfinite(r.NUM) else np.nan
            if not np.isfinite(expected) or r.NUM < 0 or not np.isclose(r.RES_EXIBICAO,expected,rtol=.015,atol=.51):
                value=Progress(None,None,False,'Resultado sem suporte consistente em numerador/denominador.')
        values.append(value)
    output['GRAU_REAL']=[v.actual for v in values]
    output['GRAU_VISUAL']=[v.visual for v in values]
    output['GRAU_VALIDO']=[v.valid for v in values]
    output['GRAU_MOTIVO']=[v.reason for v in values]
    return output


def progress_signature():
    from src.rules import ROOT
    path=ROOT/'indicator_rules/historical.json'
    return file_signature(),path.stat().st_mtime_ns,path.stat().st_size
