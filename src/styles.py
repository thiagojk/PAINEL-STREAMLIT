from html import escape
import streamlit as st
from src.data import ROOT
from src.utils import number, percent


def apply_styles():
    st.html(f'<style>{(ROOT / "assets/style.css").read_text(encoding="utf-8")}</style>')


def header(title, subtitle, metadata):
    years = metadata['anos']
    prepared = metadata['preparado_em_utc'][:10].split('-')
    date = '/'.join(reversed(prepared))
    st.html(f'''<div class="hero"><div class="eyebrow">PQAVS · Vigilância em Saúde</div>
    <h1>{escape(title)}</h1><p>{escape(subtitle)}</p>
    <span class="pill">Série disponível · {years[0]}–{years[-1]}</span>
    <span class="pill">Base preparada em {date}</span></div>''')


def cards(frame, summary):
    row = summary.iloc[0] if len(summary) else None
    values = [
        ('Municípios', number(frame.COD_MUN.nunique()), 'Localidades no recorte', ''),
        ('Estados', number(frame.UF.nunique()), 'Unidades da Federação', ''),
        ('Indicadores', number(frame.INDICADOR.nunique()), 'Disponíveis no recorte', ''),
        ('Metas atingidas', percent(row.CUMPRIMENTO) if row is not None else '—', 'Entre metas avaliadas', 'positive'),
        ('Não atingidas', percent(row.NAO_CUMPRIMENTO) if row is not None else '—', 'Entre metas avaliadas', 'negative'),
        ('Observações', number(len(frame)), 'Município × indicador × ano', ''),
    ]
    st.html('<div class="kpi-grid">' + ''.join(
        f'<div class="kpi {tone}"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>'
        for label, value, note, tone in values) + '</div>')


def note(text):
    st.html(f'<div class="note">{escape(text)}</div>')
