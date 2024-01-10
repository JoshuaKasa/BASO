import sys
import ctypes
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QPushButton, QListWidget, QLineEdit, QLabel, QCheckBox, QSlider, QPlainTextEdit, QHBoxLayout, QCompleter, QFileDialog
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

        # Set the stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #e6e6e6; /* Gray background */
            }
            QPushButton {
                background-color: #007BFF; /* Blue button background */
                color: white;
                border: none;
                border-radius: 15px; /* Adjust this value for rounder or sharper edges */
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #0056b3; /* Darker blue on hover */
            }
            QSlider {
                background-color: transparent;
                height: 10px;
            }
            QSlider::groove:horizontal {
                background: #ccc;
                height: 10px;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #007BFF; /* Blue slider handle */
                width: 15px;
                margin: -2px 0;
                border-radius: 7px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 10px; /* Adjust this value for rounder or sharper edges */
            }
        """)

        
        self.show()

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
