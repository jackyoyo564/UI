from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from user_manager import UserManager
import json
import os
import requests

API_BASE_URL = "http://127.0.0.1:5000"

class LoginWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 需要 app 時這樣取得
        self.app = QApplication.instance()
        # self.user_manager = UserManager()  # 不再用本地 user_manager
        self.setWindowTitle("登入系統")
        self.should_quit = True
        
        self.load_window_size()
        
        font = QFont("Arial", 12)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.account_label = QLabel("帳號:", self)
        self.account_label.setFont(font)
        self.account_input = QLineEdit(self)
        self.account_input.setFont(font)
        self.account_input.setPlaceholderText("請輸入帳號")
        self.account_input.returnPressed.connect(self.handle_login)
        
        self.password_label = QLabel("密碼:", self)
        self.password_label.setFont(font)
        self.password_input = QLineEdit(self)
        self.password_input.setFont(font)
        self.password_input.setPlaceholderText("請輸入密碼")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.handle_login)
        
        button_layout = QHBoxLayout()
        self.quit_button = QPushButton("退出", self)
        self.quit_button.setFont(font)
        self.quit_button.clicked.connect(self.handle_quit)
        
        self.login_button = QPushButton("登入", self)
        self.login_button.setFont(font)
        self.login_button.clicked.connect(self.handle_login)
        
        button_layout.addWidget(self.quit_button, alignment=Qt.AlignLeft)
        button_layout.addStretch()
        button_layout.addWidget(self.login_button, alignment=Qt.AlignRight)
        
        main_layout.addWidget(self.account_label)
        main_layout.addWidget(self.account_input)
        main_layout.addWidget(self.password_label)
        main_layout.addWidget(self.password_input)
        main_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(30, 5, 30, 30)
        main_layout.setAlignment(Qt.AlignCenter)
    
    def handle_login(self):
        try:
            account = self.account_input.text()
            password = self.password_input.text()
            # 呼叫 API 登入
            resp = requests.post(f"{API_BASE_URL}/api/login", json={"username": account, "password": password})
            data = resp.json()
            if data.get("success"):
                role = data.get("role")
                role_display = "管理員" if role == "manager" else "操作員" if role == "operator" else "維修員"
                print(f"登入成功，帳號: {account}, 身分: {role_display}")
                self.should_quit = False
                self.close()
                from main_window import MainWindow
                self.main_window = MainWindow(role)
                self.main_window.show()
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                print("已顯示主視窗")
            else:
                QMessageBox.warning(self, "錯誤", data.get("msg", "帳號或密碼錯誤"))
        except Exception as e:
            print(f"登入失敗：{str(e)}")
            QMessageBox.critical(self, "錯誤", f"登入過程中發生錯誤：{str(e)}")

    def handle_quit(self):
        print("正在退出應用程式...")
        self.should_quit = True
        self.close()

    def load_window_size(self):
        try:
            with open("window_sizes.json", "r") as f:
                sizes = json.load(f)
                width = sizes.get("login_window_width", 400)
                height = sizes.get("login_window_height", 240)
                self.resize(width, height)
        except (FileNotFoundError, json.JSONDecodeError):
            self.resize(400, 240)

    def closeEvent(self, event):
        sizes = {}
        try:
            with open("window_sizes.json", "r") as f:
                sizes = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        sizes["login_window_width"] = self.width()
        sizes["login_window_height"] = self.height()
        with open("window_sizes.json", "w") as f:
            json.dump(sizes, f)
        if self.should_quit:
            print("關閉登入視窗，終止應用程式")
            self.app.quit()
        else:
            print("關閉登入視窗，進入主視窗")
        event.accept()