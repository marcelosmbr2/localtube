"""Tokens de cor e tipografia do mockup e a folha de estilo global (QSS)."""

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

FONTS_DIR = Path(__file__).parent / "resources" / "fonts"
CHEVRON_SVG = Path(__file__).parent / "resources" / "chevron-down.svg"

UI_FONT = "Inter"
MONO_FONT = "JetBrains Mono"

# Superfícies
BG_WINDOW = "#0f0f11"
BG_CHROME = "#0b0b0d"
BG_PANEL = "#0d0d0f"
BG_FOOTER = "#0c0c0e"
BG_INPUT = "#121215"
BG_CARD = "#111114"
BG_SEGMENT = "#141417"
BG_BUTTON = "#1a1a1e"
BG_BUTTON_HOVER = "#212126"
BG_HOVER = "#1a1a1e"
BG_ROW_HOVER = "#16161a"
BG_SELECTED = "#1e1e23"
BG_SEGMENT_ON = "#25252b"
BG_ICON_BOX = "#18181c"
BG_TOAST = "#1b1b1f"
BG_PALETTE = "#151518"
BG_SKELETON = "#17171a"
BG_SKELETON_2 = "#1a1a1e"
BG_TRACK = "#222227"

# Bordas
BORDER = "#1e1e22"
BORDER_ROW = "#1c1c20"
BORDER_CARD = "#222227"
BORDER_INPUT = "#26262c"
BORDER_SEGMENT = "#24242a"
BORDER_STRONG = "#2a2a30"
BORDER_HOVER = "#33333b"

# Texto
TEXT = "#ededef"
TEXT_2 = "#dcdce0"
TEXT_3 = "#c9c9cf"
TEXT_4 = "#a1a1aa"
TEXT_5 = "#8b8b95"
TEXT_6 = "#7c7c86"
TEXT_7 = "#6e6e78"
TEXT_8 = "#5c5c66"
TEXT_9 = "#55555e"

# Destaques
ACCENT = "#f07152"
ACCENT_HOVER = "#f4846a"
ACCENT_TEXT = "#f5866d"
ON_ACCENT = "#1a0e0a"
GREEN = "#4fbf87"
GREEN_TEXT = "#6fd19f"
AMBER = "#e0a84a"
RED = "#e5484d"
RED_TEXT = "#f0777a"
RING = "#3a3a42"
TOGGLE_OFF = "#2a2a30"


def load_fonts() -> None:
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(path))


