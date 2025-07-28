from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QLabel, QSplitter, QFrame, QMessageBox, QPushButton, QInputDialog, QMenu, QDialog, QDialogButtonBox, QRadioButton, QLineEdit, QFormLayout, QSpinBox, QComboBox, QFileDialog, QScrollArea, QWidget, QGridLayout, QCheckBox, QStackedLayout, QComboBox as QComboBoxWidget
from PyQt5.QtGui import QFont, QPixmap, QPainter
from PyQt5.QtCore import Qt, QPoint, QSize, QRect
import json
import os
import sqlite3
from datetime import datetime
import requests

API_BASE_URL = "http://127.0.0.1:5000"
from PyQt5.QtGui import QPixmap
from io import BytesIO

# ...existing code...

class DamageStatusDialog(QDialog):
    def __init__(self, current_status, parent=None):
        super().__init__(parent)
        self.setWindowTitle("更改損壞情況")
        self.selected_status = current_status
        layout = QVBoxLayout(self)
        self.radio_light = QRadioButton("輕")
        self.radio_medium = QRadioButton("中")
        self.radio_heavy = QRadioButton("重")
        layout.addWidget(self.radio_light)
        layout.addWidget(self.radio_medium)
        layout.addWidget(self.radio_heavy)
        if current_status == "輕":
            self.radio_light.setChecked(True)
        elif current_status == "中":
            self.radio_medium.setChecked(True)
        elif current_status == "重":
            self.radio_heavy.setChecked(True)
        else:
            self.radio_light.setChecked(True)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    def get_status(self):
        if self.radio_light.isChecked():
            return "輕"
        elif self.radio_medium.isChecked():
            return "中"
        elif self.radio_heavy.isChecked():
            return "重"
        return "輕"

class RobotDetailEditDialog(QDialog):
    def __init__(self, name, repair_count, damage_status, parent=None):
        super().__init__(parent)
        self.setWindowTitle("更改詳細資訊")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)
        font_css = "font-size: 20px;"
        self.name_edit = QLineEdit(name)
        self.name_edit.setStyleSheet(font_css)
        # 修正 None 或負數問題
        if repair_count is None or not isinstance(repair_count, int) or repair_count < 0:
            repair_count = 0
        self.repair_spin = QSpinBox()
        self.repair_spin.setMinimum(0)
        self.repair_spin.setMaximum(999)
        self.repair_spin.setValue(repair_count)
        self.repair_spin.setStyleSheet("font-size: 20px;")
        self.repair_spin.setFixedHeight(40)
        self.damage_combo = QComboBox()
        self.damage_combo.addItems(["無", "輕", "中", "重"])
        self.damage_combo.setStyleSheet(font_css)
        idx = self.damage_combo.findText(damage_status)
        if idx >= 0:
            self.damage_combo.setCurrentIndex(idx)
        layout.addRow("名稱：", self.name_edit)
        layout.addRow("維修次數：", self.repair_spin)
        layout.addRow("損壞狀況：", self.damage_combo)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.setStyleSheet("font-size: 18px; min-height: 36px;")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    def get_values(self):
        return self.name_edit.text().strip(), self.repair_spin.value(), self.damage_combo.currentText()

default_repair_count = 0

class ImagePreviewDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("圖片預覽")
        self._pixmap = pixmap
        self._scale = 1.0
        self._offset = QPoint(0, 0)
        self._dragging = False
        self._drag_start = None
        self._offset_start = None
        layout = QVBoxLayout(self)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.reset_btn = QPushButton("恢復原樣", self)
        self.reset_btn.clicked.connect(self.reset_view)
        btn_layout.addWidget(self.reset_btn)
        layout.addLayout(btn_layout)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setScaledContents(False)
        layout.addWidget(self.label, alignment=Qt.AlignCenter)
        self.setMinimumSize(400, 400)
        self.resize(900, 900)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.setWindowState(Qt.WindowNoState)
        self._fit_to_window()
        # 將拖曳事件綁定到 label
        self.label.mousePressEvent = self.label_mousePressEvent
        self.label.mouseMoveEvent = self.label_mouseMoveEvent
        self.label.mouseReleaseEvent = self.label_mouseReleaseEvent

    def _fit_to_window(self):
        # 根據圖片比例自動判斷，寬圖寬度貼合，高圖高度貼合
        area = self.label.size() if self.label.size().width() > 0 else QSize(900, 900)
        pw, ph = self._pixmap.width(), self._pixmap.height()
        lw, lh = area.width(), area.height()
        scale_w = lw / pw
        scale_h = lh / ph
        self._scale = min(scale_w, scale_h)
        self._offset = QPoint(0, 0)
        self.set_pixmap()

    def reset_view(self):
        self._fit_to_window()

    def set_pixmap(self):
        width = int(self._pixmap.width() * self._scale)
        height = int(self._pixmap.height() * self._scale)
        self.label.resize(self.width(), self.height() - 50)  # 50 為按鈕區高度預留
        scaled = self._pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pixmap = QPixmap(self.label.size())
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        x = (self.label.width() - width) // 2 + self._offset.x()
        y = (self.label.height() - height) // 2 + self._offset.y()
        painter.drawPixmap(x, y, scaled)
        painter.end()
        self.label.setPixmap(pixmap)

    def resizeEvent(self, event):
        self._fit_to_window()
        super().resizeEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self._scale *= 1.1
        else:
            self._scale /= 1.1
        self.set_pixmap()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Plus, Qt.Key_Equal):
            self._scale *= 1.1
            self.set_pixmap()
        elif event.key() == Qt.Key_Minus:
            self._scale /= 1.1
            self.set_pixmap()
        super().keyPressEvent(event)

    def label_mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            width = int(self._pixmap.width() * self._scale)
            height = int(self._pixmap.height() * self._scale)
            x = (self.label.width() - width) // 2 + self._offset.x()
            y = (self.label.height() - height) // 2 + self._offset.y()
            img_rect = QRect(x, y, width, height)
            if img_rect.contains(event.pos()):
                self._dragging = True
                self._drag_start = event.pos()
                self._offset_start = QPoint(self._offset)

    def label_mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.LeftButton:
            delta = event.pos() - self._drag_start
            self._offset = self._offset_start + delta
            self.set_pixmap()

    def label_mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 只有點擊在圖片內容上才允許拖曳
            width = int(self._pixmap.width() * self._scale)
            height = int(self._pixmap.height() * self._scale)
            x = (self.label.width() - width) // 2 + self._offset.x()
            y = (self.label.height() - height) // 2 + self._offset.y()
            img_rect = QRect(x, y, width, height)
            if img_rect.contains(event.pos()):
                self._dragging = True
                self._drag_start = event.pos()
                self._offset_start = QPoint(self._offset)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.LeftButton:
            delta = event.pos() - self._drag_start
            self._offset = self._offset_start + delta
            self.set_pixmap()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
        super().mouseReleaseEvent(event)

