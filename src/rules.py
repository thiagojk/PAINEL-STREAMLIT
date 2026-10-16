"""Registro temporal separado do pipeline histórico; referência não ativa regras."""
from enum import Enum
from functools import lru_cache
import json
from pathlib import Path
import pandas as pd
from src.data import ROOT, STATUS


class GoalDirection(str, Enum):
    GREATER_EQUAL = 'GREATER_EQUAL'
    LESS_EQUAL = 'LESS_EQUAL'
    REDUCTION_FROM_BASELINE = 'REDUCTION_FROM_BASELINE'
    MAINTAIN_ZERO = 'MAINTAIN_ZERO'
    COMPOSITE = 'COMPOSITE'


@lru_cache(maxsize=4)
def _load_versions(signature):
    return tuple(json.loads(Path(path).read_text(encoding='utf-8')) for path, _, _ in signature)


def load_versions(directory=ROOT / 'indicator_rules'):
    signature = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in sorted(Path(directory).glob('*.json')))
    # Entregar cópias: um consumidor não pode ativar acidentalmente a referência.
    return json.loads(json.dumps(_load_versions(signature)))


def version_for_year(year, versions=None):
    candidates = [v for v in (load_versions() if versions is None else versions)
                  if v['start_year'] <= year <= (v['end_year'] if v['end_year'] is not None else float('inf'))]
    if len(candidates) > 1:
        raise ValueError('Configurações metodológicas sobrepostas.')
    return candidates[0] if candidates else None


def indicator_rule(year, concept_id, number, versions=None):
    """Sem fallback por número; conceito E período precisam coincidir."""
    version = version_for_year(year, versions)
    if version is None or version['status'] != 'validated':
        return None
    matches = [r for r in version['indicators'] if r['concept_id'] == concept_id and r['number'] == number]
    if len(matches) > 1:
        raise ValueError('Regra de indicador ambígua.')
    if not matches:
        return None
    rule = matches[0]
    GoalDirection(rule['evaluation']['direction'])  # Não presume threshold crescente.
    return rule


def category_summary(frame, year, versions=None):
    """Opcional para configuração futura validada, nunca inferido de numeração."""
    from src.metrics import summarize
    version = version_for_year(year, versions)
    if version is None or version['status'] != 'validated' or set(frame.ANO) != {year}:
        return pd.DataFrame()
    if len(version['indicators']) != version.get('reference_counts',{}).get('indicators'):
        return pd.DataFrame()
    rules = [r for r in version['indicators'] if indicator_rule(year,r['concept_id'],r['number'],[version]) is not None]
    metadata = []
    for rule in rules:
        for series in rule['series_ids']:
            metadata.append({'INDICADOR':rule['number'], 'SERIE':series, 'CATEGORIA':rule['category']})
    if not metadata:
        return pd.DataFrame()
    labels = pd.DataFrame(metadata)
    if labels.duplicated(['INDICADOR','SERIE']).any():
        raise ValueError('Classificação de categoria ambígua.')
    joined = frame.merge(labels, on=['INDICADOR','SERIE'], how='inner', validate='many_to_one')
    if len(joined) != len(frame) or not joined.CATEGORIA.isin(['universal','specific']).all():
        return pd.DataFrame()
    return summarize(joined, ['CATEGORIA'])


def classify_state_incentive(year, frame, applicability=None, municipality_universe=None, versions=None):
    """Retorna None até haver regra, aplicabilidade e cobertura oficiais completas.

    applicability exige uma linha explícita (bool APLICAVEL) por município ×
    indicador, inclusive não aplicáveis. Nenhum missing recebe regra implícita.
    Atualmente nenhuma configuração distribuída está habilitada para classificar.
    """
    v = version_for_year(year, versions)
    if not v or v['status'] != 'validated' or not v.get('state_incentive'):
        return None
    if not v.get('source') or not v.get('applicability_policy_validated') or v.get('missing_policy') != 'require_complete':
        return None
    if not v.get('indicators') or applicability is None or municipality_universe is None or frame.empty:
        return None
    if frame.UF.nunique() != 1 or set(frame.ANO) != {year}:
        return None
    municipalities = set(municipality_universe)
    numbers = {r['number'] for r in v['indicators']}
    if (len(numbers) != len(v['indicators']) or len(numbers) != v.get('reference_counts',{}).get('indicators')
            or not municipalities or set(frame.COD_MUN) != municipalities or not set(frame.INDICADOR).issubset(numbers)):
        return None
    a = applicability.copy()
    if not {'COD_MUN','INDICADOR','APLICAVEL'}.issubset(a) or a.duplicated(['COD_MUN','INDICADOR']).any():
        return None
    expected = pd.MultiIndex.from_product([sorted(municipalities), sorted(numbers)])
    actual = pd.MultiIndex.from_frame(a[['COD_MUN','INDICADOR']])
    if len(actual) != len(expected) or set(actual) != set(expected):
        return None
    if a.APLICAVEL.isna().any() or not a.APLICAVEL.map(lambda x:isinstance(x,bool)).all():
        return None
    selected = a.loc[a.APLICAVEL, ['COD_MUN','INDICADOR']]
    if frame.duplicated(['COD_MUN','INDICADOR']).any():
        return None
    # Mesmo número em outra definição não satisfaz a configuração oficial.
    for r in v['indicators']:
        subset = frame[frame.INDICADOR.eq(r['number'])]
        if not subset.SERIE.isin(r['series_ids']).all():
            return None
        if indicator_rule(year, r['concept_id'], r['number'], [v]) is None:
            return None
    observed = selected.merge(frame[['COD_MUN','INDICADOR','SITUACAO']], on=['COD_MUN','INDICADOR'], how='left', validate='one_to_one')
    if not observed.SITUACAO.isin(STATUS[:2]).all():
        return None
    profiles = observed.assign(ATINGIU=observed.SITUACAO.eq(STATUS[0])).groupby('COD_MUN').ATINGIU.agg(['sum','size'])
    if set(profiles.index) != municipalities or (profiles['size'] == 0).any():
        return None
    share = 100 * profiles['sum'] / profiles['size']
    tiers = [t['incentive'] for t in v['state_incentive'] if 100*share.ge(t['indicator_share']).mean() >= t['municipal_share']]
    return {'incentive':max(tiers, default=0), 'rule_id':v['id'], 'year':year, 'municipalities':len(share)}
