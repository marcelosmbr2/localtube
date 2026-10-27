"""A janela abre offscreen, todas as telas aparecem e os atalhos básicos funcionam."""

from PySide6.QtCore import Qt

from localtube import theme
from localtube.services import Services
from localtube.ui.main_window import MainWindow


def test_main_window_pages_and_palette(qtbot, settings, qapp):
    theme.load_fonts()
    qapp.setStyleSheet(theme.build_stylesheet())
    window = MainWindow(Services(settings))
    qtbot.addWidget(window)
    window.show()

    for key in ("download", "convert", "queue", "library", "settings"):
        window.go(key)
        assert window.stack.currentWidget() is window.pages[key]
        assert window.sidebar.items[key].property("active") is True

    window.palette.open()
    assert window.palette.isVisible() and len(window.palette._items) == 7
    qtbot.keyClicks(window.palette.input, "https://example.com/v")
    assert [i.command.label for i in window.palette._items] == ["Inspecionar example.com/v"]
    qtbot.keyClick(window.palette.input, Qt.Key.Key_Escape)
    assert not window.palette.isVisible()

    window.toast("Olá")
    assert window.toast_widget.isVisible()
    window.close()
