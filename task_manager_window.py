from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QLabel, QPushButton, QSplitter, QMessageBox, QComboBox, QLineEdit, QDialog, QDialogButtonBox, QProgressBar, QListWidgetItem, QCheckBox, QInputDialog, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QAbstractItemView
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QBrush, QFont
import requests
import threading

API_BASE_URL = "http://127.0.0.1:5000"

# 假資料：任務清單
TASK_LIST = [
    {"task_id": "T001", "description": "A點→B點"},
    {"task_id": "T002", "description": "A點→C點"},
    {"task_id": "T003", "description": "B點→C點"},
]

class TaskManagerWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("任務管理")
        self.resize(1300, 750)

        # 先初始化所有 map 屬性，避免屬性不存在錯誤
        self.robot_status_map = {}  # robot_id: 狀態
        self.robot_task_map = {}    # robot_id: 當前任務
        self.robot_history_map = {} # robot_id: 歷史任務
        self.robot_progress_map = {} # robot_id: 進度
        self.robot_paused_map = {}  # robot_id: 是否暫停
        self.robot_thread_map = {}  # robot_id: 執行緒
        self.robot_cancel_event = {} # robot_id: threading.Event 取消
        self.robot_pause_event = {}  # robot_id: threading.Event 暫停
        self.robot_all_tasks_map = {}  # robot_id: [所有被指派過的任務]
        self.robot_completed_tasks_map = {}  # robot_id: [已完成的任務]
        self.robot_task_queue_map = {}  # robot_id: [任務佇列]
        self.selected_robot = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Horizontal)

        # 左側：機器人清單
        self.robot_list = QListWidget()
        self.robot_list.setFixedWidth(260)
        self.robot_list.itemSelectionChanged.connect(self.update_robot_status)
        splitter.addWidget(self.robot_list)

        # 中間：任務選擇與派發
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setAlignment(Qt.AlignTop)
        label = QLabel("選擇任務（可多選排序）：")
        label.setFont(QFont("Arial", 16))
        center_layout.addWidget(label)
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(3)
        self.task_table.setHorizontalHeaderLabels(["任務名稱", "選取", "順序"])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.task_table.setFont(QFont("Arial", 14))
        self.task_table.setFixedHeight(200)
        self.task_table.setRowCount(len(TASK_LIST))
        self.task_checkboxes = []
        self.task_order = []  # 儲存勾選順序的任務index
        for i, task in enumerate(TASK_LIST):
            name_item = QTableWidgetItem(task["description"])
            name_item.setFont(QFont("Arial", 14))
            self.task_table.setItem(i, 0, name_item)
            cb = QCheckBox()
            cb.setStyleSheet("QCheckBox { margin-left: 10px; }")
            cb.stateChanged.connect(lambda state, idx=i: self.handle_task_checkbox(state, idx))
            self.task_table.setCellWidget(i, 1, cb)
            self.task_checkboxes.append(cb)
            order_item = QTableWidgetItem("")
            order_item.setTextAlignment(Qt.AlignCenter)
            self.task_table.setItem(i, 2, order_item)
        center_layout.addWidget(self.task_table)
        self.custom_task_input = QLineEdit()
        self.custom_task_input.setPlaceholderText("自訂任務（可直接輸入）")
        self.custom_task_input.setFont(QFont("Arial", 14))
        center_layout.addWidget(self.custom_task_input)
        self.assign_btn = QPushButton("派發任務")
        self.assign_btn.setFont(QFont("Arial", 16))
        self.assign_btn.clicked.connect(self.assign_task)
        center_layout.addWidget(self.assign_btn)
        self.batch_checkbox = QCheckBox("批次派發（可多選機器人）")
        self.batch_checkbox.setFont(QFont("Arial", 14))
        self.batch_checkbox.stateChanged.connect(self.toggle_batch_mode)
        center_layout.addWidget(self.batch_checkbox)
        center_layout.addStretch()
        splitter.addWidget(center_widget)

        # 右側：狀態面板
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setAlignment(Qt.AlignTop)
        self.status_panel = QLabel("請選擇機器人")
        self.status_panel.setWordWrap(True)
        right_layout.addWidget(self.status_panel)
        # 新增：目前執行任務名稱
        self.current_task_label = QLabel("")
        self.current_task_label.setWordWrap(True)
        right_layout.addWidget(self.current_task_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)
        # 新增總任務完成度進度條
        self.total_progress_bar = QProgressBar()
        self.total_progress_bar.setValue(0)
        self.total_progress_bar.setVisible(False)
        self.total_progress_bar.setFormat("總任務完成度：%p%")
        right_layout.addWidget(self.total_progress_bar)
        self.cancel_btn = QPushButton("取消任務")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_task)
        right_layout.addWidget(self.cancel_btn)
        self.pause_btn = QPushButton("暫停/繼續")
        self.pause_btn.setVisible(False)
        self.pause_btn.clicked.connect(self.pause_resume_task)
        right_layout.addWidget(self.pause_btn)
        # 新增：待辦任務列表
        right_layout.addWidget(QLabel("待辦任務列表："))
        self.todo_list = QListWidget()
        right_layout.addWidget(self.todo_list)
        right_layout.addWidget(QLabel("任務歷史紀錄："))
        self.history_list = QListWidget()
        right_layout.addWidget(self.history_list)
        splitter.addWidget(right_widget)

        main_layout.addWidget(splitter)

        self.load_robots()

    def load_robots(self):
        try:
            resp = requests.get(f"{API_BASE_URL}/api/robots")
            robots = resp.json().get("robots", [])
            self.robot_list.clear()
            for robot in robots:
                status = robot.get("status", "待機中")  # 假設API有status欄位
                name = robot.get("name", "")
                robot_id = robot.get("robot_id", "")
                display = f"{name}（{status}）"
                item = QListWidgetItem(display)
                # 狀態顏色標示
                if status == "工作中":
                    item.setForeground(QBrush(QColor("orange")))
                elif status == "離線":
                    item.setForeground(QBrush(QColor("gray")))
                else:
                    item.setForeground(QBrush(QColor("green")))
                item.setData(Qt.UserRole, robot_id)
                self.robot_list.addItem(item)
                # 初始化假資料
                self.robot_status_map[robot_id] = status
                self.robot_task_map[robot_id] = None
                self.robot_history_map.setdefault(robot_id, [])
                self.robot_progress_map[robot_id] = 0
                self.robot_paused_map[robot_id] = False
                if robot_id not in self.robot_cancel_event:
                    self.robot_cancel_event[robot_id] = threading.Event()
                if robot_id not in self.robot_pause_event:
                    self.robot_pause_event[robot_id] = threading.Event()
                self.robot_all_tasks_map.setdefault(robot_id, [])
                self.robot_completed_tasks_map.setdefault(robot_id, [])
                self.robot_task_queue_map.setdefault(robot_id, [])
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"無法載入機器人清單：{str(e)}")

    def toggle_batch_mode(self, state):
        if state == Qt.Checked:
            self.robot_list.setSelectionMode(QListWidget.MultiSelection)
        else:
            self.robot_list.setSelectionMode(QListWidget.SingleSelection)
            # 只保留一個選取
            if self.robot_list.selectedItems():
                self.robot_list.setCurrentItem(self.robot_list.selectedItems()[0])
        self.update_robot_status()

    def handle_task_checkbox(self, state, idx):
        if state == Qt.Checked:
            self.task_order.append(idx)
        else:
            if idx in self.task_order:
                self.task_order.remove(idx)
        # 更新順序號顯示
        for i, cb in enumerate(self.task_checkboxes):
            order_item = self.task_table.item(i, 2)
            if i in self.task_order:
                order_item.setText(str(self.task_order.index(i) + 1))
            else:
                order_item.setText("")

    def assign_task(self):
        selected_items = self.robot_list.selectedItems()
        if not selected_items or not selected_items[0]:
            QMessageBox.warning(self, "提示", "請先選擇機器人")
            return
        # 依照勾選順序派發多個任務
        tasks_to_assign = []
        for idx in self.task_order:
            tasks_to_assign.append(TASK_LIST[idx]["description"])
        # 若有自訂任務也加入
        custom_task = self.custom_task_input.text().strip()
        if custom_task:
            tasks_to_assign.append(custom_task)
        if not tasks_to_assign:
            QMessageBox.warning(self, "提示", "請至少選擇一個任務或輸入自訂任務")
            return
        first_robot_id = None
        for item in selected_items:
            robot_id = item.data(Qt.UserRole)
            if first_robot_id is None:
                first_robot_id = robot_id
            for task in tasks_to_assign:
                self.robot_all_tasks_map.setdefault(robot_id, [])
                self.robot_all_tasks_map[robot_id].append(task)
                self.robot_task_queue_map.setdefault(robot_id, [])
                self.robot_task_queue_map[robot_id].append(task)
                self.robot_history_map[robot_id].append(f"指派任務：{task}")
            if not self.robot_task_map[robot_id]:
                self.start_next_task(robot_id)
        QMessageBox.information(self, "派發成功", f"已將任務派發給選中機器人")
        # 自動選中第一台
        if first_robot_id:
            for i in range(self.robot_list.count()):
                item = self.robot_list.item(i)
                if item.data(Qt.UserRole) == first_robot_id:
                    self.robot_list.setCurrentItem(item)
                    break
        self.update_robot_status()
        # 重置勾選與順序
        for cb in self.task_checkboxes:
            cb.setChecked(False)
        self.task_order.clear()
        for i in range(self.task_table.rowCount()):
            self.task_table.item(i, 2).setText("")
        self.custom_task_input.clear()

    def start_next_task(self, robot_id):
        queue = self.robot_task_queue_map.get(robot_id, [])
        # 只要佇列還有任務就繼續執行
        if queue:
            next_task = queue.pop(0)
            self.robot_task_map[robot_id] = next_task
            self.robot_status_map[robot_id] = "工作中"
            self.robot_progress_map[robot_id] = 0
            self.robot_paused_map[robot_id] = False
            self.robot_cancel_event[robot_id].clear()
            self.robot_pause_event[robot_id].clear()
            self.simulate_progress(robot_id)
        else:
            self.robot_task_map[robot_id] = None
            self.robot_status_map[robot_id] = "待機中"
            self.robot_progress_map[robot_id] = 0
            self.robot_paused_map[robot_id] = False
            self.robot_cancel_event[robot_id].clear()
            self.robot_pause_event[robot_id].clear()
            self.update_robot_status()

    def simulate_progress(self, robot_id):
        def run():
            import time
            self.robot_progress_map[robot_id] = 0  # 從0%開始
            while self.robot_progress_map[robot_id] < 100 and self.robot_task_map[robot_id]:
                if self.robot_cancel_event[robot_id].is_set():
                    break
                if self.robot_paused_map[robot_id] or self.robot_pause_event[robot_id].is_set():
                    time.sleep(0.1)
                    continue
                self.robot_progress_map[robot_id] += 1
                if self.robot_progress_map[robot_id] > 100:
                    self.robot_progress_map[robot_id] = 100
                QTimer.singleShot(0, self.update_robot_status)
                time.sleep(0.15)  # 0.15秒增加1%，15秒到100%
            # 執行完一個任務後，無論如何都要啟動下一個
            if self.robot_task_map[robot_id] and not self.robot_cancel_event[robot_id].is_set():
                self.robot_status_map[robot_id] = "待機中"
                self.robot_history_map[robot_id].append(f"完成任務：{self.robot_task_map[robot_id]}")
                # 完成時加入 completed_tasks_map
                self.robot_completed_tasks_map.setdefault(robot_id, [])
                self.robot_completed_tasks_map[robot_id].append(self.robot_task_map[robot_id])
                self.robot_task_map[robot_id] = None
                self.robot_progress_map[robot_id] = 0
                QTimer.singleShot(0, self.update_robot_status)
            # 無論如何都要啟動下一個
            QTimer.singleShot(0, lambda: self.start_next_task(robot_id))
        t = threading.Thread(target=run, daemon=True)
        t.start()
        self.robot_thread_map[robot_id] = t

    def cancel_task(self):
        selected_items = self.robot_list.selectedItems()
        if not selected_items or not selected_items[0]:
            return
        for item in selected_items:
            robot_id = item.data(Qt.UserRole)
            if self.robot_task_map[robot_id]:
                self.robot_history_map[robot_id].append(f"取消任務：{self.robot_task_map[robot_id]}")
            self.robot_task_map[robot_id] = None
            self.robot_status_map[robot_id] = "待機中"
            self.robot_progress_map[robot_id] = 0
            self.robot_paused_map[robot_id] = False
            self.robot_cancel_event[robot_id].set()
            self.robot_pause_event[robot_id].clear()
        self.update_robot_status()

    def pause_resume_task(self):
        selected_items = self.robot_list.selectedItems()
        if not selected_items or not selected_items[0]:
            return
        for item in selected_items:
            robot_id = item.data(Qt.UserRole)
            if self.robot_task_map[robot_id]:
                self.robot_paused_map[robot_id] = not self.robot_paused_map[robot_id]
                if self.robot_paused_map[robot_id]:
                    self.robot_history_map[robot_id].append("暫停任務")
                    self.robot_pause_event[robot_id].set()
                else:
                    self.robot_history_map[robot_id].append("繼續任務")
                    self.robot_pause_event[robot_id].clear()
        self.update_robot_status()

    def update_robot_status(self):
        selected_items = self.robot_list.selectedItems()
        if not selected_items or not selected_items[0]:
            self.status_panel.setText("請選擇機器人")
            self.current_task_label.setText("")
            self.progress_bar.setVisible(False)
            self.total_progress_bar.setVisible(False)
            self.cancel_btn.setVisible(False)
            self.pause_btn.setVisible(False)
            self.todo_list.clear()
            self.history_list.clear()
            return
        # 批次選取時顯示提示，進度條等顯示最後一台
        if len(selected_items) > 1:
            self.status_panel.setText(f"已選取 {len(selected_items)} 台機器人，可批次操作\n（下方顯示最後選取的機器人狀態）")
        current = selected_items[-1]
        robot_id = current.data(Qt.UserRole)
        status = self.robot_status_map.get(robot_id, "待機中")
        task = self.robot_task_map.get(robot_id)
        progress = self.robot_progress_map.get(robot_id, 0)
        paused = self.robot_paused_map.get(robot_id, False)
        text = f"機器人ID：{robot_id}\n狀態：{status}\n"
        if task:
            text += f"目前任務：{task}\n進度：{progress}%\n"
            if paused:
                text += "（已暫停）\n"
        else:
            text += "目前任務：無\n"
        text += "電量：100%\n位置：A點\n"  # 假資料
        self.status_panel.setText(self.status_panel.text() + "\n" + text if len(selected_items) > 1 else text)
        # 新增：顯示目前執行任務名稱
        if task:
            self.current_task_label.setText(f"目前執行任務：{task}")
        else:
            self.current_task_label.setText("")
        if task:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(progress)
            self.cancel_btn.setVisible(True)
            self.pause_btn.setVisible(True)
            self.pause_btn.setText("繼續" if paused else "暫停")
            self.pause_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
        else:
            self.progress_bar.setVisible(False)
            self.cancel_btn.setVisible(False)
            self.pause_btn.setVisible(False)
        # 顯示總任務完成度
        all_tasks = self.robot_all_tasks_map.get(robot_id, [])
        completed_tasks = self.robot_completed_tasks_map.get(robot_id, [])
        if all_tasks:
            percent = int(len(completed_tasks) / len(all_tasks) * 100)
            self.total_progress_bar.setVisible(True)
            self.total_progress_bar.setValue(percent)
        else:
            self.total_progress_bar.setVisible(False)
        # 顯示待辦任務列表
        self.todo_list.clear()
        for t in self.robot_task_queue_map.get(robot_id, []):
            self.todo_list.addItem(t)
        self.history_list.clear()
        for h in self.robot_history_map.get(robot_id, []):
            self.history_list.addItem(h) 