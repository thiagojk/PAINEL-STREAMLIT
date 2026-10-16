"""Uso: python scripts/preparar_dados.py Base_Painel.xlsx [--saida data]."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.data import DIMENSIONS, clean_missing, read_dictionary, wide_to_long


def prepare(source: Path, destination: Path) -> dict:
    excel = pd.ExcelFile(source, engine='openpyxl')
    dictionary = read_dictionary(excel)
    frames, audit = [], {}
    for sheet in excel.sheet_names:
        headers = pd.read_excel(excel, sheet_name=sheet, nrows=0).columns.str.strip().str.upper()
        if not set(DIMENSIONS).issubset(headers):
            continue
        frame = pd.read_excel(excel, sheet_name=sheet, keep_default_na=False, dtype=object)
        frame.columns = headers
        audit[sheet] = {
            'registros': len(frame), 'colunas': list(frame.columns),
            'tipos_originais': frame.dtypes.astype(str).to_dict(),
            'ausentes_por_coluna': {c: int(clean_missing(frame[c]).isna().sum()) for c in frame},
        }
        frames.append(frame)
        print(f'{sheet}: {len(frame):,} registros', flush=True)
    if not frames:
        raise ValueError('Nenhuma aba com dimensões obrigatórias encontrada.')
    wide = pd.concat(frames, ignore_index=True)
    long, catalog = wide_to_long(wide, dictionary)
    years = sorted(int(y) for y in long.ANO.unique())
    metadata = {
        'fonte_arquivo': source.name, 'fonte_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'preparado_em_utc': datetime.now(timezone.utc).isoformat(),
        'atualizacao_fonte': None, 'registros_municipio_ano': len(wide),
        'observacoes': len(long), 'municipios': int(long.COD_MUN.nunique()),
        'ufs': int(long.UF.nunique()), 'anos': years,
        'indicadores_por_ano': {str(y): catalog.loc[catalog.ANO.eq(y), 'INDICADOR'].tolist() for y in years},
        'anos_dicionario_sem_observacoes': sorted(set(int(y) for y in dictionary.ANO) - set(years)),
        'situacoes': {str(k): int(v) for k, v in long.SITUACAO.value_counts().items()},
        'conflitos_meta': int(long.CONFLITO_META.sum()),
        'resultados_ausentes': int(long.RES.isna().sum()),
        'ausentes_por_campo': {c: int(long[c].isna().sum()) for c in long},
        'auditoria_abas': audit,
    }
    destination.mkdir(parents=True, exist_ok=True)
    # Preparar todos os arquivos antes de substituir os dados anteriores.
    with tempfile.TemporaryDirectory(dir=destination) as stage:
        stage = Path(stage)
        long.to_parquet(stage / 'base_pqavs.parquet', index=False, compression='zstd')
        catalog.to_parquet(stage / 'indicadores.parquet', index=False, compression='zstd')
        metadata['parquet_bytes'] = (stage / 'base_pqavs.parquet').stat().st_size
        (stage / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        for name in ['base_pqavs.parquet', 'indicadores.parquet', 'metadata.json']:
            os.replace(stage / name, destination / name)
    print(json.dumps({k: v for k, v in metadata.items() if k != 'auditoria_abas'}, ensure_ascii=False, indent=2))
    return metadata


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('excel', type=Path)
    p.add_argument('--saida', type=Path, default=Path(__file__).resolve().parents[1] / 'data')
    args = p.parse_args()
    prepare(args.excel, args.saida)
