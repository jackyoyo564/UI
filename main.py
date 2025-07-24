import sys
from PyQt5.QtWidgets import QApplication
from login_window import LoginWindow

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        login_window = LoginWindow()
        login_window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"程式發生錯誤：{e}")
        sys.exit(1)