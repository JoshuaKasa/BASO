import sys
import ctypes
import os
import json
import re
import shutil
import subprocess
import importlib.util
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLineEdit, QLabel, QCheckBox, QSlider, QPlainTextEdit, QHBoxLayout,
    QCompleter, QFileDialog, QComboBox, QColorDialog, QMessageBox, QGroupBox, QFormLayout,
    QSplitter, QShortcut, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QRegExp, QProcess, QUrl, QRect, QSize
from PyQt5.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextCursor, QDesktopServices, QPainter,
    QTextFormat, QFontMetricsF, QTextDocument, QKeySequence, QFontDatabase
)
import pyautogui
from pynput import mouse, keyboard

class ScriptLineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


class ScriptEditor(QPlainTextEdit):
    def __init__(self, parent=None, font_family=None):
        super().__init__(parent)
        self.completer = None
        self.preferred_font_family = font_family
        self.line_number_area = ScriptLineNumberArea(self)

        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFont(self.build_editor_font())
        tab_width = QFontMetricsF(self.font()).horizontalAdvance(' ') * 4
        self.setTabStopDistance(tab_width)

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

    def build_editor_font(self):
        families = {name.lower(): name for name in QFontDatabase().families()}
        candidates = []
        if self.preferred_font_family:
            candidates.append(self.preferred_font_family)
        candidates.extend(["JetBrains Mono", "Cascadia Mono", "Cascadia Code", "Consolas", "Courier New"])

        selected = None
        for name in candidates:
            actual = families.get(name.lower())
            if actual:
                selected = actual
                break
        if selected is None:
            selected = "Consolas"

        font = QFont(selected)
        font.setPointSize(10)
        font.setStyleHint(QFont.Monospace)
        return font

    def lineNumberAreaWidth(self):
        digits = len(str(max(1, self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance('9') * digits

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        contents_rect = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(contents_rect.left(), contents_rect.top(), self.lineNumberAreaWidth(), contents_rect.height())
        )

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(0, 0, 0, 20))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_number = str(block_number + 1)
                if block_number == self.textCursor().blockNumber():
                    painter.setPen(QColor(230, 230, 230))
                else:
                    painter.setPen(QColor(140, 140, 140))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    line_number
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlightCurrentLine(self):
        if self.isReadOnly():
            self.setExtraSelections([])
            return
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor(255, 255, 255, 28))
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def setCompleter(self, completer):
        if self.completer:
            self.completer.activated.disconnect()

        self.completer = completer
        self.completer.setWidget(self) # set the widget to the completer
        self.completer.setCompletionMode(QCompleter.PopupCompletion) # set how the completer works
        self.completer.setCaseSensitivity(Qt.CaseInsensitive) # case insensitive completion
        self.completer.activated.connect(self.insertCompletion)

    def insertCompletion(self, completion):
        tc = self.textCursor()  # get the current cursor
        extra = len(completion) - len(self.completer.completionPrefix())  # extra characters to insert
        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)  # move to the end of the word

        # Check if the completed word is the same as the suggestion
        if completion[-extra:] == self.textUnderCursor():
            self.completer.popup().hide()
            return

        tc.insertText(completion[-extra:])  # insert the remaining part of the word
        self.setTextCursor(tc)

    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:
            # Insert four spaces instead of a tab
            self.insertPlainText('    ')
            return
        elif self.completer and self.completer.popup().isVisible():
            # The following keys are forwarded by the completer to the widget
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab):
                event.ignore()
                return

        # Handle auto-completion
        super().keyPressEvent(event)
        if not self.completer:
            return
        completion_prefix = self.textUnderCursor()

        # If the completer is not visible, we do nothing here
        if not completion_prefix:
            self.completer.popup().hide()
            return

        if completion_prefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(completion_prefix)
            self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(self.completer.popup().sizeHintForColumn(0)
                    + self.completer.popup().verticalScrollBar().sizeHint().width())
        self.completer.complete(cr)  # popup it up!

class ScriptSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.rules = []
        self.patterns = {
            "trigger": [r'--<[^>\n]+>'],
            "function": [r'\bwait\b', r'\bpress\b', r'\bmove\b', r'\bclick\b'],
            "keyword": [r'\bloop\b'],
            "number": [r'\b\d+(?:ms|s|ds|cs|x|y)?\b'],
            "string": [r'".*"', r"'.*'"],
            "comment": [r'//.*'],
        }
        self.apply_theme_colors()

    def add_rule(self, patterns, format):
        for pattern in patterns:
            expression = QRegExp(pattern)
            self.rules.append((expression, format))

    def apply_theme_colors(self, theme_colors=None):
        base_text = QColor("#d9d9d9")
        primary = QColor("#67a7ff")
        secondary = QColor("#e0b96d")
        accent = QColor("#8ad4b3")

        if isinstance(theme_colors, dict):
            if QColor(theme_colors.get("text", "")).isValid():
                base_text = QColor(theme_colors["text"])
            if QColor(theme_colors.get("primary", "")).isValid():
                primary = QColor(theme_colors["primary"])
            if QColor(theme_colors.get("secondary", "")).isValid():
                secondary = QColor(theme_colors["secondary"])
            if QColor(theme_colors.get("accent", "")).isValid():
                accent = QColor(theme_colors["accent"])

        trigger_format = QTextCharFormat()
        trigger_format.setForeground(primary.lighter(140))
        trigger_format.setFontWeight(QFont.Bold)

        function_format = QTextCharFormat()
        function_format.setForeground(primary.lighter(120))
        function_format.setFontWeight(QFont.Bold)

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(accent.lighter(120))
        keyword_format.setFontWeight(QFont.Bold)

        number_format = QTextCharFormat()
        number_format.setForeground(secondary.lighter(115))

        string_format = QTextCharFormat()
        string_format.setForeground(secondary.lighter(135))

        comment_format = QTextCharFormat()
        comment_color = QColor(base_text)
        comment_color.setAlpha(165)
        comment_format.setForeground(comment_color)
        comment_format.setFontItalic(True)

        self.rules = []
        self.add_rule(self.patterns["trigger"], trigger_format)
        self.add_rule(self.patterns["function"], function_format)
        self.add_rule(self.patterns["keyword"], keyword_format)
        self.add_rule(self.patterns["number"], number_format)
        self.add_rule(self.patterns["string"], string_format)
        self.add_rule(self.patterns["comment"], comment_format)
        self.rehighlight()

    def highlightBlock(self, text):
        for pattern, format in self.rules:
            index = pattern.indexIn(text)
            while index >= 0:
                length = pattern.matchedLength()
                self.setFormat(index, length, format)
                index = pattern.indexIn(text, index + length)

        self.setCurrentBlockState(0)
        
