from PyQt6.QtWidgets import QApplication, QmainWindow
import sys

def main():
    app = QApplication(sys.argv)
    window = QmainWindow()
    window.setGeometry(0, 0, 300, 300)
    window.show()
    
    sys.exit(app.exec())
    
main()