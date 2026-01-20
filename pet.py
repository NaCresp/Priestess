import sys
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QMenu, 
                             QAction, QWidget, QVBoxLayout, QTextEdit, 
                             QLineEdit, QPushButton, QSystemTrayIcon)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QCursor, QIcon
from main import PriestessAI

class ChatWorker(QObject):
    finished = pyqtSignal()
    response_chunk = pyqtSignal(str)

    def __init__(self, ai, query):
        super().__init__()
        self.ai = ai
        self.query = query

    def run(self):
        for chunk in self.ai.chat(self.query):
            self.response_chunk.emit(chunk)
        self.finished.emit()

class ChatWindow(QWidget):
    def __init__(self, ai):
        super().__init__()
        self.ai = ai
        self.setWindowTitle("普瑞赛斯 - 对话")
        self.resize(400, 500)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.history_display = QTextEdit()
        self.history_display.setReadOnly(True)
        self.layout.addWidget(self.history_display)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("想和普瑞赛斯说什么...")
        self.input_field.returnPressed.connect(self.send_message)
        self.layout.addWidget(self.input_field)

        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.send_message)
        self.layout.addWidget(self.send_btn)
        
        self.current_worker = None

    def send_message(self):
        user_input = self.input_field.text().strip()
        if not user_input:
            return

        self.history_display.append(f"<b>博士:</b> {user_input}")
        self.input_field.clear()
        self.input_field.setDisabled(True)

        self.history_display.append("<b>普瑞赛斯:</b> ")

        self.worker = ChatWorker(self.ai, user_input)
        
        self.worker.response_chunk.connect(self.update_response)
        self.worker.finished.connect(self.enable_input)
        
        self.worker_thread = threading.Thread(target=self.worker.run)
        self.worker_thread.start()

    def update_response(self, text):
        cursor = self.history_display.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self.history_display.setTextCursor(cursor)
        self.history_display.ensureCursorVisible()

    def enable_input(self):
        self.history_display.append("\n")
        self.input_field.setDisabled(False)
        self.input_field.setFocus()


class DesktopPet(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.ai = PriestessAI()
        
        self.initUI()
        self.chat_window = ChatWindow(self.ai)
        
        self.drag_position = QPoint()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_label = QLabel()
        pixmap = QPixmap("priestess.jpg")
        
        pixmap = pixmap.scaledToWidth(120, Qt.SmoothTransformation)
             
        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.image_label)
        
        self.resize(pixmap.width(), pixmap.height())
        self.center()
        self.show()

    def center(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, 
                  (screen.height() - size.height()) // 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.showContextMenu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.snapToEdge()
            event.accept()

    def snapToEdge(self):
        screen = QApplication.primaryScreen().geometry()
        win_geo = self.geometry()
        
        x = win_geo.x()
        y = win_geo.y()
        w = win_geo.width()
        h = win_geo.height()
        
        threshold = 200
        
        if x < threshold:
            x = 0
        elif x + w > screen.width() - threshold:
            x = screen.width() - w
            
        if y < threshold:
            y = 0
        elif y + h > screen.height() - 20:
             y = screen.height() - h
             
        self.move(x, y)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.openChat()

    def showContextMenu(self, pos):
        menu = QMenu(self)
        
        chat_action = QAction("对话 (Chat)", self)
        chat_action.triggered.connect(self.openChat)
        menu.addAction(chat_action)
        
        quit_action = QAction("退出 (Exit)", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        
        menu.exec_(pos)

    def openChat(self):
        pet_rect = self.geometry()
        screen_rect = QApplication.primaryScreen().geometry()
        
        chat_width = self.chat_window.width()
        chat_height = self.chat_window.height()
        
        x = pet_rect.x() + pet_rect.width() + 5
        y = pet_rect.y()
        
        if x + chat_width > screen_rect.width():
            x = pet_rect.x() - chat_width - 5
            
        if y + chat_height > screen_rect.height():
            y = screen_rect.height() - chat_height - 5
            
        if y < 0:
            y = 5

        self.chat_window.move(x, y)

        if self.chat_window.isVisible():
            self.chat_window.activateWindow()
        else:
            self.chat_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet()
    sys.exit(app.exec_())
