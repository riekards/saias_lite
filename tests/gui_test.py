try:
	from PyQt5.QtWidgets import QApplication, QWidget, QLabel
except Exception:
	# PyQt5 not available; keep tests import-safe
	def _demo_window():
		print("PyQt5 not available; skipping GUI demo.")
else:
	# Prevent event loop from running during unittest discovery/import.
	# Keep manual demo runnable via `python tests/gui_test.py`.
	def _demo_window():
		app = QApplication.instance() or QApplication([])
		win = QWidget()
		win.setWindowTitle("Test Window")
		win.setGeometry(100, 100, 300, 150)
		label = QLabel("If you can see this, PyQt5 works", win)
		label.move(50, 60)
		win.show()
		app.exec_()


if __name__ == "__main__":
	_demo_window()
