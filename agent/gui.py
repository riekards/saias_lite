import sys
import threading
import json
import os
import logging
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QTextEdit, QLineEdit, QWidget, QVBoxLayout, QPushButton, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from pystray import Icon as SysTrayIcon, MenuItem as item
import keyboard
from .tools.background_setup import ensure_startup_task
from agent.tools.llm import call_chat_llm, call_code_llm
from agent.tools.intent_router import detect_intent

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "memory", "config.json")

logging.basicConfig(filename='saiasgui_log.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("Your clear log message here.")

class AssistantGUI(QWidget):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("SAIAS Assistant")
		self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
		self.resize(800, 600)

		layout = QVBoxLayout()

		self.chat_display = QTextEdit()
		self.chat_display.setReadOnly(True)
		layout.addWidget(self.chat_display)

		self.input_field = QLineEdit()
		self.input_field.returnPressed.connect(self.handle_input)
		layout.addWidget(self.input_field)

		self.setLayout(layout)
	
	def setup_patch_approval(self):
		self.approve_patch_button = QPushButton("Approve Patches", self)
		self.approve_patch_button.clicked.connect(self.approve_patches)
		self.layout().addWidget(self.approve_patch_button)
	
	
	def approve_patches(self):
		# Placeholder for patch approval logic
		reply = QMessageBox.question(self, 'Patch Approval',
									'Approve all pending patches?',
									QMessageBox.Yes | QMessageBox.No)
		if reply == QMessageBox.Yes:
			# Here call your patch approval logic
			QMessageBox.information(self, 'Approved', 'Patches approved successfully!')
		else:
			QMessageBox.warning(self, 'Canceled', 'Patch approval canceled!')

	def handle_input(self):
		user_input = self.input_field.text().strip()
		if user_input:
			self.chat_display.append(f"You: {user_input}")

			intent = detect_intent(user_input)
			if intent == "code":
				response = call_code_llm(user_input)
			else:
				response = call_chat_llm(user_input)

			self.chat_display.append(f"SAIAS ({intent}): {response}")
			self.input_field.clear()



def launch_gui():
	print("🧪 Launching GUI with tray support...")

	app = QApplication(sys.argv)
	window = AssistantGUI()

	# Setup system tray
	tray_icon = QSystemTrayIcon(QIcon("agent/saias.ico"))
	tray_icon.setToolTip("SAIAS - Running in background")

	menu = QMenu()

	open_action = QAction("Open")
	open_action.triggered.connect(window.showNormal)
	menu.addAction(open_action)

	exit_action = QAction("Exit")
	def quit_app():
		print("💀 Exiting via tray menu...")
		tray_icon.hide()
		app.quit()

	exit_action.triggered.connect(quit_app)
	menu.addAction(exit_action)

	tray_icon.setContextMenu(menu)
	tray_icon.show()

	# Override close event to minimize to tray
	def override_close(event):
		event.ignore()
		window.hide()
		print("🛑 Window hidden to tray.")

	window.closeEvent = override_close

	window.show()
	app.exec_()



def background_listener():
	def on_hotkey():
		gui = QApplication.instance()
		if gui:
			for widget in gui.topLevelWidgets():
				if isinstance(widget, AssistantGUI):
					widget.showNormal()
					widget.raise_()
					widget.activateWindow()

	with open(CONFIG_PATH, "r") as f:
		config = json.load(f)

	hotkey = config["background"].get("wake_hotkey", "ctrl+shift+space")
	keyboard.add_hotkey(hotkey, on_hotkey)


def launch():
	# Ensure background setup task exists
	with open(CONFIG_PATH, "r") as f:
		config = json.load(f)

	if config.get("background", {}).get("startup_enabled", False):
		ensure_startup_task()

	if config.get("background", {}).get("enabled", True):
		t = threading.Thread(target=background_listener, daemon=True)
		t.start()

	launch_gui()
