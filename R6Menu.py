import sys
import ctypes
import os
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QPushButton, QListWidget, QLineEdit, QLabel, QCheckBox, QSlider, QPlainTextEdit, QHBoxLayout, QCompleter, QFileDialog, QComboBox, QColorDialog
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QRegExp
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QBrush, QColor, QFont, QRegExpValidator, QTextCursor
import pyautogui
from pynput import mouse

class ScriptEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = None

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

        # Macro key start definition
        macro_font = QTextCharFormat()
        macro_font.setForeground(QColor(60, 64, 94))
        macro_font.setFontWeight(QFont.Bold)
        macros = [r'--<[a-zA-Z]+>'] # e.g. --<macro>
        self.add_rule(macros, macro_font)

        # Function
        function_font = QTextCharFormat()
        function_font.setForeground(Qt.darkMagenta)
        function_font.setFontWeight(QFont.Bold)
        keywords = ['wait', 'press', 'move', 'click', 'move']
        self.add_rule(keywords, function_font)

        # Keywords
        keyword_font = QTextCharFormat()
        keyword_font.setForeground(Qt.darkYellow)
        keyword_font.setFontWeight(QFont.Bold)
        keywords = ['loop']
        self.add_rule(keywords, keyword_font)

        # Numbers and times (e.g. 1s, 2ms)
        number_font = QTextCharFormat()
        number_font.setForeground(Qt.darkRed)
        numbers = [r'\b\d+(?:ms|s|ds|cs|x|y)?\b']
        self.add_rule(numbers, number_font)

        # Strings
        string_font = QTextCharFormat()
        string_font.setForeground(QColor('green'))
        strings = ['".*"', "'.*'"]
        self.add_rule(strings, string_font)

        # Comments
        comment_font = QTextCharFormat()
        comment_font.setForeground(Qt.darkGreen)
        comments = ['//.*']
        self.add_rule(comments, comment_font)

    def add_rule(self, patterns, format):
        for pattern in patterns:
            expression = QRegExp(pattern)
            self.rules.append((expression, format))

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

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.initUI()
        self.load_presets()
        self.load_theme_preferences()

        self.recoil_timer = QTimer()
        self.recoil_timer.timeout.connect(self.apply_recoil)
        self.mouse_pressed = False
        self.is_mouse_pressed = False
        self.is_right_pressed = False
        self.dragging = False
        self.offset = QPoint()
        self.setWindowOpacity(0.9)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        # Start the mouse listener
        self.listener = mouse.Listener(on_click=self.on_global_click)
        self.listener.start()

        # Connect signals
        self.start_recoil_signal.connect(self.start_recoil)
        self.stop_recoil_signal.connect(self.stop_recoil)

    def initUI(self):
        self.app = QApplication([])
        self.app.setStyle("Fusion")

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle('Rainbow 6 Siege Mod Menu')
        self.setFixedSize(400, 300)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        tab_widget = QTabWidget()
        central_layout = QVBoxLayout()
        central_layout.addWidget(tab_widget)
        central_widget.setLayout(central_layout)

        recoil_tab = QWidget()
        config_tab = QWidget()
        script_tab = QWidget()

        tab_widget.addTab(recoil_tab, 'Recoil')
        tab_widget.addTab(config_tab, 'Configs')
        tab_widget.addTab(script_tab, 'Scripts')
        
        # Create the recoil tab
        recoil_layout = QVBoxLayout()
        recoil_tab.setLayout(recoil_layout)

        self.recoil_checkbox = QCheckBox('Recoil Manager', self)
        self.recoil_checkbox.stateChanged.connect(self.toggle_recoil)
        recoil_layout.addWidget(self.recoil_checkbox)

        self.recoil_slider_label = QLabel('Recoil Control Y:')
        recoil_layout.addWidget(self.recoil_slider_label)

        self.recoil_slider = QSlider(Qt.Horizontal)
        self.recoil_slider.setMinimum(0)
        self.recoil_slider.setMaximum(100)
        self.recoil_slider.valueChanged.connect(self.update_slider_value)
        recoil_layout.addWidget(self.recoil_slider)

        self.recoil_x_slider_label = QLabel('Recoil Control X:')
        recoil_layout.addWidget(self.recoil_x_slider_label)
        
        self.recoil_x_slider = QSlider(Qt.Horizontal)
        self.recoil_x_slider.setMinimum(-100)
        self.recoil_x_slider.setMaximum(100)
        self.recoil_x_slider.setValue(0) # Start in the middle
        self.recoil_x_slider.valueChanged.connect(self.update_x_slider_value)
        recoil_layout.addWidget(self.recoil_x_slider)

        self.delay_slider_label = QLabel('Delay (ms):')
        recoil_layout.addWidget(self.delay_slider_label)

        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setMinimum(0)
        self.delay_slider.setMaximum(1000)
        self.delay_slider.valueChanged.connect(self.update_delay_value)
        recoil_layout.addWidget(self.delay_slider)
        
        # Create the config tab
        config_layout = QVBoxLayout()
        config_tab.setLayout(config_layout)

        save_button = QPushButton('Save')
        save_button.clicked.connect(self.save_preset)
        load_button = QPushButton('Load')
        load_button.clicked.connect(self.load_preset)
        config_layout.addWidget(save_button)
        config_layout.addWidget(load_button)

        self.preset_name_label = QLabel('Preset Name:')
        self.preset_name_edit = QLineEdit()
        config_layout.addWidget(self.preset_name_label)
        config_layout.addWidget(self.preset_name_edit)

        self.preset_list = QListWidget()
        config_layout.addWidget(self.preset_list)

        delete_button = QPushButton('Delete')
        delete_button.clicked.connect(self.delete_preset)
        config_layout.addWidget(delete_button)

        # Create the script tab
        script_layout = QVBoxLayout()
        script_tab.setLayout(script_layout)

        #  Script editor
        self.script_editor = ScriptEditor()
        self.highlighter = ScriptSyntaxHighlighter(self.script_editor.document())
        script_layout.addWidget(self.script_editor)

        completer = QCompleter(["wait", "press", "move", "loop", 'click'])
        self.script_editor.setCompleter(completer)    

        script_management_layout = QVBoxLayout()
        script_layout.addLayout(script_management_layout)

        save_script_button = QPushButton('Save Script')
        save_script_button.clicked.connect(self.save_script)
        script_management_layout.addWidget(save_script_button)

        load_script_button = QPushButton('Load Script')
        load_script_button.clicked.connect(self.load_script)
        script_management_layout.addWidget(load_script_button)

        delete_script_button = QPushButton('Delete Script')
        delete_script_button.clicked.connect(self.delete_script)
        script_management_layout.addWidget(delete_script_button)

        # Theme tab
        themes_tab = QWidget()
        tab_widget.addTab(themes_tab, 'Themes')
        self.createThemesTab(themes_tab)

        # Set the stylesheet
        self.setStyleSheet("""
            QSlider {
                background-color: transparent;
                height: 10px;
            }
            QSlider::groove:horizontal {
                height: 10px;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                width: 15px;
                margin: -2px 0;
                border-radius: 7px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 10px;
            }
        """)

        
        self.show()

    def createThemesTab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)

        # Dropdown for preset themes
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(['default', 'gruvbox dark', 'serika dark', 'catpuccin mocha', 'milkshake', 'cafe', 'blueberry light', 'cheesecake', 'starclass', 'honey', 'hot chocolate', 'TMO', 'nene'])
        layout.addWidget(self.theme_selector)
        self.theme_selector.currentIndexChanged.connect(self.applyPresetTheme)

        # Theme preview section
        self.createThemePreviewSection(layout)

    def createThemePreviewSection(self, layout):
        # Add a label for preview
        preview_label = QLabel("Theme Preview")
        preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(preview_label)

        # Add a test button
        test_button = QPushButton("Test Button")
        layout.addWidget(test_button)

        # Add some sample text
        sample_text = QLabel("This is a sample text for theme preview.")
        sample_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(sample_text)

        # Add a slider for preview
        preview_slider = QSlider(Qt.Horizontal)
        layout.addWidget(preview_slider)

        # Add a checkbox for preview
        preview_checkbox = QCheckBox("Sample Checkbox")
        layout.addWidget(preview_checkbox)

    def applyPresetTheme(self):
        theme_name = self.theme_selector.currentText()
        self.save_theme_preferences(theme_name)
        # List of presets:
        preset_themes = {
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
            # I made these myself
            "honey": {
                "background": "#FFF8E1",  # Light honey or cream
                "primary": "#FFC107",    # Vibrant honey or gold
                "secondary": "#FFB300",  # Deeper honey or amber
                "accent": "#FFD54F",     # Soft honey or light amber
                "text": "#795548"        # Rich brown, resembling honeycomb or bees
            },
            "starclass": { # Inspired by Starbucks but I don't want to get sued so I'm calling it Starclass :thumbsup:
                "background": "#D4E9E2",  # Light mint or soft green, reminiscent of a Starbucks cup
                "primary": "#00704A",    # Starbucks green
                "secondary": "#005241",  # Deeper green, for contrast
                "accent": "#A5D6A7",     # Lighter green, for highlights
                "text": "#3E2723"        # Dark brown, like coffee beans
            },
            "TMO": { # Inspired by BMO from Adventure Time
                "background": "#A7DBC8",  # Soft teal, similar to BMO's body
                "primary": "#59CE8F",     # Light green, like BMO's face
                "secondary": "#507C7E",   # Darker teal, for contrast
                "accent": "#A1E8AF",      # Pale green, for highlights
                "text": "#3A4042"         # Dark grey, for text
            },
            "hot chocolate": { # Inspired by hot chocolate, coffee and marshmallows
                "background": "#FFF4E6",  # Creamy off-white, like milk foam
                "primary": "#8C5E58",     # Warm brown, like hot chocolate
                "secondary": "#AA8073",   # Lighter brown, for contrast
                "accent": "#D3A99A",      # Soft pink, reminiscent of marshmallows
                "text": "#5A3B35"         # Darker brown, for text
            },
            "nene": { # She is my beatiful, perfect girl. She has amazing blue eyes, and loves light blue and cyan. She is my everything. https://www.instagram.com/heyits.nene/
                "background": "#E0F7FA",  # Light cyan, airy and light
                "primary": "#4DD0E1",     # Light blue, like her eyes
                "secondary": "#26C6DA",   # Slightly darker blue, for depth
                "accent": "#B2EBF2",      # Pale blue, for a softer touch
                "text": "#00838F"         # Dark teal, for readable text
            },
            'default': {
                "background": "#e6e6e6", "primary": "#007BFF", "secondary": "#0056b3", "accent": "#0056b3", "text": "#ffffff"
            }
        }
        colors = preset_themes.get(theme_name, ['#ffffff', '#000000', '#888888'])
        self.applyTheme(colors)

    def save_theme_preferences(self, theme_name):
        try:
            with open('theme_preferences.json', 'w') as f:
                json.dump({'theme': theme_name}, f)
        except Exception as e:
            print(f"Error saving theme preferences: {e}")

    def load_theme_preferences(self):
        if os.path.exists('theme_preferences.json'):
            try:
                with open('theme_preferences.json', 'r') as f:
                    theme_preferences = json.load(f)
                    theme_name = theme_preferences.get('theme', 'default')
                    index = self.theme_selector.findText(theme_name)
                    if index >= 0:
                        self.theme_selector.setCurrentIndex(index)
                        self.applyPresetTheme()
            except Exception as e:
                print(f"Error loading theme preferences: {e}")
        else:
            print("Theme preferences file not found.")

    def chooseColor(self):
        color = QColorDialog.getColor()
        if color.isValid():
            sender = self.sender()
            sender.setStyleSheet(f'background-color: {color.name()}')

    def applyCustomTheme(self):
        colors = [btn.palette().button().color().name() for btn in self.custom_color_buttons]
        self.applyTheme(colors)

    def applyTheme(self, colors):
        if not all(key in colors for key in ['background', 'primary', 'secondary', 'accent', 'text']):
            raise Exception('Invalid theme colors, must be a list of hex values for background, primary, secondary, accent, and text')

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {colors['background']};
                color: {colors['text']};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QPushButton {{
                background-color: {colors['primary']};
                color: {colors['text']};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                margin: 4px;
            }}
            QPushButton:hover {{
                background-color: {colors['accent']};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid #999999;
                height: 8px;
                background: {colors['secondary']};
                margin: 2px 0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {colors['primary']};
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }}
            QCheckBox {{
                spacing: 5px;
                color: {colors['text']};  /* Ensure text color for QCheckBox */
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QTabWidget::pane {{
                border-top: 2px solid {colors['secondary']};
                position: absolute;
                top: -0.5em;
                color: {colors['text']};
                background: {colors['background']};
            }}
            QTabBar::tab {{
                background: {colors['secondary']};
                color: {colors['text']};
                border-bottom: 2px solid transparent;
                padding: 10px;
                margin: 0px;
            }}
            QTabBar::tab:selected {{
                background: {colors['primary']};
                border-bottom-color: {colors['accent']};
            }}
            QListWidget, QLineEdit, QPlainTextEdit, QComboBox {{
                border: 1px solid {colors['secondary']};
                border-radius: 4px;
                padding: 3px;
                background: {colors['background']};
                color: {colors['text']};  /* Ensure text color for input fields */
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QLabel {{
                margin: 6px;
                color: {colors['text']};  /* Ensure text color for QLabel */
            }}
        """)

        # Update specific widgets if necessary
        self.preset_list.setStyleSheet(f"color: {colors['text']};")
        self.preset_name_edit.setStyleSheet(f"color: {colors['text']};")

    def update_slider_value(self, value):
        self.recoil_slider_label.setText(f'Recoil Control Y: {value}')

    def update_x_slider_value(self, value):
        self.recoil_x_slider_label.setText(f'Recoil Control X: {value}')

    def update_delay_value(self, value):
        self.delay_slider_label.setText(f'Delay (ms): {value}')

    def save_preset(self):
        name = self.preset_name_edit.text()
        y_value = self.recoil_slider.value()
        x_value = self.recoil_x_slider.value()
        delay = self.delay_slider.value()
        if name:
            item = f'{name} - Y: {y_value} - X: {x_value} - Delay: {delay} ms'
            self.preset_list.addItem(item)
            self.preset_name_edit.clear()
            self.recoil_slider.setValue(0)
            self.recoil_x_slider.setValue(0)
            self.delay_slider.setValue(0)
            self.update_slider_value(0)
            self.update_x_slider_value(0)  # Update the X slider label
            self.update_delay_value(0)
            self.save_presets()

    def load_preset(self):
        selected_item = self.preset_list.currentItem()
        if selected_item:
            text = selected_item.text()
            parts = text.split(' - ')
            if len(parts) == 4:
                name = parts[0].strip()
                y_value = int(parts[1].split(': ')[1])
                x_value = int(parts[2].split(': ')[1])
                delay = int(parts[3].split(': ')[1].split(' ms')[0])
                self.preset_name_edit.setText(name)
                self.recoil_slider.setValue(y_value)
                self.recoil_x_slider.setValue(x_value)
                self.delay_slider.setValue(delay)
                self.update_slider_value(y_value)
                self.update_x_slider_value(x_value)  # Update the X slider label
                self.update_delay_value(delay)

    def delete_preset(self):
        selected_item = self.preset_list.currentItem()
        if selected_item:
            self.preset_list.takeItem(self.preset_list.row(selected_item))
            self.save_presets()

    def save_presets(self):
        presets = []
        for index in range(self.preset_list.count()):
            item = self.preset_list.item(index)
            presets.append(item.text())
        with open('presets.txt', 'w') as file:
            file.write('\n'.join(presets))

    def load_presets(self):
        try:
            with open('presets.txt', 'r') as file:
                presets = file.read().splitlines()
                self.preset_list.addItems(presets)
        except FileNotFoundError:
            pass
    
    def on_global_click(self, x, y, button, pressed):
        if button == mouse.Button.left:
            self.is_mouse_pressed = pressed
        elif button == mouse.Button.right:
            self.is_right_pressed = pressed

        if self.is_mouse_pressed and self.is_right_pressed:
            self.start_recoil_signal.emit()
        else:
            self.stop_recoil_signal.emit()

    def start_recoil(self):
        if self.recoil_checkbox.isChecked() and not self.isActiveWindow():
            delay = self.delay_slider.value()
            self.recoil_timer.start(delay)

    def stop_recoil(self):
        self.recoil_timer.stop()

    def toggle_recoil(self):
        if self.recoil_checkbox.isChecked():
            self.start_recoil()
        else:
            self.stop_recoil()

    def apply_recoil(self):
        if self.recoil_checkbox.isChecked() and self.is_mouse_pressed and not self.isActiveWindow():
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
    
    def save_script(self):
        if not hasattr(self, 'current_script_path') or self.current_script_path is None:
            self.current_script_path, _ = QFileDialog.getSaveFileName(self, "Save Script", "", "Corel Files (*.corel)")

        if self.current_script_path:
            with open(self.current_script_path, 'w') as file:
                file.write(self.script_editor.toPlainText())

    def load_script(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Script", "", "Corel Files (*.corel)")
        if path:
            with open(path, 'r') as file:
                self.script_editor.setPlainText(file.read())
            self.current_script_path = path

    def delete_script(self):
        # TODO: Implement this. I'm thinking about deleting this, as you could just use the OS to delete the file.
        pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = ModMenu(app)
    win.show()
    sys.exit(app.exec_())
