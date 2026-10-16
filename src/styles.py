from html import escape
import streamlit as st
from src.data import ROOT
from src.utils import number, percent


def apply_styles():
    st.html(f'<style>{(ROOT / "assets/style.css").read_text(encoding="utf-8")}</style>')


def header(metadata):
    years = metadata['anos']
    date = '/'.join(reversed(metadata['preparado_em_utc'][:10].split('-')))
    st.html(f'''<header class="system-header"><div class="system-brand"><span class="brand-mark" aria-hidden="true">+</span>
    <div><div class="brand-line">PQAVS <span>Painel de Indicadores e Metas</span></div>
    <div class="brand-caption">Programa de Qualificação das Ações de Vigilância em Saúde</div></div></div>
    <div class="data-stamp"><b>{years[0]}–{years[-1]}</b><span>Base preparada em {date}</span></div></header>''')


def page_heading(title, subtitle):
    st.html(f'<div class="page-heading"><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>')


def kpi_grid(values, small=False):
    st.html('<div class="kpi-grid' + (' kpi-four' if small else '') + '">' + ''.join(
        f'<div class="kpi {tone}"><div class="kpi-label">{escape(label)}</div><div class="kpi-value">{escape(value)}</div><div class="kpi-note">{escape(note)}</div></div>'
        for label, value, note, tone in values) + '</div>')


def cards(frame, summary):
    row = summary.iloc[0] if len(summary) else None
    kpi_grid([
        ('Municípios', number(frame.COD_MUN.nunique()), 'Localidades no recorte', ''),
        ('Estados', number(frame.UF.nunique()), 'Unidades da Federação', ''),
        ('Indicadores', number(frame.INDICADOR.nunique()), 'Disponíveis no recorte', ''),
        ('Metas atingidas', percent(row.CUMPRIMENTO) if row is not None else '—',
         f'{number(row.ATINGIRAM)} de {number(row.AVALIADOS)} avaliadas' if row is not None else 'Entre avaliadas', 'positive'),
        ('Não atingidas', percent(row.NAO_CUMPRIMENTO) if row is not None else '—',
         f'{number(row.NAO_ATINGIRAM)} metas não atingidas' if row is not None else 'Entre avaliadas', 'negative'),
        ('Observações', number(len(frame)), 'Município × indicador × ano', ''),
    ])


def note(text):
    st.html(f'<div class="note">{escape(text)}</div>')


def empty_state(title='Não há dados disponíveis para esta combinação de filtros.', detail='Ajuste o ano, o território ou o indicador para continuar a análise.'):
    st.html(f'<div class="empty-state"><span class="empty-symbol" aria-hidden="true">—</span><h3>{escape(title)}</h3><p>{escape(detail)}</p></div>')


def fact_sheet(title, facts, eyebrow='FICHA DE ANÁLISE'):
    st.html(f'<section class="fact-sheet"><div class="eyebrow">{escape(eyebrow)}</div><h2>{escape(title)}</h2><div class="fact-grid">' +
            ''.join(f'<div><span>{escape(label)}</span><strong>{escape(value)}</strong></div>' for label, value in facts) + '</div></section>')


def indicator_summary(row, show_rule=True):
    rule = f'<small>{escape(str(row.LABEL_META))}</small>' if show_rule else ''
    st.html(f'<div class="indicator-brief"><span title="{escape(str(row.DESCRICAO), quote=True)}">{escape(str(row.DESCRICAO))}</span>{rule}</div>')
