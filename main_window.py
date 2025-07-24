from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QDialog, QFormLayout, QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem, QScrollArea, QStackedWidget, QRadioButton, QHBoxLayout, QHeaderView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from user_manager import UserManager
import json
import os
from robot_status_window import RobotStatusWindow
import requests
import csv

class UserManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("帳號管理")
        try:
            self.load_window_size()
            self.user_manager = UserManager()
            font = QFont("Arial", 12)

            main_layout = QVBoxLayout(self)
            
            self.table_label = QLabel("目前帳號（按身分分類，雙擊名稱查看詳細資訊）:", self)
            self.table_label.setFont(font)
            main_layout.addWidget(self.table_label)

            self.table = QTableWidget(self)
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["管理員", "操作員", "維修員"])
            self.table.setEditTriggers(QTableWidget.NoEditTriggers)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.table.setMinimumHeight(150)
            self.table.cellDoubleClicked.connect(self.show_user_details)
            self.update_table()

            scroll_area = QScrollArea()
            scroll_area.setWidget(self.table)
            scroll_area.setWidgetResizable(True)
            main_layout.addWidget(scroll_area)

            button_layout = QHBoxLayout()
            self.add_button = QPushButton("新增帳號", self)
            self.add_button.setFont(font)
            self.add_button.clicked.connect(lambda: self.stack.setCurrentIndex(1))
            self.delete_button = QPushButton("刪除帳號", self)
            self.delete_button.setFont(font)
            self.delete_button.clicked.connect(lambda: self.stack.setCurrentIndex(2))
            self.update_button = QPushButton("修改帳號", self)
            self.update_button.setFont(font)
            self.update_button.clicked.connect(lambda: self.stack.setCurrentIndex(3))
            self.export_button = QPushButton("匯出帳號", self)
            self.export_button.setFont(font)
            self.export_button.clicked.connect(self.export_users)
            button_layout.addWidget(self.add_button)
            button_layout.addWidget(self.delete_button)
            button_layout.addWidget(self.update_button)
            button_layout.addWidget(self.export_button)
            main_layout.addLayout(button_layout)

            self.stack = QStackedWidget(self)
            main_layout.addWidget(self.stack)

            empty_widget = QWidget()
            self.stack.addWidget(empty_widget)

            add_widget = QWidget()
            add_layout = QFormLayout(add_widget)
            self.add_display_name = QLineEdit()
            self.add_display_name.setPlaceholderText("使用者名稱")
            self.add_username = QLineEdit()
            self.add_username.setPlaceholderText("帳號")
            self.add_password = QLineEdit()
            self.add_password.setPlaceholderText("密碼")
            self.add_role_group = QHBoxLayout()
            self.add_role_admin = QRadioButton("管理員")
            self.add_role_operator = QRadioButton("操作員")
            self.add_role_technician = QRadioButton("維修員")
            self.add_role_group.addWidget(self.add_role_admin)
            self.add_role_group.addWidget(self.add_role_operator)
            self.add_role_group.addWidget(self.add_role_technician)
            self.add_submit = QPushButton("提交")
            self.add_submit.clicked.connect(self.add_user)
            add_layout.addRow("使用者名稱:", self.add_display_name)
            add_layout.addRow("帳號:", self.add_username)
            add_layout.addRow("密碼:", self.add_password)
            add_layout.addRow("身分:", self.add_role_group)
            add_layout.addRow(self.add_submit)
            self.stack.addWidget(add_widget)

            delete_widget = QWidget()
            delete_layout = QFormLayout(delete_widget)
            self.delete_username = QLineEdit()
            self.delete_username.setPlaceholderText("要刪除的帳號")
            self.delete_submit = QPushButton("提交")
            self.delete_submit.clicked.connect(self.delete_user)
            delete_layout.addRow("帳號:", self.delete_username)
            delete_layout.addRow(self.delete_submit)
            self.stack.addWidget(delete_widget)

            update_widget = QWidget()
            update_layout = QFormLayout(update_widget)
            self.update_username = QLineEdit()
            self.update_username.setPlaceholderText("現有帳號")
            self.update_display_name = QLineEdit()
            self.update_display_name.setPlaceholderText("新使用者名稱（選填）")
            self.update_new_username = QLineEdit()
            self.update_new_username.setPlaceholderText("新帳號（選填）")
            self.update_new_password = QLineEdit()
            self.update_new_password.setPlaceholderText("新密碼（選填）")
            self.update_submit = QPushButton("提交")
            self.update_submit.clicked.connect(self.update_user)
            update_layout.addRow("現有帳號:", self.update_username)
            update_layout.addRow("新使用者名稱:", self.update_display_name)
            update_layout.addRow("新帳號:", self.update_new_username)
            update_layout.addRow("新密碼:", self.update_new_password)
            update_layout.addRow(self.update_submit)
            self.stack.addWidget(update_widget)

            main_layout.setSpacing(15)
            main_layout.setContentsMargins(20, 20, 20, 20)
            print("UserManagementDialog 初始化成功")
        except Exception as e:
            print(f"UserManagementDialog 初始化失敗：{str(e)}")
            QMessageBox.critical(self, "錯誤", f"無法初始化帳號管理介面：{str(e)}")
            raise

    def update_table(self):
        try:
            resp = requests.get('http://127.0.0.1:5000/api/users')
            data = resp.json()
            users = data.get('users', [])
            admins = [(u['display_name'], u['username']) for u in users if u['role'] == 'manager']
            operators = [(u['display_name'], u['username']) for u in users if u['role'] == 'operator']
            technicians = [(u['display_name'], u['username']) for u in users if u['role'] == 'technician']
            max_rows = max(len(admins), len(operators), len(technicians))
            self.table.setRowCount(max_rows)
            for row in range(max_rows):
                admin_item = QTableWidgetItem(admins[row][0] if row < len(admins) else "")
                admin_item.setData(Qt.UserRole, admins[row][1] if row < len(admins) else "")
                operator_item = QTableWidgetItem(operators[row][0] if row < len(operators) else "")
                operator_item.setData(Qt.UserRole, operators[row][1] if row < len(operators) else "")
                technician_item = QTableWidgetItem(technicians[row][0] if row < len(technicians) else "")
                technician_item.setData(Qt.UserRole, technicians[row][1] if row < len(technicians) else "")
                self.table.setItem(row, 0, admin_item)
                self.table.setItem(row, 1, operator_item)
                self.table.setItem(row, 2, technician_item)
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"無法更新表格（API）：{str(e)}")

    def show_user_details(self, row, column):
        item = self.table.item(row, column)
        if item and item.text():
            username = item.data(Qt.UserRole)
            try:
                resp = requests.get('http://127.0.0.1:5000/api/users')
                data = resp.json()
                users = data.get('users', [])
                user = next((u for u in users if u['username'] == username), None)
                if user:
                    display_name, username, role = user['display_name'], user['username'], user['role']
                    role_display = "管理員" if role == "manager" else "操作員" if role == "operator" else "維修員"
                    QMessageBox.information(self, "帳號詳細資訊",
                                            f"使用者名稱: {display_name}\n帳號: {username}\n身分: {role_display}")
                else:
                    QMessageBox.warning(self, "錯誤", "無法取得帳號資訊")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"查詢帳號資訊失敗：{str(e)}")

    def add_user(self):
        display_name = self.add_display_name.text()
        username = self.add_username.text()
        password = self.add_password.text()
        role = "manager" if self.add_role_admin.isChecked() else \
               "operator" if self.add_role_operator.isChecked() else \
               "technician" if self.add_role_technician.isChecked() else None
        if not (display_name and username and password and role):
            QMessageBox.warning(self, "錯誤", "請填寫所有欄位並選擇身分")
            return
        try:
            resp = requests.post('http://127.0.0.1:5000/api/register', json={
                "display_name": display_name,
                "username": username,
                "password": password,
                "role": role
            })
            data = resp.json()
            if data.get("success"):
                QMessageBox.information(self, "成功", "使用者新增成功")
                self.add_display_name.clear()
                self.add_username.clear()
                self.add_password.clear()
                self.add_role_admin.setChecked(False)
                self.add_role_operator.setChecked(False)
                self.add_role_technician.setChecked(False)
                self.update_table()
                self.stack.setCurrentIndex(0)
            else:
                QMessageBox.warning(self, "錯誤", f"API 註冊失敗：{data.get('msg', '未知錯誤')}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"API 連線失敗：{str(e)}")

    def delete_user(self):
        username = self.delete_username.text()
        try:
            resp = requests.post('http://127.0.0.1:5000/api/delete_user', json={"username": username})
            data = resp.json()
            if data.get("success"):
                QMessageBox.information(self, "成功", "使用者刪除成功")
                self.delete_username.clear()
                self.update_table()
                self.stack.setCurrentIndex(0)
            else:
                QMessageBox.warning(self, "錯誤", f"API 刪除失敗：{data.get('msg', '未知錯誤')}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"API 連線失敗：{str(e)}")

    def update_user(self):
        username = self.update_username.text()
        new_display_name = self.update_display_name.text() or None
        new_username = self.update_new_username.text() or None
        new_password = self.update_new_password.text() or None
        if not username:
            QMessageBox.warning(self, "錯誤", "請輸入現有帳號")
            return
        if not (new_display_name or new_username or new_password):
            QMessageBox.warning(self, "錯誤", "請至少提供一個更新欄位")
            return
        try:
            resp = requests.post('http://127.0.0.1:5000/api/update_user', json={
                "username": username,
                "new_display_name": new_display_name,
                "new_username": new_username,
                "new_password": new_password
            })
            data = resp.json()
            if data.get("success"):
                QMessageBox.information(self, "成功", "使用者更新成功")
                self.update_username.clear()
                self.update_display_name.clear()
                self.update_new_username.clear()
                self.update_new_password.clear()
                self.update_table()
                self.stack.setCurrentIndex(0)
            else:
                QMessageBox.warning(self, "錯誤", f"API 更新失敗：{data.get('msg', '未知錯誤')}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"API 連線失敗：{str(e)}")

    def export_users(self):
        try:
            resp = requests.get('http://127.0.0.1:5000/api/users')
            data = resp.json()
            users = data.get('users', [])
            filename = "users_export.csv"
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Display Name', 'Username', 'Role'])
                for u in users:
                    writer.writerow([u['display_name'], u['username'], u['role']])
            QMessageBox.information(self, "成功", f"帳號已匯出至 {filename}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"匯出失敗：{str(e)}")

    def load_window_size(self):
        try:
            with open("window_sizes.json", "r") as f:
                sizes = json.load(f)
                width = sizes.get("user_dialog_width", 600)
                height = sizes.get("user_dialog_height", 500)
                self.resize(width, height)
        except (FileNotFoundError, json.JSONDecodeError):
            self.resize(600, 500)

    def closeEvent(self, event):
        sizes = {}
        try:
            with open("window_sizes.json", "r") as f:
                sizes = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        sizes["user_dialog_width"] = self.width()
        sizes["user_dialog_height"] = self.height()
        with open("window_sizes.json", "w") as f:
            json.dump(sizes, f)
        event.accept()

class MainWindow(QMainWindow):
    def __init__(self, role, app):
        super().__init__()
        self.role = role
        self.app = app
        self.is_logging_out = False  # 添加登出標誌
        self.setWindowTitle("主畫面")
        self.load_window_size()

        font = QFont("Arial", 12)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.welcome_label = QLabel(f"歡迎使用系統！身分：{'管理員' if role == 'manager' else '操作員' if role == 'operator' else '維修員'}", self)
        self.welcome_label.setFont(font)
        self.welcome_label.setAlignment(Qt.AlignCenter)
        self.welcome_label.setWordWrap(True)
        layout.addWidget(self.welcome_label)

        if self.role in ["manager", "operator"]:
            self.task_button = QPushButton("任務管理", self)
            self.task_button.setFont(font)
            self.task_button.clicked.connect(self.handle_task_management)
            layout.addWidget(self.task_button)

        if self.role in ["manager", "technician"]:
            self.status_button = QPushButton("檢視機器人狀態", self)
            self.status_button.setFont(font)
            self.status_button.clicked.connect(self.handle_status_view)
            layout.addWidget(self.status_button)

        if self.role == "manager":
            self.user_management_button = QPushButton("帳號管理", self)
            self.user_management_button.setFont(font)
            self.user_management_button.clicked.connect(self.handle_user_management)
            layout.addWidget(self.user_management_button)

        self.logout_button = QPushButton("登出", self)
        self.logout_button.setFont(font)
        self.logout_button.clicked.connect(self.handle_logout)
        layout.addWidget(self.logout_button)

        layout.setSpacing(15)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setAlignment(Qt.AlignCenter)

    def handle_task_management(self):
        QMessageBox.information(self, "提示", "任務管理功能尚未實現")

    def handle_status_view(self):
        try:
            self.status_window = RobotStatusWindow(self.app, self)
            self.status_window.show()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"無法開啟機器人狀態檢視介面：{str(e)}")

    def handle_user_management(self):
        try:
            dialog = UserManagementDialog(self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"無法開啟帳號管理介面：{str(e)}")

    def handle_logout(self):
        from login_window import LoginWindow
        print("正在登出...")
        QMessageBox.information(self, "提示", "已登出")
        self.is_logging_out = True  # 設置登出標誌
        self.close()  # 觸發 closeEvent
        try:
            self.login_window = LoginWindow(self.app)
            self.login_window.show()
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            print("已顯示登入視窗")
        except Exception as e:
            print(f"無法顯示登入視窗：{str(e)}")
            QMessageBox.critical(None, "錯誤", f"無法返回登入介面：{str(e)}")

    def load_window_size(self):
        try:
            with open("window_sizes.json", "r") as f:
                sizes = json.load(f)
                width = sizes.get("main_window_width", 800)
                height = sizes.get("main_window_height", 600)
                self.resize(width, height)
        except (FileNotFoundError, json.JSONDecodeError):
            self.resize(800, 600)

    def closeEvent(self, event):
        if self.is_logging_out:
            # 登出時直接關閉，不顯示確認對話框
            sizes = {}
            try:
                with open("window_sizes.json", "r") as f:
                    sizes = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            sizes["main_window_width"] = self.width()
            sizes["main_window_height"] = self.height()
            with open("window_sizes.json", "w") as f:
                json.dump(sizes, f)
            print("關閉主視窗，返回登入畫面")
            event.accept()
        else:
            # 非登出時（例如點擊叉叉），顯示確認對話框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("確認退出")
            msg_box.setText("是否直接關閉程式？")
            yes_button = msg_box.addButton("是", QMessageBox.AcceptRole)
            no_button = msg_box.addButton("否", QMessageBox.RejectRole)
            msg_box.setDefaultButton(no_button)
            msg_box.exec_()

            if msg_box.clickedButton() == yes_button:
                sizes = {}
                try:
                    with open("window_sizes.json", "r") as f:
                        sizes = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    pass
                sizes["main_window_width"] = self.width()
                sizes["main_window_height"] = self.height()
                with open("window_sizes.json", "w") as f:
                    json.dump(sizes, f)
                print("關閉主視窗，終止應用程式")
                self.app.quit()
                event.accept()
            else:
                print("取消關閉主視窗")
                event.ignore()