def ui_font(px: float = 13, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(UI_FONT)
    font.setPixelSize(round(px))
    font.setWeight(weight)
    return font


def mono_font(px: float = 11.5, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(MONO_FONT)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(round(px))
    font.setWeight(weight)
    return font


def section_font() -> QFont:
    font = ui_font(11, QFont.Weight.DemiBold)
    font.setCapitalization(QFont.Capitalization.AllUppercase)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.66)
    return font


def build_stylesheet() -> str:
    return f"""
* {{ outline: none; }}
QWidget {{ color: {TEXT}; font-family: "{UI_FONT}"; font-size: 13px; }}
QMainWindow, #Central {{ background: {BG_WINDOW}; }}
QToolTip {{ background: {BG_TOAST}; color: {TEXT_2}; border: 1px solid #2c2c33; padding: 4px 6px; }}

/* Estrutura */
#TopBar {{ background: {BG_CHROME}; border-bottom: 1px solid {BORDER}; }}
#Sidebar {{ background: {BG_CHROME}; border-right: 1px solid {BORDER}; }}
#SidebarFooter {{ border-top: 1px solid {BORDER_ROW}; }}
#PageHeader {{ border-bottom: 1px solid {BORDER}; }}
#SidePanel {{ background: {BG_PANEL}; border-left: 1px solid {BORDER}; }}
#Footer {{ background: {BG_FOOTER}; border-top: 1px solid {BORDER}; }}
#PageTitle {{ font-size: 15px; font-weight: 600; }}
#PageSubtitle {{ font-size: 12px; color: {TEXT_6}; }}

QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: 0; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle {{ background: #26262c; border-radius: 2px; border: 3px solid transparent; }}
QScrollBar::handle:vertical {{ min-height: 24px; margin: 3px; border: 0; border-radius: 2px; }}
QScrollBar::handle:horizontal {{ min-width: 24px; margin: 3px; border: 0; border-radius: 2px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* Botões */
QPushButton {{
    height: 32px; padding: 0 12px; background: {BG_BUTTON}; border: 1px solid {BORDER_STRONG};
    border-radius: 7px; color: {TEXT}; font-size: 12.5px; font-weight: 500;
}}
QPushButton:hover {{ background: {BG_BUTTON_HOVER}; }}
QPushButton:disabled {{ color: {TEXT_7}; }}
QPushButton[variant="primary"] {{
    background: {ACCENT}; border-color: {ACCENT}; color: {ON_ACCENT}; font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton[variant="primary"]:disabled {{ background: rgba(240,113,82,.45); border-color: rgba(240,113,82,.0); color: {ON_ACCENT}; }}
QPushButton[variant="outline"] {{ background: transparent; color: {TEXT_4}; }}
QPushButton[variant="outline"]:hover {{ background: #18181c; color: {TEXT}; }}
QPushButton[variant="ghost"] {{ background: transparent; border: 0; color: {TEXT_4}; padding: 0 8px; font-size: 12px; border-radius: 5px; }}
QPushButton[variant="ghost"]:hover {{ background: #1e1e23; color: {TEXT}; }}
QPushButton[variant="link"] {{ background: transparent; border: 0; color: {TEXT_5}; padding: 0; font-size: 12px; }}
QPushButton[variant="link"]:hover {{ color: {TEXT}; }}
QPushButton[variant="accentLink"] {{ background: transparent; border: 0; color: {ACCENT}; padding: 0; font-size: 11.5px; font-weight: 400; }}
QPushButton[variant="accentLink"]:hover {{ color: {ACCENT_TEXT}; }}
QPushButton[size="lg"] {{ height: 36px; border-radius: 8px; font-size: 13px; padding: 0 14px; }}
QPushButton[size="sm"] {{ height: 28px; border-radius: 6px; font-size: 12px; padding: 0 10px; }}

QToolButton[variant="icon"] {{ background: transparent; border: 1px solid transparent; border-radius: 6px; }}
QToolButton[variant="icon"]:hover {{ background: #1e1e23; }}
QToolButton[variant="iconOutline"] {{ background: transparent; border: 1px solid transparent; border-radius: 6px; }}
QToolButton[variant="iconOutline"]:hover {{ background: #18181c; border-color: {BORDER_INPUT}; }}

#PaletteButton {{
    background: {BG_PALETTE}; border: 1px solid {BORDER_SEGMENT}; border-radius: 7px;
}}
#PaletteButton:hover {{ border-color: #30303a; }}

/* Controle segmentado */
#Segmented {{ background: {BG_SEGMENT}; border: 1px solid {BORDER_SEGMENT}; border-radius: 7px; }}
#Segmented[tone="dark"] {{ background: {BG_PANEL}; }}
#Segmented QPushButton {{
    height: 24px; padding: 0 11px; background: transparent; border: 0; border-radius: 5px;
    color: {TEXT_5}; font-size: 12px; font-weight: 500;
}}
#Segmented QPushButton:hover {{ color: {TEXT_3}; }}
#Segmented QPushButton:checked {{ background: {BG_SEGMENT_ON}; color: {TEXT}; }}
#Segmented QPushButton:disabled {{ color: {TEXT_8}; }}
#Segmented[size="lg"] QPushButton {{ height: 26px; }}

/* Campos */
QLineEdit {{
    background: {BG_INPUT}; border: 1px solid {BORDER_INPUT}; border-radius: 7px;
    padding: 0 10px; height: 30px; color: {TEXT_3}; selection-background-color: rgba(240,113,82,.35);
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}
QLineEdit[mono="true"] {{ font-family: "{MONO_FONT}"; font-size: 11.5px; }}
QLineEdit[tone="dark"] {{ background: {BG_PANEL}; border-radius: 6px; height: 28px; }}
QLineEdit[bare="true"] {{ background: transparent; border: 0; padding: 0; height: 100%; color: {TEXT}; }}
QLineEdit:disabled {{ color: {TEXT_7}; }}
#UrlField {{ background: {BG_INPUT}; border: 1px solid {BORDER_STRONG}; border-radius: 8px; }}
#UrlField[focused="true"] {{ border-color: {ACCENT}; }}
#SearchField {{ background: {BG_INPUT}; border: 1px solid {BORDER_INPUT}; border-radius: 7px; }}
#SearchField[focused="true"] {{ border-color: {ACCENT}; }}
#PathField {{ background: {BG_INPUT}; border: 1px solid {BORDER_INPUT}; border-radius: 7px; }}
#PathField[tone="dark"] {{ background: {BG_PANEL}; border-radius: 6px; }}

QComboBox {{
    background: {BG_INPUT}; border: 1px solid {BORDER_INPUT}; border-radius: 7px; height: 30px;
    padding: 0 10px; color: {TEXT_2}; combobox-popup: 0;
}}
QComboBox:hover {{ border-color: {BORDER_HOVER}; }}
QComboBox[tone="dark"] {{ background: {BG_PANEL}; border-radius: 6px; height: 28px; font-size: 12.5px; }}
QComboBox::drop-down {{ border: 0; width: 24px; }}
QComboBox::down-arrow {{ image: url("{CHEVRON_SVG.as_posix()}"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {BG_PALETTE}; border: 1px solid #2c2c33; padding: 4px; color: {TEXT_2};
    selection-background-color: #1f1f24; selection-color: {TEXT}; outline: 0;
}}

QSlider::groove:horizontal {{ height: 4px; background: {BG_TRACK}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {TEXT}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}

/* Cartões e linhas */
#Card {{ background: {BG_CARD}; border: 1px solid {BORDER_CARD}; border-radius: 10px; }}
#Card[radius="9"] {{ border-radius: 9px; background: {BG_INPUT}; }}
#Card[plain="true"] {{ background: transparent; }}
#CardRow[divider="true"] {{ border-top: 1px solid {BORDER_ROW}; }}
#CardRow[clickable="true"]:hover {{ background: {BG_ROW_HOVER}; }}
#CardRow[selected="true"] {{ background: rgba(240,113,82,.06); }}
#CardRow[first="true"] {{ border-top-left-radius: 9px; border-top-right-radius: 9px; }}
#CardRow[last="true"] {{ border-bottom-left-radius: 9px; border-bottom-right-radius: 9px; }}

/* Barra lateral */
#NavItem {{ border-radius: 6px; background: transparent; }}
#NavItem:hover {{ background: {BG_HOVER}; }}
#NavItem[active="true"] {{ background: {BG_SELECTED}; }}
#NavCount {{ background: rgba(240,113,82,.14); color: {ACCENT_TEXT}; border-radius: 9px; font-size: 11px; font-weight: 600; padding: 0 5px; }}
#TableHeader {{ background: {BG_INPUT}; }}
#TableHeader QLabel {{ font-size: 11px; font-weight: 600; color: {TEXT_7}; }}
#IconBox {{ background: {BG_ICON_BOX}; border: 1px solid {BORDER_SEGMENT}; border-radius: 7px; }}

#DropZone {{ background: {BG_CARD}; border: 1.5px dashed #2c2c33; border-radius: 10px; }}
#DropZone:hover, #DropZone[dragging="true"] {{ background: #131317; border-color: #3d3d46; }}

#Chip {{ border: 1px solid {BORDER_STRONG}; border-radius: 5px; background: {BG_PALETTE}; color: {TEXT_4}; font-size: 11px; padding: 0 8px; }}
#Chip[tone="green"] {{ border-color: rgba(79,191,135,.3); background: rgba(79,191,135,.08); color: {GREEN_TEXT}; }}
#Badge {{ border-radius: 4px; background: rgba(240,113,82,.12); color: {ACCENT_TEXT}; font-size: 10.5px; font-weight: 500; padding: 1px 6px; }}
#Kbd {{ font-size: 10.5px; color: {TEXT_7}; padding: 0 5px; border: 1px solid {BORDER_STRONG}; border-radius: 4px; background: {BG_CARD}; }}

/* Sobreposições */
#Toast {{ background: {BG_TOAST}; border: 1px solid #2c2c33; border-radius: 9px; }}
#PalettePanel {{ background: {BG_PALETTE}; border: 1px solid #2c2c33; border-radius: 12px; }}
#PaletteHeader {{ border-bottom: 1px solid {BORDER_CARD}; }}
#PaletteFooter {{ background: {BG_INPUT}; border-top: 1px solid {BORDER_CARD}; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }}
#PaletteItem {{ border-radius: 7px; }}
#PaletteItem[active="true"], #PaletteItem:hover {{ background: #1f1f24; }}
#PaletteIcon {{ background: #1c1c21; border: 1px solid {BORDER_INPUT}; border-radius: 6px; }}

/* Biblioteca */
QTableView {{ background: transparent; border: 0; gridline-color: transparent; selection-background-color: transparent; }}
QHeaderView {{ background: {BG_WINDOW}; border: 0; }}
QHeaderView::section {{
    background: {BG_WINDOW}; border: 0; border-bottom: 1px solid {BORDER_ROW}; color: {TEXT_7};
    font-size: 11px; font-weight: 600; padding: 0 8px; height: 34px;
}}
"""
