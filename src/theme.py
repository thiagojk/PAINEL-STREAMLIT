"""Tokens únicos: interface, situações oficiais e escalas analíticas."""
PRIMARY = '#176B78'
PRIMARY_DARK = '#123E52'
PRIMARY_LIGHT = '#E7F1F3'
POSITIVE = '#147D73'
NEGATIVE = '#B45B44'
NEUTRAL = '#AFBAC4'
TEXT_PRIMARY = '#17384B'
TEXT_SECONDARY = '#526779'
BACKGROUND = '#F1F5F8'
SURFACE = '#FFFFFF'
BORDER = '#D5E1E8'
SECONDARY = '#405D91'
SHADOW = '#17384B0A'
CHART_1 = PRIMARY
CHART_2 = SECONDARY
CHART_3 = '#8A6530'
CHART_4 = '#79538C'
CHART_5 = '#496D51'
PALETTE = [CHART_1, CHART_2, CHART_3, CHART_4, CHART_5]
COLORS = {'Atingida': POSITIVE, 'Não atingida': NEGATIVE, 'Sem informação': NEUTRAL}
# Luminância decrescente; sem centro artificial ou oposição vermelho × verde.
MAP_SCALE = [[0, '#EDF6F3'], [.25, '#BDDDD3'], [.5, '#7DB9AB'], [.75, '#398E80'], [1, '#116357']]
# Mapas reutilizam a semântica global; categorias nunca viram um gradiente.
MAP_STATUS_REACHED = POSITIVE
MAP_STATUS_NOT_REACHED = NEGATIVE
MAP_STATUS_MISSING = NEUTRAL
MAP_STATUS_COLORS = {'Atingida': MAP_STATUS_REACHED, 'Não atingida': MAP_STATUS_NOT_REACHED, 'Sem informação': MAP_STATUS_MISSING}
MAP_PROGRESS_SCALE = MAP_SCALE
TOKENS = {k: v for k, v in list(globals().items()) if k.isupper() and isinstance(v, str)}

def css_variables():
    values = {**TOKENS, 'INK': TEXT_PRIMARY, 'MUTED': TEXT_SECONDARY, 'TEAL': PRIMARY, 'LINE': BORDER}
    return ':root {' + ''.join(f'--{k.lower().replace("_", "-")}:{v};' for k,v in values.items()) + '--map-gradient:linear-gradient(90deg,' + ','.join(c for _,c in MAP_SCALE) + ');}'
