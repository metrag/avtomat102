from pathlib import Path
from PyQt6.QtGui import QIcon

_ICON_PATH = Path(__file__).parents[2] / "assets" / "images" / "icon.png"

def set_window_icon(widget):
    """Устанавливает иконку приложения на окно."""
    if _ICON_PATH.exists():
        widget.setWindowIcon(QIcon(str(_ICON_PATH)))
