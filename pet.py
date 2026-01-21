import sys
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QMenu, 
                             QAction, QWidget, QVBoxLayout, QTextEdit, 
                             QLineEdit, QPushButton, QSystemTrayIcon, QListWidget, QMessageBox)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QPixmap, QCursor, QIcon
from main import PriestessAI
import shutil
import os
import subprocess

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
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
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


class IngestionWorker(QThread):
    finished = pyqtSignal()
    
    def run(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(base_dir, 'ingest.py')
        if os.path.exists(script_path):
            try:
                subprocess.run([sys.executable, script_path], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Ingestion failed: {e}")
        self.finished.emit()

class DropWindow(QWidget):
    ingestion_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("投喂")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.resize(300, 300)
        self.setAcceptDrops(True)
        
        self.layout = QVBoxLayout()
        self.label = QLabel("把文件拖到这里投喂给普瑞赛斯\n\n关闭窗口开始消化")
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)
        
        self.file_list = QListWidget()
        self.layout.addWidget(self.file_list)
        
        self.setLayout(self.layout)
        self.worker = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]

        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, 'data')
        
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        count = 0
        for f_path in files:
            if os.path.isfile(f_path):
                try:
                    shutil.copy(f_path, data_dir)
                    file_name = os.path.basename(f_path)
                    self.file_list.addItem(f"已接收: {file_name}")
                    count += 1
                except Exception as e:
                    print(f"Error copying {f_path}: {e}")
                    self.file_list.addItem(f"错误: {os.path.basename(f_path)}")
        
        self.label.setText(f"本次新增 {count} 个文件\n关闭窗口以开始消化...")
        self.file_list.scrollToBottom()

    def closeEvent(self, event):
        if self.file_list.count() > 0:
            print("Starting ingestion in background...")
            self.worker = IngestionWorker()
            self.worker.finished.connect(self.on_ingestion_finished)
            self.worker.start()
            
        event.accept()

    def on_ingestion_finished(self):
        print("Ingestion finished via thread.")
        self.ingestion_finished.emit()


class DesktopPet(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.ai = PriestessAI()
        
        self.initUI()
        self.chat_window = ChatWindow(self.ai)
        self.drop_window = DropWindow()
        self.drop_window.ingestion_finished.connect(self.ai.reload_knowledge)
        
        self.drag_position = QPoint()
    
    def openFeed(self):
        pet_rect = self.geometry()
        feed_width = self.drop_window.width()
        feed_height = self.drop_window.height()
        
        self.drop_window.file_list.clear()
        self.drop_window.label.setText("把文件拖到这里投喂给普瑞赛斯\n\n关闭窗口开始消化")
        
        x = pet_rect.x() + pet_rect.width() + 20
        y = pet_rect.y()
        
        self.drop_window.move(x, y)
        self.drop_window.show()
        self.drop_window.activateWindow()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
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
        
        chat_action = QAction("对话", self)
        chat_action.triggered.connect(self.openChat)
        menu.addAction(chat_action)
        
        feed_action = QAction("投喂", self)
        feed_action.triggered.connect(self.openFeed)
        menu.addAction(feed_action)
        
        clear_action = QAction("清空记忆", self)
        clear_action.triggered.connect(self.clear_data)
        menu.addAction(clear_action)
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        
        menu.exec_(pos)
        
    def clear_data(self):
        reply = QMessageBox.question(self, '确认', 
                                     "确定要清空所有数据吗？普瑞赛斯将遗忘所有已投喂的知识。",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, 'data')
            
            # Clear data directory
            if os.path.exists(data_dir):
                for filename in os.listdir(data_dir):
                    file_path = os.path.join(data_dir, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"Failed to delete {file_path}. Reason: {e}")
            
            print("Data directory cleared. Starting ingestion to reset DB...")
            
            self.worker = IngestionWorker()
            self.worker.finished.connect(self.on_ingestion_finished)
            self.worker.start()
            
    def on_ingestion_finished(self):
        print("Ingestion (Reset) finished.")
        self.ai.reload_knowledge()
        QMessageBox.information(self, "完成", "普瑞赛斯的记忆已重置。")

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
    app.setQuitOnLastWindowClosed(False)
    pet = DesktopPet()
    sys.exit(app.exec_())
