import sys
from PyQt5.QtWidgets import QApplication
from login_window import LoginWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 防止最後窗口關閉時退出應用程式
    window = LoginWindow(app)
    window.show()
    sys.exit(app.exec_())