class ModMenu(QMainWindow):
    # Define signals
    start_recoil_signal = pyqtSignal()
    stop_recoil_signal = pyqtSignal()
    run_script_signal = pyqtSignal(str, str)
    inprocess_finished_signal = pyqtSignal(bool, str)

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.presets_file = os.path.join(self.project_root, 'presets.txt')
        self.theme_preferences_file = os.path.join(self.project_root, 'theme_preferences.json')
        self.custom_theme_file = os.path.join(self.project_root, 'custom_theme.json')
        self.script_bindings_file = os.path.join(self.project_root, 'script_bindings.json')
        self.compact_size = (400, 300)
        self.expanded_size = (920, 680)
        self.compact_mode = False
        self.recoil_activation_mode = "both"
        self.current_script_path = None
        self.corel_process = None
        self.hotkey_listener = None
        self.script_bindings = {}
        self.script_runtime_cache = {}
        self.corel_runtime_module = None
        self.active_theme_colors = None
        self.full_tab_names = ['Recoil', 'Configs', 'Scripts', 'Themes', 'Options']
        self.compact_tab_names = ['Rc', 'Cfg', 'Scr', 'Th', 'Opt']
        self.script_running_inprocess = False
        self.script_state_lock = threading.Lock()

        # Connect signals
        self.start_recoil_signal.connect(self.start_recoil)
        self.stop_recoil_signal.connect(self.stop_recoil)
        self.run_script_signal.connect(self.run_script_from_hotkey)
        self.inprocess_finished_signal.connect(self.on_inprocess_script_finished)

        self.initUI()
        self.load_presets()
        self.load_theme_preferences()
        self.load_script_bindings()

        self.recoil_timer = QTimer()
        self.recoil_timer.timeout.connect(self.apply_recoil)
        self.mouse_pressed = False
        self.is_mouse_pressed = False
        self.is_right_pressed = False
        self.dragging = False
        self.offset = QPoint()
        self.setWindowOpacity(0.9)
        self.apply_window_flags()

        self.ui_stats_timer = QTimer(self)
        self.ui_stats_timer.timeout.connect(self.update_runtime_summary)
        self.ui_stats_timer.start(1500)
        self.update_runtime_summary()

        # Start the mouse listener
        self.listener = mouse.Listener(on_click=self.on_global_click)
        self.listener.start()

    def initUI(self):
        if self.app is None:
            self.app = QApplication.instance() or QApplication([])
        self.app.setStyle("Fusion")
        self.setup_font_preferences()
        self.app.setFont(QFont(self.ui_font_family, 10))
        self.setWindowTitle('Rainbow 6 Siege Mod Menu')

        self.resize(*self.expanded_size)
        self.setMinimumSize(760, 520)
        self.setMaximumSize(16777215, 16777215)
        self.compact_mode = False

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.tab_widget = QTabWidget()
        self.central_layout = QVBoxLayout()
        self.central_layout.setContentsMargins(8, 8, 8, 8)
        self.central_layout.setSpacing(8)
        self.central_layout.addWidget(self.tab_widget)
        central_widget.setLayout(self.central_layout)

        recoil_tab = QWidget()
        config_tab = QWidget()
        script_tab = QWidget()
        themes_tab = QWidget()
        options_tab = QWidget()

        self.tab_widget.addTab(recoil_tab, 'Recoil')
        self.tab_widget.addTab(config_tab, 'Configs')
        self.tab_widget.addTab(script_tab, 'Scripts')
        self.tab_widget.addTab(themes_tab, 'Themes')
        self.tab_widget.addTab(options_tab, 'Options')

        self.createRecoilTab(recoil_tab)
        self.createConfigsTab(config_tab)
        self.createScriptsTab(script_tab)
        self.createThemesTab(themes_tab)
        self.createOptionsTab(options_tab)
        self.apply_global_styles()
        self.apply_tooltips()
        self.apply_editor_fonts()
        self.apply_compact_layout_state()

        self.update_slider_value(self.recoil_slider.value())
        self.update_x_slider_value(self.recoil_x_slider.value())
        self.update_delay_value(self.delay_slider.value())
        self.update_current_script_label()
        self.update_editor_status_labels()
        self.update_recoil_runtime_label()
        self.update_recoil_info_panel()
        self.refresh_script_library_list()
        self.show()

    def createRecoilTab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        state_group = QGroupBox("Runtime")
        self.recoil_runtime_group = state_group
        state_layout = QFormLayout(state_group)
        self.recoil_checkbox = QCheckBox('Enable Recoil Manager', self)
        self.recoil_checkbox.stateChanged.connect(self.toggle_recoil)
        state_layout.addRow("State", self.recoil_checkbox)

        self.recoil_activation_combo = QComboBox()
        self.recoil_activation_combo.addItem("LMB + RMB", "both")
        self.recoil_activation_combo.addItem("LMB only", "left")
        self.recoil_activation_combo.addItem("RMB only", "right")
        self.recoil_activation_combo.currentIndexChanged.connect(self.on_recoil_activation_changed)
        self.recoil_activation_mode = self.recoil_activation_combo.currentData()
        state_layout.addRow("Activation", self.recoil_activation_combo)

        self.recoil_state_label = QLabel("Idle")
        state_layout.addRow("Status", self.recoil_state_label)
        layout.addWidget(state_group)

        values_group = QGroupBox("Values")
        self.recoil_values_group = values_group
        values_layout = QVBoxLayout(values_group)
        values_layout.setSpacing(6)

        self.recoil_slider_label = QLabel('Recoil Control Y: 0')
        values_layout.addWidget(self.recoil_slider_label)
        self.recoil_slider = QSlider(Qt.Horizontal)
        self.recoil_slider.setMinimum(0)
        self.recoil_slider.setMaximum(100)
        self.recoil_slider.valueChanged.connect(self.update_slider_value)
        values_layout.addWidget(self.recoil_slider)

        self.recoil_x_slider_label = QLabel('Recoil Control X: 0')
        values_layout.addWidget(self.recoil_x_slider_label)
        self.recoil_x_slider = QSlider(Qt.Horizontal)
        self.recoil_x_slider.setMinimum(-100)
        self.recoil_x_slider.setMaximum(100)
        self.recoil_x_slider.setValue(0)
        self.recoil_x_slider.valueChanged.connect(self.update_x_slider_value)
        values_layout.addWidget(self.recoil_x_slider)

        self.delay_slider_label = QLabel('Delay (ms): 0')
        values_layout.addWidget(self.delay_slider_label)
        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setMinimum(1)
        self.delay_slider.setMaximum(1000)
        self.delay_slider.setValue(1)
        self.delay_slider.valueChanged.connect(self.update_delay_value)
        values_layout.addWidget(self.delay_slider)
        layout.addWidget(values_group)

        quick_actions = QHBoxLayout()
        self.apply_once_button = QPushButton("Apply Once")
        self.apply_once_button.clicked.connect(self.apply_recoil_once)
        self.reset_recoil_values_button = QPushButton("Reset Values")
        self.reset_recoil_values_button.clicked.connect(self.reset_recoil_values)
        quick_actions.addWidget(self.apply_once_button)
        quick_actions.addWidget(self.reset_recoil_values_button)
        self.recoil_quick_actions_widget = QWidget()
        self.recoil_quick_actions_widget.setLayout(quick_actions)
        layout.addWidget(self.recoil_quick_actions_widget)

        guide_group = QGroupBox("Guide")
        self.recoil_guide_group = guide_group
        guide_layout = QVBoxLayout(guide_group)
        self.recoil_info_box = QPlainTextEdit()
        self.recoil_info_box.setObjectName("infoOutput")
        self.recoil_info_box.setReadOnly(True)
        self.recoil_info_box.setMinimumHeight(120)
        guide_layout.addWidget(self.recoil_info_box)
        layout.addWidget(guide_group, 1)

    def createConfigsTab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        name_row = QHBoxLayout()
        self.preset_name_label = QLabel('Preset Name:')
        self.preset_name_edit = QLineEdit()
        self.preset_name_edit.setPlaceholderText("e.g. ak74-mid-range")
        name_row.addWidget(self.preset_name_label)
        name_row.addWidget(self.preset_name_edit)
        layout.addLayout(name_row)

        filter_row = QHBoxLayout()
        filter_label = QLabel("Filter:")
        self.preset_filter_input = QLineEdit()
        self.preset_filter_input.setPlaceholderText("type to filter presets")
        self.preset_filter_input.textChanged.connect(self.filter_preset_list)
        filter_row.addWidget(filter_label)
        filter_row.addWidget(self.preset_filter_input)
        layout.addLayout(filter_row)

        actions_row = QHBoxLayout()
        self.save_preset_button = QPushButton('Save')
        self.save_preset_button.clicked.connect(self.save_preset)
        self.load_preset_button = QPushButton('Load')
        self.load_preset_button.clicked.connect(self.load_preset)
        self.delete_preset_button = QPushButton('Delete')
        self.delete_preset_button.clicked.connect(self.delete_preset)
        self.rename_preset_button = QPushButton('Rename')
        self.rename_preset_button.clicked.connect(self.rename_preset)
        self.duplicate_preset_button = QPushButton('Duplicate')
        self.duplicate_preset_button.clicked.connect(self.duplicate_preset)
        actions_row.addWidget(self.save_preset_button)
        actions_row.addWidget(self.load_preset_button)
        actions_row.addWidget(self.delete_preset_button)
        actions_row.addWidget(self.rename_preset_button)
        actions_row.addWidget(self.duplicate_preset_button)
        layout.addLayout(actions_row)

        self.preset_list = QListWidget()
        self.preset_list.setObjectName("presetList")
        self.preset_list.itemSelectionChanged.connect(self.update_preset_summary_label)
        self.preset_list.itemDoubleClicked.connect(lambda _item: self.load_preset())
        layout.addWidget(self.preset_list)

        transfer_row = QHBoxLayout()
        self.export_presets_button = QPushButton("Export")
        self.export_presets_button.clicked.connect(self.export_presets)
        self.import_presets_button = QPushButton("Import")
        self.import_presets_button.clicked.connect(self.import_presets)
        transfer_row.addWidget(self.export_presets_button)
        transfer_row.addWidget(self.import_presets_button)
        layout.addLayout(transfer_row)

        self.preset_summary_label = QLabel("No preset selected")
        self.preset_summary_label.setWordWrap(True)
        layout.addWidget(self.preset_summary_label)

    def createScriptsTab(self, parent_widget):
        script_layout = QVBoxLayout(parent_widget)
        script_layout.setContentsMargins(8, 8, 8, 8)
        script_layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.hotkey_label = QLabel("Hotkey:")
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setPlaceholderText("optional override (e.g. ctrl+shift+k)")
        self.auto_save_on_run_checkbox = QCheckBox("Auto-save before manual run")
        self.auto_save_on_run_checkbox.setChecked(True)
        top_row.addWidget(self.hotkey_label)
        top_row.addWidget(self.hotkey_input, 1)
        top_row.addWidget(self.auto_save_on_run_checkbox)
        script_layout.addLayout(top_row)

        split = QSplitter(Qt.Horizontal)
        self.script_splitter = split
        script_layout.addWidget(split, 1)

        library_panel = QWidget()
        self.script_library_panel = library_panel
        library_layout = QVBoxLayout(library_panel)
        library_layout.setContentsMargins(0, 0, 0, 0)
        library_layout.setSpacing(6)
        self.script_search_input = QLineEdit()
        self.script_search_input.setPlaceholderText("Search .corel scripts")
        self.script_search_input.textChanged.connect(self.refresh_script_library_list)
        library_layout.addWidget(self.script_search_input)
        self.script_library_list = QListWidget()
        self.script_library_list.itemDoubleClicked.connect(self.open_script_from_library_item)
        library_layout.addWidget(self.script_library_list, 1)

        library_buttons = QHBoxLayout()
        refresh_library_button = QPushButton("Refresh")
        refresh_library_button.clicked.connect(self.refresh_script_library_list)
        new_script_button = QPushButton("New")
        new_script_button.clicked.connect(self.create_new_script)
        open_scripts_folder_button = QPushButton("Folder")
        open_scripts_folder_button.clicked.connect(self.open_script_folder)
        library_buttons.addWidget(refresh_library_button)
        library_buttons.addWidget(new_script_button)
        library_buttons.addWidget(open_scripts_folder_button)
        library_layout.addLayout(library_buttons)

        self.script_library_stats_label = QLabel("0 scripts")
        library_layout.addWidget(self.script_library_stats_label)

        editor_panel = QWidget()
        editor_layout = QVBoxLayout(editor_panel)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(6)

        self.script_subtabs = QTabWidget()
        editor_layout.addWidget(self.script_subtabs)

        script_edit_tab = QWidget()
        script_edit_layout = QVBoxLayout(script_edit_tab)
        script_edit_layout.setContentsMargins(4, 4, 4, 4)
        script_edit_layout.setSpacing(6)

        self.current_script_label = QLabel("Current file: (none)")
        self.current_script_label.setToolTip("")
        script_edit_layout.addWidget(self.current_script_label)

        editor_meta_row = QHBoxLayout()
        self.editor_find_input = QLineEdit()
        self.editor_find_input.setPlaceholderText("Find in file...")
        self.editor_find_input.returnPressed.connect(self.find_next_in_editor)
        self.find_prev_button = QPushButton("Prev")
        self.find_prev_button.clicked.connect(self.find_prev_in_editor)
        self.find_next_button = QPushButton("Next")
        self.find_next_button.clicked.connect(self.find_next_in_editor)
        self.editor_case_checkbox = QCheckBox("Case")
        self.editor_case_checkbox.setChecked(False)
        self.editor_position_label = QLabel("Ln 1, Col 1")
        self.editor_modified_label = QLabel("Saved")
        editor_meta_row.addWidget(self.editor_find_input, 1)
        editor_meta_row.addWidget(self.find_prev_button)
        editor_meta_row.addWidget(self.find_next_button)
        editor_meta_row.addWidget(self.editor_case_checkbox)
        editor_meta_row.addWidget(self.editor_position_label)
        editor_meta_row.addWidget(self.editor_modified_label)
        script_edit_layout.addLayout(editor_meta_row)

        self.script_editor = ScriptEditor(font_family=self.code_font_family)
        self.script_editor.setObjectName("scriptEditor")
        self.highlighter = ScriptSyntaxHighlighter(self.script_editor.document())
        self.script_editor.cursorPositionChanged.connect(self.update_editor_status_labels)
        self.script_editor.document().modificationChanged.connect(self.update_editor_status_labels)
        script_edit_layout.addWidget(self.script_editor, 1)

        completer = QCompleter(["wait", "press", "move", "loop", "click"])
        self.script_editor.setCompleter(completer)
        self.setup_editor_shortcuts()

        edit_buttons_top = QHBoxLayout()
        self.new_script_button = QPushButton('New')
        self.new_script_button.clicked.connect(self.create_new_script)
        self.load_script_button = QPushButton('Load')
        self.load_script_button.clicked.connect(self.load_script)
        self.save_script_button = QPushButton('Save')
        self.save_script_button.clicked.connect(self.save_script)
        edit_buttons_top.addWidget(self.new_script_button)
        edit_buttons_top.addWidget(self.load_script_button)
        edit_buttons_top.addWidget(self.save_script_button)
        script_edit_layout.addLayout(edit_buttons_top)

        edit_buttons_bottom = QHBoxLayout()
        self.delete_script_button = QPushButton('Delete')
        self.delete_script_button.clicked.connect(self.delete_script)
        self.bind_loaded_script_button = QPushButton('Bind Loaded Script')
        self.bind_loaded_script_button.clicked.connect(self.bind_loaded_script_hotkey)
        self.run_script_button = QPushButton('Run')
        self.run_script_button.clicked.connect(self.run_script_clicked)
        edit_buttons_bottom.addWidget(self.delete_script_button)
        edit_buttons_bottom.addWidget(self.bind_loaded_script_button)
        edit_buttons_bottom.addWidget(self.run_script_button)
        script_edit_layout.addLayout(edit_buttons_bottom)

        script_bindings_tab = QWidget()
        bindings_layout = QVBoxLayout(script_bindings_tab)
        bindings_layout.setContentsMargins(4, 4, 4, 4)
        bindings_layout.setSpacing(6)

        bindings_actions = QHBoxLayout()
        self.bind_file_script_button = QPushButton('Bind Script File')
        self.bind_file_script_button.clicked.connect(self.bind_script_file_hotkey)
        self.remove_binding_button = QPushButton('Remove Selected')
        self.remove_binding_button.clicked.connect(self.remove_selected_script_binding)
        bindings_actions.addWidget(self.bind_file_script_button)
        bindings_actions.addWidget(self.remove_binding_button)
        bindings_layout.addLayout(bindings_actions)

        self.script_binding_list = QListWidget()
        self.script_binding_list.itemDoubleClicked.connect(self.open_script_from_binding_item)
        bindings_layout.addWidget(self.script_binding_list, 1)

        script_output_tab = QWidget()
        output_layout = QVBoxLayout(script_output_tab)
        output_layout.setContentsMargins(4, 4, 4, 4)
        output_layout.setSpacing(6)
        output_actions = QHBoxLayout()
        self.clear_output_button = QPushButton("Clear Output")
        self.clear_output_button.clicked.connect(self.clear_script_output)
        self.clear_output_before_run_checkbox = QCheckBox("Clear on run")
        self.clear_output_before_run_checkbox.setChecked(True)
        output_actions.addWidget(self.clear_output_button)
        output_actions.addWidget(self.clear_output_before_run_checkbox)
        output_actions.addStretch()
        output_layout.addLayout(output_actions)
        self.script_output = QPlainTextEdit()
        self.script_output.setObjectName("logOutput")
        self.script_output.setReadOnly(True)
        self.script_output.setPlaceholderText("Script execution output will appear here...")
        output_layout.addWidget(self.script_output, 1)

        self.script_subtabs.addTab(script_edit_tab, "Edit")
        self.script_subtabs.addTab(script_bindings_tab, "Bindings")
        self.script_subtabs.addTab(script_output_tab, "Output")

        split.addWidget(library_panel)
        split.addWidget(editor_panel)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 3)

    def createOptionsTab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout(behavior_group)
        self.always_on_top_checkbox = QCheckBox("Keep window always on top")
        self.always_on_top_checkbox.setChecked(True)
        self.always_on_top_checkbox.stateChanged.connect(self.apply_window_flags)
        self.compact_mode_checkbox = QCheckBox("Compact mode (400 x 300)")
        self.compact_mode_checkbox.stateChanged.connect(self.toggle_compact_mode)
        behavior_layout.addWidget(self.always_on_top_checkbox)
        behavior_layout.addWidget(self.compact_mode_checkbox)
        layout.addWidget(behavior_group)

        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout(actions_group)
        self.restart_hotkeys_button = QPushButton("Restart Hotkeys")
        self.restart_hotkeys_button.clicked.connect(self.restart_hotkey_listener)
        self.open_project_button = QPushButton("Open BASO Folder")
        self.open_project_button.clicked.connect(self.open_project_folder)
        self.clear_cache_button = QPushButton("Clear AST Cache")
        self.clear_cache_button.clicked.connect(self.clear_script_runtime_cache)
        actions_layout.addWidget(self.restart_hotkeys_button)
        actions_layout.addWidget(self.open_project_button)
        actions_layout.addWidget(self.clear_cache_button)
        layout.addWidget(actions_group)

        self.runtime_summary_label = QLabel("Runtime summary unavailable")
        self.runtime_summary_label.setWordWrap(True)
        layout.addWidget(self.runtime_summary_label)
        layout.addStretch()

    def apply_global_styles(self):
        self.setStyleSheet("""
            QWidget {
                font-size: 10pt;
            }
            QGroupBox {
                border: 1px solid rgba(120, 120, 120, 140);
                border-radius: 12px;
                margin-top: 6px;
                padding: 16px 12px 10px 12px;
            }
            QGroupBox::title {
                subcontrol-origin: padding;
                subcontrol-position: top left;
                left: 10px;
                top: 1px;
                padding: 0 4px;
            }
            QPushButton {
                border-radius: 10px;
                padding: 7px 13px;
            }
            QLineEdit, QPlainTextEdit, QListWidget, QComboBox {
                border-radius: 10px;
                padding: 6px 8px;
            }
            QSlider::groove:horizontal {
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                margin: -2px 0;
                border-radius: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)

    def setup_font_preferences(self):
        self.ui_font_family = self.pick_font_family(
            ["Inter", "IBM Plex Sans", "Segoe UI", "Noto Sans", "Arial"],
            fallback="Segoe UI"
        )
        self.code_font_family = self.pick_font_family(
            ["JetBrains Mono", "Cascadia Mono", "Cascadia Code", "Consolas", "Courier New"],
            fallback="Consolas"
        )

    def pick_font_family(self, candidates, fallback):
        families = {name.lower(): name for name in QFontDatabase().families()}
        for candidate in candidates:
            actual = families.get(candidate.lower())
            if actual:
                return actual
        return fallback

    def apply_editor_fonts(self, code_point_size=None):
        if code_point_size is None:
            code_point_size = 9 if self.compact_mode else 10
        code_font = QFont(self.code_font_family)
        code_font.setPointSize(code_point_size)
        code_font.setStyleHint(QFont.Monospace)

        if hasattr(self, 'script_editor') and self.script_editor is not None:
            self.script_editor.setFont(code_font)
            self.script_editor.updateLineNumberAreaWidth(0)
        if hasattr(self, 'script_output') and self.script_output is not None:
            self.script_output.setFont(code_font)
        if hasattr(self, 'recoil_info_box') and self.recoil_info_box is not None:
            self.recoil_info_box.setFont(code_font)

    def apply_compact_layout_state(self):
        compact = bool(self.compact_mode)
        ui_size = 9 if compact else 10
        if self.app is not None:
            self.app.setFont(QFont(self.ui_font_family, ui_size))
        self.apply_editor_fonts(9 if compact else 10)

        if hasattr(self, 'central_layout') and self.central_layout is not None:
            if compact:
                self.central_layout.setContentsMargins(4, 4, 4, 4)
                self.central_layout.setSpacing(4)
            else:
                self.central_layout.setContentsMargins(8, 8, 8, 8)
                self.central_layout.setSpacing(8)

        if hasattr(self, 'tab_widget') and self.tab_widget is not None:
            self.tab_widget.setUsesScrollButtons(compact)
            self.tab_widget.tabBar().setExpanding(not compact)
            self.tab_widget.tabBar().setElideMode(Qt.ElideRight if compact else Qt.ElideNone)
            self.set_tab_visible(2, not compact)  # Scripts
            self.set_tab_visible(3, not compact)  # Themes
            names = self.compact_tab_names if compact else self.full_tab_names
            for index, name in enumerate(names):
                if compact and index in (2, 3):
                    continue
                if index < self.tab_widget.count():
                    self.tab_widget.setTabText(index, name)

        if hasattr(self, 'recoil_runtime_group') and self.recoil_runtime_group is not None:
            self.recoil_runtime_group.setVisible(True)
        if hasattr(self, 'recoil_values_group') and self.recoil_values_group is not None:
            self.recoil_values_group.setVisible(True)
        if hasattr(self, 'recoil_quick_actions_widget') and self.recoil_quick_actions_widget is not None:
            self.recoil_quick_actions_widget.setVisible(not compact)
        if hasattr(self, 'recoil_guide_group') and self.recoil_guide_group is not None:
            self.recoil_guide_group.setVisible(not compact)
        if hasattr(self, 'preset_summary_label') and self.preset_summary_label is not None:
            self.preset_summary_label.setVisible(not compact)
        if hasattr(self, 'runtime_summary_label') and self.runtime_summary_label is not None:
            self.runtime_summary_label.setVisible(not compact)
        if hasattr(self, 'editor_position_label') and self.editor_position_label is not None:
            self.editor_position_label.setVisible(not compact)
        if hasattr(self, 'editor_case_checkbox') and self.editor_case_checkbox is not None:
            self.editor_case_checkbox.setVisible(not compact)
        if hasattr(self, 'editor_modified_label') and self.editor_modified_label is not None:
            self.editor_modified_label.setVisible(not compact)
        if hasattr(self, 'find_prev_button') and self.find_prev_button is not None:
            self.find_prev_button.setVisible(not compact)

        if hasattr(self, 'script_library_panel') and self.script_library_panel is not None:
            self.script_library_panel.setVisible(not compact)
        if hasattr(self, 'script_splitter') and self.script_splitter is not None:
            if compact:
                self.script_splitter.setSizes([0, 1])
            else:
                self.script_library_panel.show()
                self.script_splitter.setSizes([280, 640])

        if hasattr(self, 'auto_save_on_run_checkbox') and self.auto_save_on_run_checkbox is not None:
            self.auto_save_on_run_checkbox.setVisible(not compact)
        if hasattr(self, 'bind_loaded_script_button') and self.bind_loaded_script_button is not None:
            self.bind_loaded_script_button.setVisible(not compact)
        if hasattr(self, 'hotkey_label') and self.hotkey_label is not None:
            self.hotkey_label.setVisible(not compact)

        if hasattr(self, 'rename_preset_button') and self.rename_preset_button is not None:
            self.rename_preset_button.setVisible(not compact)
        if hasattr(self, 'duplicate_preset_button') and self.duplicate_preset_button is not None:
            self.duplicate_preset_button.setVisible(not compact)
        if hasattr(self, 'export_presets_button') and self.export_presets_button is not None:
            self.export_presets_button.setVisible(not compact)
        if hasattr(self, 'import_presets_button') and self.import_presets_button is not None:
            self.import_presets_button.setVisible(not compact)

        if hasattr(self, 'open_project_button') and self.open_project_button is not None:
            self.open_project_button.setVisible(not compact)
        if hasattr(self, 'clear_cache_button') and self.clear_cache_button is not None:
            self.clear_cache_button.setText("Cache" if compact else "Clear AST Cache")
        if hasattr(self, 'restart_hotkeys_button') and self.restart_hotkeys_button is not None:
            self.restart_hotkeys_button.setText("Hotkeys" if compact else "Restart Hotkeys")
        if hasattr(self, 'remove_binding_button') and self.remove_binding_button is not None:
            self.remove_binding_button.setText("Remove" if compact else "Remove Selected")
        if hasattr(self, 'bind_file_script_button') and self.bind_file_script_button is not None:
            self.bind_file_script_button.setText("Bind" if compact else "Bind Script File")
        if hasattr(self, 'clear_output_button') and self.clear_output_button is not None:
            self.clear_output_button.setText("Clear" if compact else "Clear Output")
        if hasattr(self, 'clear_output_before_run_checkbox') and self.clear_output_before_run_checkbox is not None:
            self.clear_output_before_run_checkbox.setText("Clr on run" if compact else "Clear on run")

    def set_tab_visible(self, index, visible):
        if not hasattr(self, 'tab_widget') or self.tab_widget is None:
            return
        if index >= self.tab_widget.count():
            return
        tab_bar = self.tab_widget.tabBar()
        if hasattr(tab_bar, "setTabVisible"):
            tab_bar.setTabVisible(index, visible)
        else:
            self.tab_widget.setTabEnabled(index, visible)
            self.tab_widget.setTabText(index, "" if not visible else self.full_tab_names[index])
        if not visible and self.tab_widget.currentIndex() == index:
            self.tab_widget.setCurrentIndex(0)

    def apply_tooltips(self):
        tips = {
            "recoil_checkbox": "Enable recoil compensation while the trigger condition is active.",
            "recoil_activation_combo": "Choose which mouse buttons trigger recoil compensation.",
            "recoil_slider": "Vertical recoil movement in pixels per step.",
            "recoil_x_slider": "Horizontal recoil movement. Negative = left, positive = right.",
            "delay_slider": "Delay between recoil steps in milliseconds.",
            "recoil_info_box": "Live summary and usage tips.",
            "preset_name_edit": "Preset name used for Save/Rename actions.",
            "preset_filter_input": "Filter presets by name or values.",
            "preset_list": "Double-click a preset to load it.",
            "hotkey_input": "Optional override hotkey (e.g. ctrl+shift+k). Leave empty to use script trigger.",
            "auto_save_on_run_checkbox": "Automatically save current script before manual run.",
            "script_search_input": "Filter discovered .corel files by name/path.",
            "script_library_list": "Double-click a script to open it.",
            "current_script_label": "Current file loaded in editor.",
            "script_editor": "Minimal editor: line numbers, syntax highlight, autocomplete, Ctrl+S/Ctrl+O/Ctrl+F, F5 to run.",
            "editor_find_input": "Find text in the current script (Enter = next result).",
            "editor_case_checkbox": "Case-sensitive search.",
            "editor_position_label": "Current cursor position.",
            "editor_modified_label": "Shows whether current script has unsaved changes.",
            "run_script_button": "Run current script immediately.",
            "script_binding_list": "Double-click a binding to open its script.",
            "clear_output_before_run_checkbox": "Clear output panel before each run.",
            "theme_selector": "Choose a preset theme or custom theme.",
            "always_on_top_checkbox": "Keep BASO above other windows.",
            "compact_mode_checkbox": "Switch to compact window mode (400 x 300).",
            "runtime_summary_label": "Live counters for presets, bindings, cache, and scripts.",
        }
        for attr_name, text in tips.items():
            widget = getattr(self, attr_name, None)
            if widget is not None:
                widget.setToolTip(text)

        if hasattr(self, "custom_color_buttons"):
            for key, button in self.custom_color_buttons.items():
                button.setToolTip(f"Set custom color for {key}.")

    def createThemesTab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        theme_label = QLabel("Preset Theme:")
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(list(self.get_preset_themes().keys()) + ["custom"])
        self.theme_selector.currentIndexChanged.connect(self.applyPresetTheme)
        top_row.addWidget(theme_label)
        top_row.addWidget(self.theme_selector, 1)
        layout.addLayout(top_row)

        self.createThemePreviewSection(layout)
        self.createCustomThemeSection(layout)

    def createThemePreviewSection(self, layout):
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_label = QLabel("Theme Preview")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(preview_label)

        test_button = QPushButton("Test Button")
        preview_layout.addWidget(test_button)

        sample_text = QLabel("This is a sample text for theme preview.")
        sample_text.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(sample_text)

        preview_slider = QSlider(Qt.Horizontal)
        preview_layout.addWidget(preview_slider)

        preview_checkbox = QCheckBox("Sample Checkbox")
        preview_layout.addWidget(preview_checkbox)
        layout.addWidget(preview_group)

    def createCustomThemeSection(self, layout):
        self.custom_color_buttons = {}
        custom_group = QGroupBox("Custom Theme")
        custom_layout = QFormLayout(custom_group)
        for key in ["background", "primary", "secondary", "accent", "text"]:
            button = QPushButton()
            button.setMinimumWidth(140)
            button.setProperty("color_key", key)
            button.clicked.connect(self.chooseColor)
            custom_layout.addRow(key.capitalize(), button)
            self.custom_color_buttons[key] = button

        actions = QHBoxLayout()
        apply_custom = QPushButton("Apply Custom")
        apply_custom.clicked.connect(self.applyCustomTheme)
        reset_custom = QPushButton("Reset Custom")
        reset_custom.clicked.connect(self.reset_custom_theme_colors)
        save_custom = QPushButton("Save Custom")
        save_custom.clicked.connect(self.save_current_custom_theme)
        actions.addWidget(apply_custom)
        actions.addWidget(reset_custom)
        actions.addWidget(save_custom)
        custom_layout.addRow(actions)
        layout.addWidget(custom_group)

        self.set_custom_theme_buttons(self.load_custom_theme_colors())

    def get_preset_themes(self):
        return {
            "default": {
                "background": "#e6e6e6", "primary": "#007BFF", "secondary": "#0056b3", "accent": "#0056b3", "text": "#ffffff"
            },
            "gruvbox dark": {
                "background": "#282828", "primary": "#fabd2f", "secondary": "#83a598", "accent": "#b16286", "text": "#ffffff"
            },
            "serika dark": {
                "background": "#3a3a3a", "primary": "#e2b714", "secondary": "#4d4d4d", "accent": "#8c7851", "text": "#ffffff"
            },
            "serika": {
                "background": "#e2d3ba", "primary": "#323437", "secondary": "#e2b714", "accent": "#3e424d", "text": "#282828"
            },
            "catpuccin mocha": {
                "background": "#1E1E2E", "primary": "#CDD6F4", "secondary": "#F5A97F", "accent": "#89b4fa", "text": "#a6accd"
            },
            "milkshake": {
                "background": "#f2e7c9", "primary": "#6e4a4a", "secondary": "#c6aa8e", "accent": "#a67358", "text": "#38220f"
            },
            "cafe": {
                "background": "#2e1f1c", "primary": "#c0a36e", "secondary": "#a67358", "accent": "#805b36", "text": "#f3e9dc"
            },
            "blueberry light": {
                "background": "#d8e2ef", "primary": "#3c4c5e", "secondary": "#528bff", "accent": "#6b8dd6", "text": "#1c283b"
            },
            "cheesecake": {
                "background": "#f4e0d3", "primary": "#5a4a42", "secondary": "#c6aa8e", "accent": "#805b36", "text": "#38220f"
            },
            "honey": {
                "background": "#FFF8E1", "primary": "#FFC107", "secondary": "#FFB300", "accent": "#FFD54F", "text": "#795548"
            },
            "starclass": {
                "background": "#D4E9E2", "primary": "#00704A", "secondary": "#005241", "accent": "#A5D6A7", "text": "#3E2723"
            },
            "TMO": {
                "background": "#A7DBC8", "primary": "#59CE8F", "secondary": "#507C7E", "accent": "#A1E8AF", "text": "#3A4042"
            },
            "hot chocolate": {
                "background": "#FFF4E6", "primary": "#8C5E58", "secondary": "#AA8073", "accent": "#D3A99A", "text": "#5A3B35"
            },
            "nene": {
                "background": "#E0F7FA", "primary": "#4DD0E1", "secondary": "#26C6DA", "accent": "#B2EBF2", "text": "#00838F"
            },
            "nocto": {
                "background": "#f5f5f5", "primary": "#424242", "secondary": "#bdbdbd", "accent": "#e0e0e0", "text": "#212121"
            },
        }

    def applyPresetTheme(self):
        if not hasattr(self, 'theme_selector'):
            return
        theme_name = self.theme_selector.currentText()
        if theme_name == "custom":
            colors = self.load_custom_theme_colors()
            self.set_custom_theme_buttons(colors)
        else:
            colors = self.get_preset_themes().get(theme_name, self.get_preset_themes()["default"])
            self.set_custom_theme_buttons(colors)

        self.applyTheme(colors)
        self.save_theme_preferences(theme_name)

    def save_theme_preferences(self, theme_name):
        try:
            with open(self.theme_preferences_file, 'w') as file:
                json.dump({'theme': theme_name}, file, indent=2)
        except Exception as exc:
            self.append_script_output(f"Error saving theme preferences: {exc}")

    def load_theme_preferences(self):
        theme_name = "default"
        if os.path.exists(self.theme_preferences_file):
            try:
                with open(self.theme_preferences_file, 'r') as file:
                    data = json.load(file)
                if isinstance(data, dict) and isinstance(data.get('theme'), str):
                    theme_name = data['theme']
            except Exception as exc:
                self.append_script_output(f"Error loading theme preferences: {exc}")

        index = self.theme_selector.findText(theme_name)
        if index < 0:
            index = self.theme_selector.findText("default")
        self.theme_selector.setCurrentIndex(index)
        self.applyPresetTheme()

    def set_custom_theme_buttons(self, colors):
        for key, button in self.custom_color_buttons.items():
            self.set_color_button_value(button, colors.get(key, "#ffffff"))

    def set_color_button_value(self, button, color_hex):
        normalized = QColor(color_hex).name() if QColor(color_hex).isValid() else "#ffffff"
        button.setProperty("color_value", normalized)
        button.setText(normalized)
        button.setStyleSheet(f"background-color: {normalized};")

    def chooseColor(self):
        sender = self.sender()
        if sender is None:
            return
        current = sender.property("color_value") or "#ffffff"
        picked = QColorDialog.getColor(QColor(current), self, "Choose Color")
        if picked.isValid():
            self.set_color_button_value(sender, picked.name())

    def get_custom_theme_colors(self):
        colors = {}
        defaults = self.get_preset_themes()["default"]
        for key, button in self.custom_color_buttons.items():
            raw = button.property("color_value")
            colors[key] = raw if isinstance(raw, str) and QColor(raw).isValid() else defaults[key]
        return colors

    def save_current_custom_theme(self):
        colors = self.get_custom_theme_colors()
        self.save_custom_theme_colors(colors)
        self.theme_selector.setCurrentText("custom")
        self.applyCustomTheme()

    def save_custom_theme_colors(self, colors):
        try:
            with open(self.custom_theme_file, 'w') as file:
                json.dump(colors, file, indent=2)
        except Exception as exc:
            self.append_script_output(f"Error saving custom theme: {exc}")

    def load_custom_theme_colors(self):
        defaults = self.get_preset_themes()["default"].copy()
        if not os.path.exists(self.custom_theme_file):
            return defaults
        try:
            with open(self.custom_theme_file, 'r') as file:
                data = json.load(file)
            if isinstance(data, dict):
                for key in defaults.keys():
                    value = data.get(key)
                    if isinstance(value, str) and QColor(value).isValid():
                        defaults[key] = value
        except Exception as exc:
            self.append_script_output(f"Error loading custom theme: {exc}")
        return defaults

    def reset_custom_theme_colors(self):
        defaults = self.get_preset_themes()["default"]
        self.set_custom_theme_buttons(defaults)
        self.save_custom_theme_colors(defaults)
        self.theme_selector.setCurrentText("default")
        self.applyPresetTheme()

    def applyCustomTheme(self):
        colors = self.get_custom_theme_colors()
        self.save_custom_theme_colors(colors)
        self.applyTheme(colors)
        self.save_theme_preferences("custom")

    def applyTheme(self, colors):
        required_keys = {'background', 'primary', 'secondary', 'accent', 'text'}
        if not isinstance(colors, dict) or not required_keys.issubset(colors.keys()):
            raise Exception('Invalid theme colors, expected keys: background, primary, secondary, accent, text')

        background = QColor(colors['background'])
        text_color = QColor(colors['text'])
        primary = QColor(colors['primary'])
        secondary = QColor(colors['secondary'])
        accent = QColor(colors['accent'])

        is_dark = background.lightness() < 128
        panel_color = background.lighter(112) if is_dark else background.darker(104)
        input_color = background.lighter(107) if is_dark else background.darker(108)
        tab_idle = background.lighter(120) if is_dark else background.darker(103)
        border_color = secondary.lighter(120) if is_dark else secondary.darker(110)
        subtle_text = text_color.lighter(135) if is_dark else text_color.darker(145)
        hover_color = accent.lighter(110) if is_dark else accent.darker(110)
        pressed_color = accent.darker(110) if is_dark else accent.darker(125)

        def rgba(color, alpha):
            return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"

        ui_font = getattr(self, "ui_font_family", "Segoe UI")
        compact_css = ""
        if self.compact_mode:
            compact_css = """
            QWidget {
                font-size: 8.5pt;
            }
            QLabel {
                margin: 0px;
            }
            QGroupBox {
                margin-top: 4px;
                padding: 12px 7px 6px 7px;
                border-radius: 9px;
            }
            QGroupBox::title {
                left: 6px;
                top: 1px;
                padding: 0 3px;
            }
            QPushButton {
                padding: 4px 7px;
                border-radius: 7px;
                font-weight: 500;
            }
            QLineEdit, QPlainTextEdit, QListWidget, QComboBox {
                padding: 3px 5px;
                border-radius: 7px;
            }
            QTabBar::tab {
                padding: 4px 8px;
                margin-right: 3px;
                min-width: 0px;
                border-radius: 7px;
            }
            QPlainTextEdit#scriptEditor, QPlainTextEdit#logOutput, QPlainTextEdit#infoOutput {
                border-radius: 8px;
                padding: 5px;
            }
            """
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {colors['background']};
                color: {colors['text']};
                font-family: '{ui_font}';
            }}
            QWidget {{
                color: {colors['text']};
            }}
            QToolTip {{
                color: {colors['text']};
                background: {rgba(panel_color, 240)};
                border: 1px solid {border_color.name()};
                border-radius: 8px;
                padding: 6px 8px;
            }}
            QTabWidget::pane {{
                border: none;
                background: transparent;
                margin-top: 8px;
            }}
            QTabBar {{
                qproperty-drawBase: 0;
            }}
            QTabBar::tab {{
                background: {tab_idle.name()};
                color: {subtle_text.name()};
                border: 1px solid transparent;
                border-radius: 10px;
                padding: 8px 14px;
                margin-right: 6px;
                margin-bottom: 2px;
                min-width: 72px;
            }}
            QTabBar::tab:hover {{
                color: {colors['text']};
                border: 1px solid {rgba(border_color, 170)};
            }}
            QTabBar::tab:selected {{
                background: {panel_color.name()};
                color: {colors['text']};
                border: 1px solid {border_color.name()};
            }}
            QGroupBox {{
                background: {panel_color.name()};
                border: 1px solid {rgba(border_color, 175)};
                border-radius: 12px;
                margin-top: 6px;
                padding: 16px 12px 10px 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: padding;
                subcontrol-position: top left;
                left: 10px;
                top: 1px;
                padding: 0 4px;
                color: {subtle_text.name()};
                background: transparent;
            }}
            QPushButton {{
                background-color: {rgba(primary, 70)};
                color: {colors['text']};
                border: 1px solid {rgba(border_color, 170)};
                border-radius: 10px;
                padding: 7px 13px;
                margin: 1px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {rgba(hover_color, 100)};
                border: 1px solid {hover_color.name()};
            }}
            QPushButton:pressed {{
                background-color: {rgba(pressed_color, 120)};
            }}
            QLineEdit, QPlainTextEdit, QListWidget, QComboBox {{
                background: {input_color.name()};
                border: 1px solid {rgba(border_color, 180)};
                border-radius: 10px;
                padding: 6px 8px;
                color: {colors['text']};
                selection-background-color: {rgba(accent, 140)};
            }}
            QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus, QComboBox:focus {{
                border: 1px solid {accent.name()};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QListWidget::item {{
                border-radius: 6px;
                padding: 4px 6px;
            }}
            QListWidget::item:selected {{
                background: {rgba(accent, 120)};
                color: {colors['text']};
            }}
            QListWidget#presetList {{
                padding: 6px;
            }}
            QListWidget#presetList::item {{
                margin: 3px 2px;
                padding: 8px 10px;
                border: 1px solid {rgba(border_color, 120)};
                border-radius: 8px;
            }}
            QListWidget#presetList::item:hover {{
                background: {rgba(accent, 70)};
                border: 1px solid {rgba(accent, 140)};
            }}
            QListWidget#presetList::item:selected {{
                background: {rgba(accent, 120)};
                border: 1px solid {accent.name()};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {rgba(border_color, 170)};
                height: 8px;
                background: {rgba(secondary, 85)};
                margin: 2px 0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {accent.name()};
                border: 1px solid {rgba(border_color, 220)};
                width: 16px;
                margin: -2px 0;
                border-radius: 8px;
            }}
            QCheckBox {{
                spacing: 6px;
                color: {colors['text']};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid {rgba(border_color, 180)};
                background: {input_color.name()};
            }}
            QCheckBox::indicator:checked {{
                background: {accent.name()};
                border: 1px solid {accent.name()};
            }}
            QLabel {{
                color: {colors['text']};
            }}
            QPlainTextEdit#scriptEditor, QPlainTextEdit#logOutput, QPlainTextEdit#infoOutput {{
                border-radius: 12px;
                padding: 8px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {rgba(border_color, 180)};
                min-height: 28px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 10px;
                margin: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {rgba(border_color, 180)};
                min-width: 28px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            {compact_css}
        """)
        if hasattr(self, 'highlighter') and self.highlighter is not None:
            self.highlighter.apply_theme_colors(colors)
        self.active_theme_colors = dict(colors)
        self.apply_compact_layout_state()

    def update_slider_value(self, value):
        self.recoil_slider_label.setText(f'Recoil Control Y: {value}')
        self.update_preset_summary_label()
        self.update_recoil_info_panel()

    def update_x_slider_value(self, value):
        self.recoil_x_slider_label.setText(f'Recoil Control X: {value}')
        self.update_preset_summary_label()
        self.update_recoil_info_panel()

    def update_delay_value(self, value):
        self.delay_slider_label.setText(f'Delay (ms): {value}')
        self.update_preset_summary_label()
        self.update_recoil_info_panel()

    def format_preset_text(self, name, y_value, x_value, delay):
        return f'{name} - Y: {y_value} - X: {x_value} - Delay: {delay} ms'

    def format_preset_display_text(self, name, y_value, x_value, delay):
        return f"{name}   ·   Y {y_value:+d}   X {x_value:+d}   {delay} ms"

    def create_preset_item(self, name, y_value, x_value, delay):
        serialized = self.format_preset_text(name, y_value, x_value, delay)
        display = self.format_preset_display_text(name, y_value, x_value, delay)
        item = QListWidgetItem(display)
        item.setData(Qt.UserRole, serialized)
        item.setToolTip(serialized)
        return item

    def update_preset_item(self, item, name, y_value, x_value, delay):
        serialized = self.format_preset_text(name, y_value, x_value, delay)
        display = self.format_preset_display_text(name, y_value, x_value, delay)
        item.setText(display)
        item.setData(Qt.UserRole, serialized)
        item.setToolTip(serialized)

    def get_preset_item_serialized(self, item):
        if item is None:
            return ""
        serialized = item.data(Qt.UserRole)
        if isinstance(serialized, str) and serialized.strip():
            return serialized.strip()
        text = item.text().strip()
        return text

    def parse_preset_item(self, item):
        return self.parse_preset_text(self.get_preset_item_serialized(item))

    def parse_preset_text(self, text):
        match = re.match(r'^\s*(.*?)\s*-\s*Y:\s*(-?\d+)\s*-\s*X:\s*(-?\d+)\s*-\s*Delay:\s*(\d+)\s*ms\s*$', text)
        if not match:
            return None
        return match.group(1), int(match.group(2)), int(match.group(3)), int(match.group(4))

    def get_existing_preset_names(self):
        names = set()
        for index in range(self.preset_list.count()):
            parsed = self.parse_preset_item(self.preset_list.item(index))
            if parsed:
                names.add(parsed[0].lower())
        return names

    def make_unique_preset_name(self, base_name):
        existing = self.get_existing_preset_names()
        candidate = base_name
        suffix = 2
        while candidate.lower() in existing:
            candidate = f"{base_name}-{suffix}"
            suffix += 1
        return candidate

    def update_preset_summary_label(self):
        if not hasattr(self, 'preset_summary_label'):
            return
        selected_item = self.preset_list.currentItem()
        if selected_item:
            parsed = self.parse_preset_item(selected_item)
            if parsed:
                name, y_value, x_value, delay = parsed
                self.preset_summary_label.setText(
                    f"Selected: {name} | Y={y_value}, X={x_value}, Delay={delay}ms"
                )
                return
        self.preset_summary_label.setText(
            f"Current values: Y={self.recoil_slider.value()}, X={self.recoil_x_slider.value()}, Delay={self.delay_slider.value()}ms"
        )

    def filter_preset_list(self, text):
        token = text.strip().lower()
        for index in range(self.preset_list.count()):
            item = self.preset_list.item(index)
            searchable = f"{item.text()} {self.get_preset_item_serialized(item)}".lower()
            item.setHidden(token not in searchable)

    def save_preset(self):
        name = self.preset_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Save Preset", "Preset name cannot be empty.")
            return

        y_value = self.recoil_slider.value()
        x_value = self.recoil_x_slider.value()
        delay = self.delay_slider.value()

        replaced = False
        for index in range(self.preset_list.count()):
            item = self.preset_list.item(index)
            parsed = self.parse_preset_item(item)
            if parsed and parsed[0].lower() == name.lower():
                self.update_preset_item(item, name, y_value, x_value, delay)
                self.preset_list.setCurrentItem(item)
                replaced = True
                break
        if not replaced:
            item = self.create_preset_item(name, y_value, x_value, delay)
            self.preset_list.addItem(item)
            self.preset_list.setCurrentItem(item)

        self.save_presets()
        self.update_preset_summary_label()
        self.update_runtime_summary()

    def load_preset(self):
        selected_item = self.preset_list.currentItem()
        if not selected_item:
            return
        parsed = self.parse_preset_item(selected_item)
        if not parsed:
            QMessageBox.warning(self, "Load Preset", "Selected preset has an invalid format.")
            return

        name, y_value, x_value, delay = parsed
        self.preset_name_edit.setText(name)
        self.recoil_slider.setValue(y_value)
        self.recoil_x_slider.setValue(x_value)
        self.delay_slider.setValue(max(1, delay))
        self.update_slider_value(y_value)
        self.update_x_slider_value(x_value)
        self.update_delay_value(delay)
        self.update_preset_summary_label()

    def delete_preset(self):
        selected_item = self.preset_list.currentItem()
        if selected_item:
            self.preset_list.takeItem(self.preset_list.row(selected_item))
            self.save_presets()
            self.update_preset_summary_label()
            self.update_runtime_summary()

    def rename_preset(self):
        selected_item = self.preset_list.currentItem()
        new_name = self.preset_name_edit.text().strip()
        if not selected_item or not new_name:
            QMessageBox.warning(self, "Rename Preset", "Select a preset and set a new name first.")
            return
        parsed = self.parse_preset_item(selected_item)
        if not parsed:
            QMessageBox.warning(self, "Rename Preset", "Selected preset has an invalid format.")
            return

        _old_name, y_value, x_value, delay = parsed
        self.update_preset_item(selected_item, new_name, y_value, x_value, delay)
        self.save_presets()
        self.update_preset_summary_label()

    def duplicate_preset(self):
        selected_item = self.preset_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Duplicate Preset", "Select a preset to duplicate.")
            return

        parsed = self.parse_preset_item(selected_item)
        if not parsed:
            QMessageBox.warning(self, "Duplicate Preset", "Selected preset has an invalid format.")
            return

        name, y_value, x_value, delay = parsed
        duplicated_name = self.make_unique_preset_name(f"{name}-copy")
        duplicated_item = self.create_preset_item(duplicated_name, y_value, x_value, delay)
        self.preset_list.addItem(duplicated_item)
        self.preset_list.setCurrentItem(duplicated_item)
        self.preset_name_edit.setText(duplicated_name)
        self.save_presets()
        self.update_preset_summary_label()
        self.update_runtime_summary()

    def export_presets(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Presets", self.presets_file, "Text Files (*.txt)")
        if not path:
            return
        presets = [self.get_preset_item_serialized(self.preset_list.item(index)) for index in range(self.preset_list.count())]
        try:
            with open(path, 'w') as file:
                file.write('\n'.join(presets))
        except OSError as exc:
            QMessageBox.critical(self, "Export Presets", f"Failed to export presets:\n{exc}")

    def import_presets(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Presets", self.project_root, "Text Files (*.txt)")
        if not path:
            return

        imported = 0
        try:
            with open(path, 'r') as file:
                lines = file.read().splitlines()
        except OSError as exc:
            QMessageBox.critical(self, "Import Presets", f"Failed to import presets:\n{exc}")
            return

        existing_names = self.get_existing_preset_names()
        for line in lines:
            parsed = self.parse_preset_text(line)
            if not parsed:
                continue
            name, y_value, x_value, delay = parsed
            if name.lower() in existing_names:
                name = self.make_unique_preset_name(name)
            item = self.create_preset_item(name, y_value, x_value, delay)
            self.preset_list.addItem(item)
            existing_names.add(name.lower())
            imported += 1

        if imported:
            self.save_presets()
            self.update_runtime_summary()
        QMessageBox.information(self, "Import Presets", f"Imported {imported} preset(s).")

    def save_presets(self):
        presets = [self.get_preset_item_serialized(self.preset_list.item(index)) for index in range(self.preset_list.count())]
        with open(self.presets_file, 'w') as file:
            file.write('\n'.join(presets))

    def load_presets(self):
        self.preset_list.clear()
        try:
            with open(self.presets_file, 'r') as file:
                presets = file.read().splitlines()
            for line in presets:
                parsed = self.parse_preset_text(line)
                if parsed:
                    name, y_value, x_value, delay = parsed
                    self.preset_list.addItem(self.create_preset_item(name, y_value, x_value, delay))
        except FileNotFoundError:
            pass
        self.filter_preset_list(self.preset_filter_input.text())
        self.update_preset_summary_label()
        self.update_runtime_summary()

    def is_recoil_trigger_active(self):
        mode = self.recoil_activation_mode
        if mode == "left":
            return self.is_mouse_pressed
        if mode == "right":
            return self.is_right_pressed
        return self.is_mouse_pressed and self.is_right_pressed

    def on_recoil_activation_changed(self, _index):
        self.recoil_activation_mode = self.recoil_activation_combo.currentData()
        self.update_recoil_runtime_label()
        self.update_recoil_info_panel()

    def update_recoil_runtime_label(self):
        if not hasattr(self, 'recoil_state_label'):
            return
        if not self.recoil_checkbox.isChecked():
            status = "Disabled"
        elif self.isActiveWindow():
            status = "Paused (window focused)"
        elif self.is_recoil_trigger_active():
            status = "Active trigger detected"
        else:
            status = "Waiting for trigger"
        self.recoil_state_label.setText(status)
        self.update_recoil_info_panel()

    def update_recoil_info_panel(self):
        if not hasattr(self, 'recoil_info_box'):
            return
        mode_map = {
            "both": "LMB + RMB",
            "left": "LMB only",
            "right": "RMB only",
        }
        status = self.recoil_state_label.text() if hasattr(self, 'recoil_state_label') else "Unknown"
        mode = mode_map.get(self.recoil_activation_mode, "LMB + RMB")
        y_value = self.recoil_slider.value() if hasattr(self, 'recoil_slider') else 0
        x_value = self.recoil_x_slider.value() if hasattr(self, 'recoil_x_slider') else 0
        delay = self.delay_slider.value() if hasattr(self, 'delay_slider') else 1
        lines = [
            f"Status: {status}",
            f"Activation: {mode}",
            f"Y: {y_value} | X: {x_value} | Delay: {delay} ms",
            "",
            "Tips:",
            "1) Start with low Y values and increase gradually.",
            "2) Use X to correct horizontal drift.",
            "3) Lower delay is stronger/faster compensation.",
            "4) Recoil runs only while BASO window is unfocused.",
        ]
        self.recoil_info_box.setPlainText("\n".join(lines))

    def apply_recoil_once(self):
        if os.name != 'nt':
            return
        y_value = self.recoil_slider.value()
        x_value = self.recoil_x_slider.value()
        if y_value == 0 and x_value == 0:
            return
        ctypes.windll.user32.mouse_event(0x0001, x_value, y_value, 0, 0)

    def reset_recoil_values(self):
        self.recoil_slider.setValue(0)
        self.recoil_x_slider.setValue(0)
        self.delay_slider.setValue(1)
        self.update_preset_summary_label()
        self.update_recoil_info_panel()

    def apply_window_flags(self, _state=None):
        flags = Qt.FramelessWindowHint
        if hasattr(self, 'always_on_top_checkbox'):
            if self.always_on_top_checkbox.isChecked():
                flags |= Qt.WindowStaysOnTopHint
        else:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def toggle_compact_mode(self, state):
        if isinstance(state, bool):
            enabled = state
        elif isinstance(state, int):
            enabled = state == Qt.Checked
        else:
            enabled = bool(state)
        self.compact_mode = enabled
        if enabled:
            self.expanded_size = (max(self.width(), 760), max(self.height(), 520))
            self.setFixedSize(*self.compact_size)
        else:
            self.setMinimumSize(760, 520)
            self.setMaximumSize(16777215, 16777215)
            self.resize(*self.expanded_size)
        self.apply_compact_layout_state()
        if self.active_theme_colors:
            self.applyTheme(self.active_theme_colors)

    def open_project_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.project_root))

    def open_script_folder(self):
        scripts_root = os.path.join(self.project_root, 'corel')
        target = scripts_root if os.path.isdir(scripts_root) else self.project_root
        QDesktopServices.openUrl(QUrl.fromLocalFile(target))

    def clear_script_runtime_cache(self):
        self.script_runtime_cache.clear()
        self.append_script_output("Cleared script runtime cache.")
        self.update_runtime_summary()

    def clear_script_output(self):
        self.script_output.clear()

    def discover_script_files(self):
        script_files = []
        skip_dirs = {'.git', '__pycache__', 'target', 'ext'}
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [name for name in dirs if name not in skip_dirs]
            for name in files:
                if not name.lower().endswith('.corel'):
                    continue
                abs_path = os.path.abspath(os.path.join(root, name))
                if abs_path.endswith(os.path.join('corel', 'corel.corel')):
                    continue
                script_files.append(abs_path)
        return sorted(script_files, key=lambda value: value.lower())

    def refresh_script_library_list(self, _text=None):
        if not hasattr(self, 'script_library_list'):
            return

        self.script_library_list.clear()
        query = self.script_search_input.text().strip().lower()
        all_scripts = self.discover_script_files()
        visible = 0
        for path in all_scripts:
            relative = os.path.relpath(path, self.project_root)
            searchable = f"{os.path.basename(path)} {relative}".lower()
            if query and query not in searchable:
                continue
            item = QListWidgetItem(relative.replace('\\', '/'))
            item.setData(Qt.UserRole, path)
            self.script_library_list.addItem(item)
            visible += 1

        self.script_library_stats_label.setText(f"{visible} script(s)")
        self.update_runtime_summary()

    def open_script_from_library_item(self, item):
        path = item.data(Qt.UserRole)
        if not path:
            return
        try:
            self.open_script_file(path, announce_sync=True)
            self.script_subtabs.setCurrentIndex(0)
        except Exception as exc:
            QMessageBox.critical(self, "Open Script", f"Failed to open script:\n{exc}")

    def create_new_script(self):
        default_dir = os.path.join(self.project_root, 'corel')
        path, _ = QFileDialog.getSaveFileName(self, "Create Script", default_dir, "Corel Files (*.corel)")
        if not path:
            return
        if not path.lower().endswith(".corel"):
            path += ".corel"

        if not os.path.exists(path):
            template = "--<k>\n\n// New script\nwait 10ms\n"
            with open(path, 'w') as file:
                file.write(template)
        self.open_script_file(path, announce_sync=True)
        self.refresh_script_library_list()
        self.script_subtabs.setCurrentIndex(0)

    def update_runtime_summary(self):
        if not hasattr(self, 'runtime_summary_label'):
            return
        presets_count = self.preset_list.count() if hasattr(self, 'preset_list') else 0
        bindings_count = len(self.script_bindings)
        cache_count = len(self.script_runtime_cache)
        scripts_count = self.script_library_list.count() if hasattr(self, 'script_library_list') else 0
        mode_label = "Compact" if self.compact_mode else "Expanded"
        self.runtime_summary_label.setText(
            f"Window: {mode_label} | Presets: {presets_count} | "
            f"Bindings: {bindings_count} | Cached AST: {cache_count} | Scripts found: {scripts_count}"
        )

    def setup_editor_shortcuts(self):
        self.shortcut_editor_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_editor_save.activated.connect(self.save_script)
        self.shortcut_editor_open = QShortcut(QKeySequence("Ctrl+O"), self)
        self.shortcut_editor_open.activated.connect(self.load_script)
        self.shortcut_editor_find = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_editor_find.activated.connect(self.focus_editor_find)
        self.shortcut_editor_run = QShortcut(QKeySequence("F5"), self)
        self.shortcut_editor_run.activated.connect(self.run_script_clicked)

    def focus_editor_find(self):
        if not hasattr(self, 'editor_find_input'):
            return
        self.editor_find_input.setFocus()
        self.editor_find_input.selectAll()

    def find_in_editor(self, forward=True):
        if not hasattr(self, 'script_editor'):
            return
        query = self.editor_find_input.text().strip()
        if not query:
            return

        flags = QTextDocument.FindFlags()
        if not forward:
            flags |= QTextDocument.FindBackward
        if self.editor_case_checkbox.isChecked():
            flags |= QTextDocument.FindCaseSensitively

        found = self.script_editor.find(query, flags)
        if found:
            return

        cursor = self.script_editor.textCursor()
        cursor.movePosition(QTextCursor.Start if forward else QTextCursor.End)
        self.script_editor.setTextCursor(cursor)
        self.script_editor.find(query, flags)

    def find_next_in_editor(self):
        self.find_in_editor(forward=True)

    def find_prev_in_editor(self):
        self.find_in_editor(forward=False)

    def update_editor_status_labels(self):
        if not hasattr(self, 'script_editor'):
            return
        cursor = self.script_editor.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.positionInBlock() + 1
        if hasattr(self, 'editor_position_label'):
            self.editor_position_label.setText(f"Ln {line}, Col {column}")
        if hasattr(self, 'editor_modified_label'):
            self.editor_modified_label.setText("Modified" if self.script_editor.document().isModified() else "Saved")
        if hasattr(self, 'current_script_label'):
            self.update_current_script_label()

    def mark_editor_clean(self):
        if hasattr(self, 'script_editor'):
            self.script_editor.document().setModified(False)
        self.update_editor_status_labels()
    
    def on_global_click(self, x, y, button, pressed):
        if button == mouse.Button.left:
            self.is_mouse_pressed = pressed
        elif button == mouse.Button.right:
            self.is_right_pressed = pressed

        if self.is_recoil_trigger_active():
            self.start_recoil_signal.emit()
        else:
            self.stop_recoil_signal.emit()

    def start_recoil(self):
        if self.recoil_checkbox.isChecked() and self.is_recoil_trigger_active() and not self.isActiveWindow():
            delay = max(1, self.delay_slider.value())
            self.recoil_timer.start(delay)
        self.update_recoil_runtime_label()

    def stop_recoil(self):
        self.recoil_timer.stop()
        self.update_recoil_runtime_label()

    def toggle_recoil(self):
        if self.recoil_checkbox.isChecked():
            self.start_recoil()
        else:
            self.stop_recoil()
        self.update_recoil_runtime_label()

    def apply_recoil(self):
        if self.recoil_checkbox.isChecked() and self.is_recoil_trigger_active() and not self.isActiveWindow():
            y_value = self.recoil_slider.value()
            x_value = self.recoil_x_slider.value()
            if y_value > 0 or x_value != 0:
                MOUSEEVENTF_MOVE = 0x0001
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, x_value, y_value, 0, 0)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = True
            self.offset = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = False

    def mouseMoveEvent(self, event):
        if self.mouse_pressed:
            self.move(self.pos() + event.pos() - self.offset)
    
    def normalize_hotkey(self, hotkey_text):
        if not hotkey_text or not hotkey_text.strip():
            raise ValueError("Hotkey cannot be empty.")

        parts = [part.strip().lower() for part in hotkey_text.split('+') if part.strip()]
        if not parts:
            raise ValueError("Hotkey cannot be empty.")

        modifier_aliases = {
            'ctrl': '<ctrl>',
            'control': '<ctrl>',
            'alt': '<alt>',
            'shift': '<shift>',
            'cmd': '<cmd>',
            'command': '<cmd>',
            'win': '<cmd>',
            'windows': '<cmd>',
            'super': '<cmd>',
            'meta': '<cmd>',
        }
        special_keys = {
            'space': '<space>',
            'enter': '<enter>',
            'return': '<enter>',
            'tab': '<tab>',
            'esc': '<esc>',
            'escape': '<esc>',
            'up': '<up>',
            'down': '<down>',
            'left': '<left>',
            'right': '<right>',
            'delete': '<delete>',
            'backspace': '<backspace>',
        }
        modifier_order = {'<ctrl>': 0, '<alt>': 1, '<shift>': 2, '<cmd>': 3}

        modifiers = set()
        key_token = None
        for part in parts:
            if part in modifier_aliases:
                modifiers.add(modifier_aliases[part])
                continue

            if part.startswith('<') and part.endswith('>'):
                candidate = part
            elif part in special_keys:
                candidate = special_keys[part]
            elif part.startswith('f') and part[1:].isdigit():
                number = int(part[1:])
                if number < 1 or number > 24:
                    raise ValueError("Function keys must be between F1 and F24.")
                candidate = f'<f{number}>'
            elif len(part) == 1:
                candidate = part
            else:
                raise ValueError(f'Unsupported key token: "{part}".')

            if key_token is not None:
                raise ValueError("Use only one non-modifier key in a hotkey.")
            key_token = candidate

        if key_token is None:
            raise ValueError("A hotkey must include at least one non-modifier key.")

        ordered_modifiers = sorted(modifiers, key=lambda item: modifier_order.get(item, 99))
        normalized = '+'.join(ordered_modifiers + [key_token])
        try:
            keyboard.HotKey.parse(normalized)
        except Exception as exc:
            raise ValueError(f'Invalid hotkey syntax: {exc}') from exc
        return normalized

    def extract_hotkey_from_script(self, script_path):
        try:
            with open(script_path, 'r') as file:
                source = file.read()
        except Exception as exc:
            raise ValueError(f"Failed to read script: {exc}") from exc

        match = re.search(r'^\s*--<([^>\r\n]+)>\s*$', source, flags=re.MULTILINE)
        if not match:
            raise ValueError('No trigger declaration found. Add one like --<k> at the top of the script.')

        trigger = match.group(1).strip()
        if not trigger:
            raise ValueError('Trigger declaration is empty. Use --<k> or --<ctrl+alt+k>.')
        return trigger

    def refresh_script_bindings_list(self):
        self.script_binding_list.clear()
        for hotkey in sorted(self.script_bindings.keys()):
            script_path = self.script_bindings[hotkey]
            item = QListWidgetItem(f"{hotkey} -> {script_path}")
            item.setData(Qt.UserRole, hotkey)
            self.script_binding_list.addItem(item)
        self.update_runtime_summary()

    def save_script_bindings(self):
        try:
            with open(self.script_bindings_file, 'w') as file:
                json.dump(self.script_bindings, file, indent=2)
        except Exception as exc:
            self.append_script_output(f"Failed to save script bindings: {exc}")

    def load_script_bindings(self):
        self.script_bindings = {}
        if os.path.exists(self.script_bindings_file):
            try:
                with open(self.script_bindings_file, 'r') as file:
                    loaded = json.load(file)
                if isinstance(loaded, dict):
                    for hotkey, script_path in loaded.items():
                        if isinstance(hotkey, str) and isinstance(script_path, str):
                            self.script_bindings[hotkey] = script_path
            except Exception as exc:
                self.append_script_output(f"Failed to load script bindings: {exc}")

        self.refresh_script_bindings_list()
        self.restart_hotkey_listener()
        self.prewarm_script_runtime_cache_async()
        self.update_runtime_summary()

    def create_hotkey_callback(self, script_path, hotkey):
        def callback():
            self.run_script_signal.emit(script_path, hotkey)
        return callback

    def restart_hotkey_listener(self):
        if self.hotkey_listener is not None:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
            self.hotkey_listener = None

        if not self.script_bindings:
            self.update_runtime_summary()
            return

        valid_bindings = {}
        removed_bindings = []
        for hotkey, script_path in self.script_bindings.items():
            if os.path.exists(script_path):
                valid_bindings[hotkey] = script_path
            else:
                removed_bindings.append((hotkey, script_path))

        if removed_bindings:
            self.script_bindings = valid_bindings
            self.save_script_bindings()
            self.refresh_script_bindings_list()
            for hotkey, script_path in removed_bindings:
                self.append_script_output(f"Removed missing script binding {hotkey}: {script_path}")

        if not valid_bindings:
            self.update_runtime_summary()
            return

        callbacks = {}
        for hotkey, script_path in valid_bindings.items():
            callbacks[hotkey] = self.create_hotkey_callback(script_path, hotkey)

        try:
            self.hotkey_listener = keyboard.GlobalHotKeys(callbacks)
            self.hotkey_listener.start()
        except Exception as exc:
            self.hotkey_listener = None
            self.append_script_output(f"Failed to start hotkey listener: {exc}")
        self.update_runtime_summary()

    def bind_loaded_script_hotkey(self):
        hotkey_text = self.hotkey_input.text().strip()

        if not self.current_script_path:
            self.current_script_path, _ = QFileDialog.getSaveFileName(self, "Save Script", "", "Corel Files (*.corel)")
            if not self.current_script_path:
                return

        self.save_script()
        self.add_or_update_script_binding(self.current_script_path, hotkey_text or None)

    def bind_script_file_hotkey(self):
        hotkey_text = self.hotkey_input.text().strip()

        script_path, _ = QFileDialog.getOpenFileName(self, "Select Script", "", "Corel Files (*.corel)")
        if not script_path:
            return
        self.add_or_update_script_binding(script_path, hotkey_text or None)

    def add_or_update_script_binding(self, script_path, hotkey_text=None):
        if not os.path.exists(script_path):
            QMessageBox.warning(self, "Bind Hotkey", f"Script file not found:\n{script_path}")
            return

        source_label = "manual input"
        if hotkey_text is None:
            try:
                hotkey_text = self.extract_hotkey_from_script(script_path)
                source_label = "script trigger"
            except ValueError as exc:
                QMessageBox.warning(self, "Bind Hotkey", str(exc))
                return

        try:
            normalized_hotkey = self.normalize_hotkey(hotkey_text)
        except ValueError as exc:
            QMessageBox.warning(self, "Bind Hotkey", str(exc))
            return

        abs_script_path = os.path.abspath(script_path)

        # A script can have only one binding: remove previous hotkeys pointing to this script.
        for existing_hotkey, existing_script in list(self.script_bindings.items()):
            if existing_hotkey != normalized_hotkey and os.path.abspath(existing_script) == abs_script_path:
                del self.script_bindings[existing_hotkey]

        previous_path = self.script_bindings.get(normalized_hotkey)
        if previous_path and os.path.abspath(previous_path) != abs_script_path:
            answer = QMessageBox.question(
                self,
                "Bind Hotkey",
                f'{normalized_hotkey} is already bound to:\n{previous_path}\n\nReplace it?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if answer != QMessageBox.Yes:
                return

        self.script_bindings[normalized_hotkey] = abs_script_path
        self.save_script_bindings()
        self.refresh_script_bindings_list()
        self.restart_hotkey_listener()
        self.append_script_output(f"Bound {normalized_hotkey} to {abs_script_path} ({source_label})")
        self.prime_script_runtime_cache(abs_script_path, announce=False)
        self.hotkey_input.clear()
        self.update_runtime_summary()

    def sync_script_binding_from_script(self, script_path, announce_changes=True, allow_new_binding=True):
        abs_script_path = os.path.abspath(script_path)

        existing_for_script = [
            hotkey for hotkey, existing_script in self.script_bindings.items()
            if os.path.abspath(existing_script) == abs_script_path
        ]

        if not existing_for_script and not allow_new_binding:
            return

        trigger_text = None
        normalized_hotkey = None
        parsing_error = None
        try:
            trigger_text = self.extract_hotkey_from_script(abs_script_path)
            normalized_hotkey = self.normalize_hotkey(trigger_text)
        except ValueError as exc:
            parsing_error = str(exc)

        changed = False
        for hotkey in existing_for_script:
            del self.script_bindings[hotkey]
            changed = True

        if normalized_hotkey is None:
            if changed:
                self.save_script_bindings()
                self.refresh_script_bindings_list()
                self.restart_hotkey_listener()
                if announce_changes:
                    self.append_script_output(f"Removed bindings for {abs_script_path} (no valid --<...> trigger).")
                self.update_runtime_summary()
            elif parsing_error and announce_changes:
                self.append_script_output(parsing_error)
            return

        conflict_path = self.script_bindings.get(normalized_hotkey)
        if conflict_path and os.path.abspath(conflict_path) != abs_script_path:
            if changed:
                self.save_script_bindings()
                self.refresh_script_bindings_list()
                self.restart_hotkey_listener()
                self.update_runtime_summary()
            if announce_changes:
                self.append_script_output(
                    f"Hotkey {normalized_hotkey} from script {abs_script_path} conflicts with {conflict_path}. "
                    "Keeping existing binding."
                )
            return

        if self.script_bindings.get(normalized_hotkey) != abs_script_path:
            self.script_bindings[normalized_hotkey] = abs_script_path
            changed = True

        if changed:
            self.save_script_bindings()
            self.refresh_script_bindings_list()
            self.restart_hotkey_listener()
            if announce_changes:
                self.append_script_output(
                    f"Synced script trigger {normalized_hotkey} from {abs_script_path}."
                )
            self.update_runtime_summary()

    def get_corel_runtime_module(self):
        if self.corel_runtime_module is not None:
            return self.corel_runtime_module

        runtime_path = os.path.join(self.project_root, 'corel', 'corel_interpreter.py')
        if not os.path.exists(runtime_path):
            raise RuntimeError(f"Corel interpreter not found: {runtime_path}")

        spec = importlib.util.spec_from_file_location("corel_runtime", runtime_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Failed to load corel_interpreter module.")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.corel_runtime_module = module
        return module

    def ensure_corel_executable(self):
        corel_dir = os.path.join(self.project_root, 'corel')
        corel_exe = os.path.join(corel_dir, 'target', 'debug', 'corel.exe')
        if os.path.exists(corel_exe):
            return corel_exe

        result = subprocess.run(
            ["cargo", "build"],
            cwd=corel_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            details = stderr or stdout or "unknown cargo build error"
            raise RuntimeError(f"Failed to build corel.exe: {details}")

        if not os.path.exists(corel_exe):
            raise RuntimeError(f"corel.exe not found after build: {corel_exe}")

        return corel_exe

    def compile_script_ast(self, script_path):
        runtime = self.get_corel_runtime_module()
        corel_dir = os.path.join(self.project_root, 'corel')
        corel_input = os.path.join(corel_dir, 'corel.corel')
        ast_path = os.path.join(corel_dir, 'ast.json')
        corel_exe = self.ensure_corel_executable()

        shutil.copyfile(script_path, corel_input)
        parse_result = subprocess.run(
            [corel_exe],
            cwd=corel_dir,
            capture_output=True,
            text=True
        )
        if parse_result.returncode != 0:
            stderr = parse_result.stderr.strip()
            stdout = parse_result.stdout.strip()
            details = stderr or stdout or "unknown parser error"
            raise RuntimeError(f"Corel parser failed: {details}")

        if not os.path.exists(ast_path):
            raise RuntimeError(f"AST file not generated: {ast_path}")

        with open(ast_path, 'r') as file:
            json_data = json.load(file)

        return runtime.build_ast_from_json(json_data)

    def get_cached_script_ast(self, script_path):
        abs_script_path = os.path.abspath(script_path)
        mtime = os.path.getmtime(abs_script_path)
        cache_entry = self.script_runtime_cache.get(abs_script_path)
        if cache_entry and cache_entry.get('mtime') == mtime and cache_entry.get('ast') is not None:
            return cache_entry['ast']

        ast = self.compile_script_ast(abs_script_path)
        self.script_runtime_cache[abs_script_path] = {
            'mtime': mtime,
            'ast': ast
        }
        self.update_runtime_summary()
        return ast

    def prime_script_runtime_cache(self, script_path, announce=False):
        try:
            self.get_cached_script_ast(script_path)
            if announce:
                self.append_script_output(f"Prepared runtime cache for {os.path.abspath(script_path)}")
        except Exception as exc:
            if announce:
                self.append_script_output(f"Could not prepare runtime cache: {exc}")

    def prewarm_script_runtime_cache_async(self):
        scripts = [path for path in self.script_bindings.values() if os.path.exists(path)]
        if not scripts:
            return

        def worker():
            for path in scripts:
                self.prime_script_runtime_cache(path, announce=False)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def execute_script_inprocess_thread(self, script_path, ast_nodes):
        success = True
        message = "Script finished successfully."
        try:
            runtime = self.get_corel_runtime_module()
            interpreter = runtime.CorelInterpreter(ast_nodes)
            interpreter.run()
        except Exception as exc:
            success = False
            message = f"Script finished with errors: {exc}"
        self.inprocess_finished_signal.emit(success, message)

    def on_inprocess_script_finished(self, success, message):
        with self.script_state_lock:
            self.script_running_inprocess = False
        self.append_script_output(message)
        self.run_script_button.setEnabled(True)
        self.update_runtime_summary()

    def remove_selected_script_binding(self):
        selected_item = self.script_binding_list.currentItem()
        if not selected_item:
            return

        hotkey = selected_item.data(Qt.UserRole)
        script_path = self.script_bindings.get(hotkey, "")
        answer = QMessageBox.question(
            self,
            "Remove Binding",
            f"Remove this binding?\n{hotkey} -> {script_path}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return

        if hotkey in self.script_bindings:
            del self.script_bindings[hotkey]
            self.save_script_bindings()
            self.refresh_script_bindings_list()
            self.restart_hotkey_listener()
            self.append_script_output(f"Removed binding {hotkey}")
            self.update_runtime_summary()

    def update_current_script_label(self):
        modified_suffix = ""
        if hasattr(self, 'script_editor') and self.script_editor.document().isModified():
            modified_suffix = " *"
        if self.current_script_path:
            abs_path = os.path.abspath(self.current_script_path)
            self.current_script_label.setText(f"Current file: {os.path.basename(abs_path)}{modified_suffix}")
            self.current_script_label.setToolTip(abs_path)
        else:
            self.current_script_label.setText(f"Current file: (none){modified_suffix}")
            self.current_script_label.setToolTip("")

    def open_script_file(self, path, announce_sync=True):
        abs_path = os.path.abspath(path)
        with open(abs_path, 'r') as file:
            self.script_editor.setPlainText(file.read())
        self.current_script_path = abs_path
        self.mark_editor_clean()
        self.update_current_script_label()
        self.sync_script_binding_from_script(abs_path, announce_changes=announce_sync, allow_new_binding=False)
        self.prime_script_runtime_cache(abs_path, announce=False)
        self.refresh_script_library_list()

    def open_script_from_binding_item(self, item):
        hotkey = item.data(Qt.UserRole)
        script_path = self.script_bindings.get(hotkey)
        if not script_path:
            return
        if not os.path.exists(script_path):
            self.append_script_output(f"Bound script no longer exists: {script_path}")
            self.restart_hotkey_listener()
            return

        try:
            self.open_script_file(script_path, announce_sync=False)
            self.script_subtabs.setCurrentIndex(0)
            self.append_script_output(f"Opened bound script: {script_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Open Script", f"Failed to open bound script:\n{exc}")

    def save_script(self):
        if not self.current_script_path:
            self.current_script_path, _ = QFileDialog.getSaveFileName(self, "Save Script", "", "Corel Files (*.corel)")

        if self.current_script_path:
            with open(self.current_script_path, 'w') as file:
                file.write(self.script_editor.toPlainText())
            self.mark_editor_clean()
            self.update_current_script_label()
            self.sync_script_binding_from_script(self.current_script_path, announce_changes=False, allow_new_binding=False)
            self.prime_script_runtime_cache(self.current_script_path, announce=False)
            self.refresh_script_library_list()

    def load_script(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Script", self.project_root, "Corel Files (*.corel)")
        if path:
            self.open_script_file(path, announce_sync=True)

    def delete_script(self):
        path = self.current_script_path
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Delete Script", "", "Corel Files (*.corel)")
            if not path:
                return

        if not os.path.exists(path):
            QMessageBox.warning(self, "Delete Script", f"File not found:\n{path}")
            return

        answer = QMessageBox.question(
            self,
            "Delete Script",
            f"Delete this script?\n{path}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return

        try:
            os.remove(path)
            abs_path = os.path.abspath(path)
            if abs_path in self.script_runtime_cache:
                del self.script_runtime_cache[abs_path]
            if os.path.abspath(path) == os.path.abspath(self.current_script_path or ""):
                self.current_script_path = None
                self.script_editor.clear()
                self.mark_editor_clean()
            self.update_current_script_label()
            self.append_script_output(f"Deleted script: {path}")
            self.refresh_script_library_list()
            self.update_runtime_summary()
        except OSError as exc:
            QMessageBox.critical(self, "Delete Script", f"Failed to delete script:\n{exc}")

    def append_script_output(self, text):
        if not text:
            return
        self.script_output.moveCursor(QTextCursor.End)
        self.script_output.insertPlainText(text)
        if not text.endswith('\n'):
            self.script_output.insertPlainText('\n')
        self.script_output.moveCursor(QTextCursor.End)

    def read_script_stdout(self):
        if self.corel_process is None:
            return
        output = bytes(self.corel_process.readAllStandardOutput()).decode('utf-8', errors='replace')
        self.append_script_output(output)

    def read_script_stderr(self):
        if self.corel_process is None:
            return
        output = bytes(self.corel_process.readAllStandardError()).decode('utf-8', errors='replace')
        self.append_script_output(output)

    def on_script_finished(self, exit_code, _exit_status):
        if exit_code == 0:
            self.append_script_output("Script finished successfully.")
        else:
            self.append_script_output(f"Script finished with errors. Exit code: {exit_code}")
        self.run_script_button.setEnabled(True)
        self.update_runtime_summary()

    def run_script_clicked(self):
        auto_save = self.auto_save_on_run_checkbox.isChecked() if hasattr(self, 'auto_save_on_run_checkbox') else True
        self.run_script(save_current=auto_save, trigger_source="manual")

    def run_script_from_hotkey(self, script_path, hotkey):
        self.run_script(script_path=script_path, save_current=False, trigger_source=f"hotkey {hotkey}")

    def run_script(self, script_path=None, save_current=True, trigger_source="manual"):
        if os.name != 'nt':
            self.append_script_output("Running Corel scripts is currently supported only on Windows.")
            return

        with self.script_state_lock:
            if self.script_running_inprocess:
                self.append_script_output("A script is already running.")
                return

        if self.corel_process and self.corel_process.state() != QProcess.NotRunning:
            self.append_script_output("A script is already running.")
            return

        if script_path is None:
            if not self.current_script_path:
                self.current_script_path, _ = QFileDialog.getSaveFileName(
                    self, "Save Script Before Running", "", "Corel Files (*.corel)"
                )
                if not self.current_script_path:
                    return

            if save_current:
                self.save_script()
            script_path = os.path.abspath(self.current_script_path)
        else:
            script_path = os.path.abspath(script_path)
            if save_current and self.current_script_path and os.path.abspath(self.current_script_path) == script_path:
                self.save_script()

        if not os.path.exists(script_path):
            self.append_script_output(f"Script file not found: {script_path}")
            return

        clear_before_run = self.clear_output_before_run_checkbox.isChecked() if hasattr(self, 'clear_output_before_run_checkbox') else True

        # Fast path: run precompiled AST in-process (avoids per-trigger process startup).
        try:
            ast_nodes = self.get_cached_script_ast(script_path)
            if clear_before_run:
                self.script_output.clear()
            self.append_script_output(f"Trigger: {trigger_source}")
            self.append_script_output(f"Running script: {script_path}")
            self.run_script_button.setEnabled(False)
            with self.script_state_lock:
                self.script_running_inprocess = True
            worker = threading.Thread(
                target=self.execute_script_inprocess_thread,
                args=(script_path, ast_nodes),
                daemon=True
            )
            worker.start()
            return
        except Exception as exc:
            self.append_script_output(f"In-process runtime unavailable, using runner fallback: {exc}")

        corel_dir = os.path.join(self.project_root, 'corel')
        runner = os.path.join(corel_dir, 'corel.bat')
        if not os.path.exists(runner):
            self.append_script_output(f"Runner not found: {runner}")
            return

        if clear_before_run:
            self.script_output.clear()
        self.append_script_output(f"Trigger: {trigger_source}")
        self.append_script_output(f"Running script: {script_path}")
        self.append_script_output("Please wait...")

        if self.corel_process:
            self.corel_process.deleteLater()

        self.corel_process = QProcess(self)
        self.corel_process.setWorkingDirectory(corel_dir)
        self.corel_process.readyReadStandardOutput.connect(self.read_script_stdout)
        self.corel_process.readyReadStandardError.connect(self.read_script_stderr)
        self.corel_process.finished.connect(self.on_script_finished)

        self.run_script_button.setEnabled(False)
        self.corel_process.start("cmd.exe", ["/c", runner, script_path])
        if not self.corel_process.waitForStarted(3000):
            self.append_script_output("Failed to start script runner process.")
            self.run_script_button.setEnabled(True)

    def closeEvent(self, event):
        if hasattr(self, 'ui_stats_timer') and self.ui_stats_timer is not None:
            self.ui_stats_timer.stop()

        try:
            if hasattr(self, 'listener') and self.listener is not None:
                self.listener.stop()
        except Exception:
            pass

        try:
            if self.hotkey_listener is not None:
                self.hotkey_listener.stop()
                self.hotkey_listener = None
        except Exception:
            pass

        if self.corel_process and self.corel_process.state() != QProcess.NotRunning:
            self.corel_process.kill()
            self.corel_process.waitForFinished(1000)

        with self.script_state_lock:
            self.script_running_inprocess = False

        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = ModMenu(app)
    win.show()
    sys.exit(app.exec_())
