from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape

PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)

COLOR_PRIMARY = colors.HexColor("#1A365D")
COLOR_SECONDARY = colors.HexColor("#C5A059")
COLOR_TEXT_DARK = colors.HexColor("#2D3748")
COLOR_TEXT_MUTED = colors.HexColor("#718096")
COLOR_BG_ACCENT = colors.HexColor("#F7FAFC")

BORDER_MARGIN_OUTER = 28
BORDER_MARGIN_INNER = 36
