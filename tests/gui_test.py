from PyQt5.QtWidgets import QApplication, QWidget, QLabel

app = QApplication([])
win = QWidget()
win.setWindowTitle("Test Window")
win.setGeometry(100, 100, 300, 150)
label = QLabel("If you can see this, PyQt5 works", win)
label.move(50, 60)
win.show()
app.exec_()