class ImageDeleteDialog(QDialog):
    def __init__(self, images, parent=None):
        super().__init__(parent)
        self.setWindowTitle("刪除圖片")
        self.selected_ids = set()
        layout = QVBoxLayout(self)
        scroll = QScrollArea(self)
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        self.checkboxes = []
        for idx, img in enumerate(images):
            img_label = QLabel()
            try:
                img_resp = requests.get(f"{API_BASE_URL}{img['image_path']}")
                if img_resp.status_code == 200:
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_resp.content)
                    img_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio))
            except Exception:
                pass
            cb = QCheckBox()
            cb.stateChanged.connect(lambda state, img_id=img['id']: self.toggle_select(img_id, state))
            grid.addWidget(img_label, idx // 4, (idx % 4) * 2)
            grid.addWidget(cb, idx // 4, (idx % 4) * 2 + 1)
            self.checkboxes.append(cb)
        scroll.setWidget(grid_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("刪除")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self.setMinimumSize(500, 400)
    def toggle_select(self, img_id, state):
        if state:
            self.selected_ids.add(img_id)
        else:
            self.selected_ids.discard(img_id)
    def get_selected_ids(self):
        return list(self.selected_ids)

class RobotStatusWindow(QMainWindow):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("機器人狀態檢視")
        self._first_restore = True
        self._last_manual_size = None
        self._maximized_size = None
        self._restored_once = False
        self.robot_image = QLabel(self)  # 必須最早建立
        self.load_window_size()
        self.showMaximized()  # 預設最大化

        font = QFont("Arial", 12)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 使用 QSplitter 實現可調整大小的面板
        splitter = QSplitter(Qt.Horizontal)

        # 左側面板：機器人選擇（佔1/5），加框線
        self.left_panel = QFrame()
        self.left_panel.setFrameShape(QFrame.Box)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setAlignment(Qt.AlignTop)

        # 標題與按鈕
        title_layout = QHBoxLayout()
        self.robot_list_label = QLabel("可用機器人：", self)
        self.robot_list_label.setFont(font)
        title_layout.addWidget(self.robot_list_label)

        self.add_btn = QPushButton("新增", self)
        self.add_btn.setFixedWidth(50)
        self.add_btn.clicked.connect(self.add_robot)
        title_layout.addWidget(self.add_btn)

        self.del_btn = QPushButton("刪除", self)
        self.del_btn.setFixedWidth(50)
        self.del_btn.clicked.connect(self.delete_robot)
        title_layout.addWidget(self.del_btn)
        title_layout.addStretch()
        left_layout.addLayout(title_layout)

        self.robot_list = QListWidget(self)
        self.robot_list.setFont(font)
        self.robot_list.currentItemChanged.connect(self.update_robot_details)
        self.robot_list.itemDoubleClicked.connect(self.show_robot_details)
        self.robot_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.robot_list.customContextMenuRequested.connect(self.show_robot_context_menu)
        left_layout.addWidget(self.robot_list)
        splitter.addWidget(self.left_panel)

        # 中間面板：機器人狀態（3/5，帶框線）
        self.center_panel = QFrame()
        self.center_panel.setFrameShape(QFrame.Box)
        center_layout = QVBoxLayout(self.center_panel)
        center_layout.setContentsMargins(5, 5, 5, 5)
        center_layout.setSpacing(5)

        # ====== 新增：右上角顯示模式選擇 ======
        top_row = QHBoxLayout()
        self.mode_combo = QComboBoxWidget()
        self.mode_combo.addItems(["單一畫面", "雙畫面"])
        self.mode_combo.setFixedWidth(100)
        self.mode_combo.setCurrentIndex(0)
        top_row.addStretch()
        top_row.addWidget(self.mode_combo)
        center_layout.addLayout(top_row)

        # ====== 新增：上方切換按鈕區 ======
        btn_row = QHBoxLayout()
        self.camera_btn = QPushButton("camera")
        self.lidar_btn = QPushButton("lidar")
        self.camera_btn.setCheckable(True)
        self.lidar_btn.setCheckable(True)
        self.camera_btn.setChecked(True)
        self.lidar_btn.setChecked(False)
        btn_row.addWidget(self.camera_btn)
        btn_row.addWidget(self.lidar_btn)
        btn_row.addStretch()
        center_layout.addLayout(btn_row)

        # ====== 新增：內容區 ======
        self.center_content = QWidget()
        self.center_content_layout = QVBoxLayout(self.center_content)
        self.center_content_layout.setContentsMargins(0, 0, 0, 0)
        self.center_content_layout.setSpacing(5)
        # camera畫面
        self.camera_view = QLabel("這裡是camera畫面示意", self)
        self.camera_view.setAlignment(Qt.AlignCenter)
        self.camera_view.setStyleSheet("font-size: 22px; color: #2a5d9f; border: 1px solid #aaa; background: #eaf3ff;")
        # lidar畫面
        self.lidar_view = QLabel("這裡是LIDAR畫面示意", self)
        self.lidar_view.setAlignment(Qt.AlignCenter)
        self.lidar_view.setStyleSheet("font-size: 22px; color: #9f2a2a; border: 1px solid #aaa; background: #fff3ea;")
        self.center_content_layout.addWidget(self.camera_view)
        self.center_content_layout.addWidget(self.lidar_view)
        center_layout.addWidget(self.center_content, stretch=1)
        splitter.addWidget(self.center_panel)

        # 右側面板：機器人詳細資訊（1/5，帶框線）
        self.right_panel = QFrame()
        self.right_panel.setFrameShape(QFrame.Box)
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setAlignment(Qt.AlignTop)
        self.details_label = QLabel("機器人詳細資訊：", self)
        self.details_label.setFont(font)
        right_layout.addWidget(self.details_label)

        self.info_display = QLabel(self)
        self.info_display.setFont(font)
        self.info_display.setWordWrap(True)
        right_layout.addWidget(self.info_display)
        right_layout.addStretch()

        # 圖片顯示區
        self.show_img_btn = QPushButton("顯示圖片", self)
        self.show_img_btn.setCheckable(True)
        self.show_img_btn.setChecked(False)
        self.show_img_btn.clicked.connect(self.toggle_image_area)
        right_layout.addWidget(self.show_img_btn)

        # 圖片區塊
        self.images_area = QWidget(self)
        images_area_layout = QVBoxLayout(self.images_area)
        btn_row = QHBoxLayout()
        self.add_img_btn = QPushButton("加入圖片", self)
        self.add_img_btn.clicked.connect(self.add_robot_image)
        btn_row.addWidget(self.add_img_btn)
        self.delete_imgs_btn = QPushButton("刪除圖片", self)
        self.delete_imgs_btn.clicked.connect(self.delete_robot_images_dialog)
        btn_row.addWidget(self.delete_imgs_btn)
        btn_row.addStretch()
        images_area_layout.addLayout(btn_row)
        self.images_layout = QVBoxLayout()  # 縮圖直向排列
        images_area_layout.addLayout(self.images_layout)
        self.images_area.setVisible(True)
        right_layout.addWidget(self.images_area)  # <--- 確保加到 right_layout
        splitter.addWidget(self.right_panel)

        # 設定初始分割比例（左:中:右 ≈ 1:3:1）
        splitter.setSizes([self.width() // 5, self.width() * 3 // 5, self.width() // 5])
        main_layout.addWidget(splitter)

        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 初始化資料庫並載入機器人清單
        self.init_db()
        self.load_robots()
        self.robot_image.mousePressEvent = self.show_image_preview

        # 切換按鈕事件
        self.camera_btn.clicked.connect(lambda: self.switch_center_view(0))
        self.lidar_btn.clicked.connect(lambda: self.switch_center_view(1))
        self.mode_combo.currentIndexChanged.connect(self.update_center_content_mode)
        self.update_center_content_mode()

    # 新增機器人
    def add_robot(self):
        name, ok = QInputDialog.getText(self, "新增機器人", "請輸入機器人名稱：")
        if ok and name.strip():
            import uuid
            robot_id = f"robot{uuid.uuid4().hex[:12]}"
            add_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            try:
                resp = requests.post(f'{API_BASE_URL}/api/add_robot', json={
                    "robot_id": robot_id,
                    "name": name.strip(),
                    "add_date": add_date
                })
                data = resp.json()
                if data.get("success"):
                    self.load_robots(select_name=name.strip())
                else:
                    QMessageBox.warning(self, "錯誤", f"新增機器人失敗：{data.get('msg', '未知錯誤')}")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"API 連線失敗：{str(e)}")

    # 刪除機器人
    def delete_robot(self):
        current = self.robot_list.currentItem()
        if not current:
            QMessageBox.warning(self, "提示", "請先選擇要刪除的機器人")
            return
        name = current.text().strip()
        robot_id = self.get_robot_id_by_name(name)
        if not robot_id:
            QMessageBox.warning(self, "錯誤", "找不到該機器人資料")
            return
        try:
            resp = requests.post(f'{API_BASE_URL}/api/delete_robot', json={"robot_id": robot_id})
            data = resp.json()
            if data.get("success"):
                self.load_robots()
                self.info_display.setText("")
                self.robot_image.clear()
            else:
                QMessageBox.warning(self, "錯誤", f"刪除機器人失敗：{data.get('msg', '未知錯誤')}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"API 連線失敗：{str(e)}")

    # 雙擊顯示詳細資訊
    def show_robot_details(self, item):
        self.update_robot_details(item, None)

    # 右鍵選單：更改名稱
    def show_robot_context_menu(self, pos):
        item = self.robot_list.itemAt(pos)
        if item:
            menu = QMenu(self)
            rename_action = menu.addAction("重新命名")
            detail_action = menu.addAction("更改詳細資訊")
            action = menu.exec_(self.robot_list.mapToGlobal(pos))
            if action == rename_action:
                self.rename_robot(item)
            elif action == detail_action:
                self.edit_robot_details(item)

    def rename_robot(self, item):
        name = item.text().strip()
        robot_id = self.get_robot_id_by_name(name)
        if not robot_id:
            QMessageBox.warning(self, "錯誤", "找不到該機器人資料")
            return
        old_name = name
        new_name, ok = QInputDialog.getText(self, "更改名稱", "請輸入新名稱：", text=old_name)
        if ok and new_name.strip() and new_name != old_name:
            try:
                resp = requests.post(f'{API_BASE_URL}/api/update_robot', json={
                    "robot_id": robot_id,
                    "name": new_name.strip()
                })
                data = resp.json()
                if data.get("success"):
                    self.load_robots(select_name=new_name.strip())
                else:
                    QMessageBox.warning(self, "錯誤", f"更改名稱失敗：{data.get('msg', '未知錯誤')}")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"API 連線失敗：{str(e)}")

    def edit_robot_details(self, item):
        name = item.text().strip()
        robot_id = self.get_robot_id_by_name(name)
        if not robot_id:
            QMessageBox.warning(self, "錯誤", "找不到該機器人資料")
            return
        try:
            resp = requests.get(f'{API_BASE_URL}/api/robot/{robot_id}')
            data = resp.json()
            if data.get("success"):
                robot_data = data.get('robot', {})
                name, repair_count, damage_status = robot_data.get('name', ''), robot_data.get('repair_count', 0), robot_data.get('damage_status', '無損壞')
                if repair_count is None or not isinstance(repair_count, int) or repair_count < 0:
                    repair_count = 0
            else:
                QMessageBox.warning(self, "錯誤", f"獲取機器人詳細資訊失敗：{data.get('msg', '未知錯誤')}")
                return
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"API 連線失敗：{str(e)}")
            return

        dialog = RobotDetailEditDialog(name, repair_count, damage_status, self)
        if dialog.exec_() == QDialog.Accepted:
            new_name, new_repair, new_damage = dialog.get_values()
            try:
                resp = requests.post(f'{API_BASE_URL}/api/update_robot', json={
                    "robot_id": robot_id,
                    "name": new_name,
                    "repair_count": new_repair,
                    "damage_status": new_damage
                })
                data = resp.json()
                if data.get("success"):
                    self.load_robots(select_name=new_name)
                else:
                    QMessageBox.warning(self, "錯誤", f"更改詳細資訊失敗：{data.get('msg', '未知錯誤')}")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"API 連線失敗：{str(e)}")

    def get_robot_id_by_name(self, name):
        try:
            resp = requests.get(f'{API_BASE_URL}/api/robots')
            data = resp.json()
            robots = data.get('robots', [])
            for robot in robots:
                if robot['name'] == name:
                    return robot['robot_id']
        except Exception:
            pass
        return None

    def init_db(self):
        """初始化機器人資料庫"""
        try:
            conn = sqlite3.connect("robots.db")
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS robots (
                    robot_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    add_date TEXT NOT NULL,
                    repair_count INTEGER DEFAULT 0,
                    task_completion_rate REAL DEFAULT 0.0,
                    damage_status TEXT DEFAULT '無損壞',
                    battery_level INTEGER DEFAULT 100,
                    image_path TEXT
                )
            ''')
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"資料庫初始化失敗：{str(e)}")
            QMessageBox.critical(self, "錯誤", f"無法初始化機器人資料庫：{str(e)}")

    def load_robots(self, select_name=None):
        """從 API 載入機器人清單"""
        try:
            resp = requests.get(f'{API_BASE_URL}/api/robots')
            data = resp.json()
            robots = data.get('robots', [])
            self.robot_list.clear()
            for robot in robots:
                self.robot_list.addItem(robot['name'])
            # 自動選取指定名稱
            if select_name:
                items = self.robot_list.findItems(select_name, Qt.MatchExactly)
                if items:
                    self.robot_list.setCurrentItem(items[0])
        except Exception as e:
            print(f"載入機器人清單失敗：{str(e)}")
            QMessageBox.critical(self, "錯誤", f"無法載入機器人清單（API）：{str(e)}")

    def update_robot_details(self, current, previous):
        """從 API 更新右側詳細資訊，圖片用 HTTP 下載顯示，並顯示所有縮圖"""
        if not current:
            self.robot_image.clear()
            self.info_display.setText("請選擇一個機器人")
            self.clear_images_area()
            return
        name = current.text().strip()
        try:
            resp = requests.get(f'{API_BASE_URL}/api/robots')
            data = resp.json()
            robots = data.get('robots', [])
            robot = next((r for r in robots if r['name'] == name), None)
            if robot:
                status_map = {"無": "無損壞", "輕": "輕度損壞", "中": "中度損壞", "重": "重度損壞"}
                show_status = status_map.get(robot['damage_status'], robot['damage_status'])
                self.info_display.setText(
                    f"名稱: {robot['name']}\n"
                    f"加入系統時間: {robot['add_date']}\n"
                    f"維修次數: {robot['repair_count']}\n"
                    f"任務完成率: {robot['task_completion_rate']}%\n"
                    f"損壞情況: {show_status}\n"
                    f"電量: {robot['battery_level']}%"
                )
                # 主要大圖
                self.robot_image.clear()
                # 顯示該機器人所有縮圖
                self.show_all_robot_images(robot['robot_id'])
            else:
                self.info_display.setText("無法取得機器人資訊")
                self.robot_image.clear()
                self.clear_images_area()
        except Exception as e:
            print(f"載入機器人詳細資訊失敗：{str(e)}")
            self.info_display.setText("無法取得機器人資訊")
            self.robot_image.clear()
            self.clear_images_area()

    def show_all_robot_images(self, robot_id):
        self.clear_images_area()
        try:
            resp = requests.get(f'{API_BASE_URL}/api/robot_images/{robot_id}')
            data = resp.json()
            images = data.get('images', [])
            for img in images:
                img_label = QLabel()
                img_label.setFixedSize(120, 120)
                img_label.setScaledContents(True)
                try:
                    img_resp = requests.get(f"{API_BASE_URL}{img['image_path']}")
                    if img_resp.status_code == 200:
                        pixmap = QPixmap()
                        pixmap.loadFromData(img_resp.content)
                        img_label.setPixmap(pixmap.scaled(120, 120, Qt.KeepAspectRatio))
                        img_label._full_pixmap = pixmap  # 保存原始 QPixmap，避免被回收
                        def make_mouse_press_event(label, img_id):
                            def mousePressEvent(event):
                                if event.button() == Qt.LeftButton:
                                    self.show_image_preview_pixmap(label._full_pixmap)
                                elif event.button() == Qt.RightButton:
                                    menu = QMenu(label)
                                    del_action = menu.addAction("刪除圖片")
                                    action = menu.exec_(label.mapToGlobal(event.pos()))
                                    if action == del_action:
                                        self.confirm_delete_single_image(img_id)
                            return mousePressEvent
                        img_label.mousePressEvent = make_mouse_press_event(img_label, img['id'])
                except Exception:
                    pass
                self.images_layout.addWidget(img_label)
        except Exception as e:
            print(f"載入所有機器人圖片失敗：{str(e)}")

    def _make_delete_img_handler(self, img_id):
        return lambda pos, img_id=img_id: self.confirm_delete_single_image(img_id)

    def clear_images_area(self):
        while self.images_layout.count():
            item = self.images_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def show_image_preview_pixmap(self, pixmap):
        dialog = ImagePreviewDialog(pixmap, self)
        dialog.exec_()

    def toggle_image_area(self):
        self.images_area.setVisible(self.show_img_btn.isChecked())
        if self.show_img_btn.isChecked():
            self.show_img_btn.setText("隱藏圖片")
        else:
            self.show_img_btn.setText("顯示圖片")

    def add_robot_image(self):
        current = self.robot_list.currentItem()
        if not current:
            QMessageBox.warning(self, "提示", "請先選擇一個機器人")
            return
        name = current.text().strip()
        robot_id = self.get_robot_id_by_name(name)
        if not robot_id:
            QMessageBox.warning(self, "錯誤", "找不到該機器人資料")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "選擇圖片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
                    data = {'robot_id': robot_id}
                    resp = requests.post(f'{API_BASE_URL}/api/upload_robot_image', files=files, data=data)
                    result = resp.json()
                    if result.get('success'):
                        self.update_robot_details(current, None)
                    else:
                        QMessageBox.warning(self, "錯誤", f"圖片上傳失敗：{result.get('msg', '未知錯誤')}")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"API 連線失敗：{str(e)}")

    def delete_robot_image_menu(self, pos):
        if not self.robot_image.pixmap():
            return
        menu = QMenu(self)
        del_action = menu.addAction("刪除圖片")
        action = menu.exec_(self.robot_image.mapToGlobal(pos))
        if action == del_action:
            self.delete_robot_image()

    def delete_robot_image(self):
        current = self.robot_list.currentItem()
        if not current:
            return
        name = current.text().strip()
        robot_id = self.get_robot_id_by_name(name)
        if not robot_id:
            return
        try:
            resp = requests.post(f'{API_BASE_URL}/api/update_robot', json={
                "robot_id": robot_id,
                "image_path": None
            })
            data = resp.json()
            if data.get("success"):
                self.update_robot_details(current, None)
            else:
                QMessageBox.warning(self, "錯誤", f"刪除圖片失敗：{data.get('msg', '未知錯誤')}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"API 連線失敗：{str(e)}")

    def delete_robot_images_dialog(self):
        current = self.robot_list.currentItem()
        if not current:
            QMessageBox.warning(self, "提示", "請先選擇一個機器人")
            return
        name = current.text().strip()
        robot_id = self.get_robot_id_by_name(name)
        if not robot_id:
            QMessageBox.warning(self, "錯誤", "找不到該機器人資料")
            return
        try:
            resp = requests.get(f'{API_BASE_URL}/api/robot_images/{robot_id}')
            data = resp.json()
            images = data.get('images', [])
            if not images:
                QMessageBox.information(self, "提示", "沒有圖片可刪除")
                return
            dialog = ImageDeleteDialog(images, self)
            if dialog.exec_() == QDialog.Accepted:
                ids = dialog.get_selected_ids()
                if ids:
                    del_resp = requests.post(f'{API_BASE_URL}/api/delete_robot_images', json={"ids": ids})
                    del_data = del_resp.json()
                    if del_data.get('success'):
                        self.update_robot_details(current, None)
                    else:
                        QMessageBox.warning(self, "錯誤", f"刪除圖片失敗：{del_data.get('msg', '未知錯誤')}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"API 連線失敗：{str(e)}")

    def confirm_delete_single_image(self, img_id):
        reply = QMessageBox.question(self, "確認刪除", "確定要刪除此圖片嗎？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                del_resp = requests.post(f'{API_BASE_URL}/api/delete_robot_images', json={"ids": [img_id]})
                del_data = del_resp.json()
                if del_data.get('success'):
                    current = self.robot_list.currentItem()
                    self.update_robot_details(current, None)
                else:
                    QMessageBox.warning(self, "錯誤", f"刪除圖片失敗：{del_data.get('msg', '未知錯誤')}")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"API 連線失敗：{str(e)}")

    def changeEvent(self, event):
        # 監聽視窗狀態改變
        if event.type() == event.WindowStateChange:
            if self.isMaximized():
                self._maximized_size = (self.width(), self.height())
                self._first_restore = True
                self._restored_once = False
            elif not self.isMaximized() and self._first_restore and not self._restored_once:
                # 第一次從最大化還原
                if self._maximized_size:
                    width = int(self._maximized_size[0] * 0.75)
                    height = int(self._maximized_size[1] * 0.75)
                    self.resize(width, height)
                self._first_restore = False
                self._restored_once = True
        super().changeEvent(event)

    def resizeEvent(self, event):
        # 記錄手動調整的大小
        if not self.isMaximized():
            self._last_manual_size = (self.width(), self.height())
        super().resizeEvent(event)

    def show_image_preview(self, event):
        if self.robot_image.pixmap():
            dialog = ImagePreviewDialog(self.robot_image.pixmap(), self)
            dialog.exec_()

    def switch_center_view(self, idx):
        self.camera_btn.setChecked(idx == 0)
        self.lidar_btn.setChecked(idx == 1)
        self._current_view_idx = idx
        self.update_center_content_mode()

    def update_center_content_mode(self):
        mode = self.mode_combo.currentIndex()
        # 0: 單一畫面，1: 雙畫面
        if mode == 0:
            # 只顯示一個畫面，填滿
            if getattr(self, '_current_view_idx', 0) == 0:
                self.camera_view.setVisible(True)
                self.lidar_view.setVisible(False)
            else:
                self.camera_view.setVisible(False)
                self.lidar_view.setVisible(True)
            self.center_content_layout.setStretch(0, 1)
            self.center_content_layout.setStretch(1, 0)
        else:
            # 雙畫面，上下各半
            self.camera_view.setVisible(True)
            self.lidar_view.setVisible(True)
            self.center_content_layout.setStretch(0, 1)
            self.center_content_layout.setStretch(1, 1)

    def load_window_size(self):
        """載入視窗大小"""
        try:
            with open("window_sizes.json", "r") as f:
                sizes = json.load(f)
                width = sizes.get("robot_status_window_width", 800)
                height = sizes.get("robot_status_window_height", 600)
                self.resize(width, height)
        except (FileNotFoundError, json.JSONDecodeError):
            self.resize(800, 600)

    def closeEvent(self, event):
        """儲存視窗大小"""
        sizes = {}
        try:
            with open("window_sizes.json", "r") as f:
                sizes = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        # 儲存最後一次手動調整的大小
        if self._last_manual_size:
            sizes["robot_status_window_width"] = self._last_manual_size[0]
            sizes["robot_status_window_height"] = self._last_manual_size[1]
        else:
            sizes["robot_status_window_width"] = self.width()
            sizes["robot_status_window_height"] = self.height()
        with open("window_sizes.json", "w") as f:
            json.dump(sizes, f)
        event.accept()

# ...existing code...
