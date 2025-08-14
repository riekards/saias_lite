# gui.py
import sys
import threading
import json
import os
import logging
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction, QTextEdit, QLineEdit,
    QWidget, QVBoxLayout, QPushButton, QMessageBox, QLabel
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer
from pystray import Icon as SysTrayIcon
import keyboard
from agent.tools.background_setup import ensure_startup_task
from agent.tools.llm import call_chat_llm
from agent.tools.intent_router import route as route_intent
from agent.tools.evaluate_patch import (
    list_pending_patches,
    apply_patch_by_id,
    print_pending_patch_summaries
)
import io
import contextlib

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "memory", "config.json")

logging.basicConfig(
    filename='saiasgui_log.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("GUI initialized.")

class AssistantGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SAIAS Assistant")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.resize(800, 600)

        layout = QVBoxLayout()

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        # Input field
        self.input_field = QLineEdit()
        self.input_field.returnPressed.connect(self.handle_input)
        layout.addWidget(self.input_field)

        # Status label
        self.status_label = QLabel("🟢 Ready")
        layout.addWidget(self.status_label)

        # Approve Patches Button
        self.approve_patch_button = QPushButton("Approve All Patches")
        self.approve_patch_button.clicked.connect(self.approve_all_patches)
        layout.addWidget(self.approve_patch_button)

        # Refresh Button
        self.refresh_button = QPushButton("Refresh Patches")
        self.refresh_button.clicked.connect(self.show_pending_patches)
        layout.addWidget(self.refresh_button)

        self.setLayout(layout)

        # Auto-refresh patch status
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_patch_status)
        self.timer.start(5000)  # Every 5 seconds

        self.update_patch_status()

    def update_patch_status(self):
        patches = list_pending_patches()
        if patches:
            self.status_label.setText(f"🟡 {len(patches)} Pending Patch(s)")
            self.status_label.setStyleSheet("color: orange;")
        else:
            self.status_label.setText("🟢 Ready")
            self.status_label.setStyleSheet("color: green;")

    def show_pending_patches(self):
        patches = list_pending_patches()
        if not patches:
            self.chat_display.append("<b>No pending patches.</b>")
            return

        msg = "<b>🧠 Pending Patches:</b>\n"
        for fname, patch in patches:
            msg += f"""
• <b>{patch['patch_id']}</b>
  ↪ File: {patch['target_file']}
  ↪ Score: {patch['refactor_score']}/10
  ↪ {patch['description']}\n
            """
        self.chat_display.append(msg)

    def approve_all_patches(self):
        patches = list_pending_patches()
        if not patches:
            QMessageBox.information(self, "No Patches", "There are no pending patches to approve.")
            return

        reply = QMessageBox.question(
            self, 'Approve All Patches?',
            f"You are about to apply {len(patches)} patch(es). Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        applied = 0
        for _, patch in patches:
            if apply_patch_by_id(patch["patch_id"]):
                applied += 1

        QMessageBox.information(self, "Success", f"Applied {applied} patch(es).")
        self.update_patch_status()

    def handle_input(self):
        user_input = self.input_field.text().strip()
        if not user_input:
            return

        self.chat_display.append(f"<b>You:</b> {user_input}")
        self.input_field.clear()

        # Route intent
        try:
            response = route_intent(user_input)
        except Exception as e:
            logging.error(f"Intent routing error: {e}")
            response = "❌ An error occurred while processing your request."

        # Display response
        self.chat_display.append(f"<b>SAIAS:</b> {response}")

        # Auto-show patches if generated
        if "patch" in response.lower() and "pending" in response.lower():
            QTimer.singleShot(1000, self.show_pending_patches)


def launch_gui():
    app = QApplication(sys.argv)
    window = AssistantGUI()

    # Setup system tray
    icon_path = os.path.join(os.path.dirname(__file__), "saias.ico")
    tray_icon = QSystemTrayIcon(QIcon(icon_path))
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

    # Minimize to tray
    def override_close(event):
        event.ignore()
        window.hide()
        print("🛑 Window hidden to tray.")
    window.closeEvent = override_close

    window.show()
    app.exec_()


def background_listener():
    def on_hotkey():
        app = QApplication.instance()
        if app:
            for widget in app.topLevelWidgets():
                if isinstance(widget, AssistantGUI):
                    widget.showNormal()
                    widget.raise_()
                    widget.activateWindow()

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    hotkey = config["background"].get("wake_hotkey", "ctrl+shift+space")
    keyboard.add_hotkey(hotkey, on_hotkey)


def launch():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    if config.get("background", {}).get("startup_enabled", False):
        ensure_startup_task()

    if config.get("background", {}).get("enabled", True):
        t = threading.Thread(target=background_listener, daemon=True)
        t.start()

    launch_gui()