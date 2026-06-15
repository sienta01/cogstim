"""
CogStim Desktop Admin App
- System tray support (minimize to taskbar)
- Auto-send WhatsApp reminders at 1:00 PM daily (via Selenium automation)
- User management table with detail view
"""

import sys
import os
import json
import requests
from datetime import datetime, timedelta

from whatsapp_sender import WhatsAppSender

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QSystemTrayIcon, QMenu, QDialog, QScrollArea, QFrame, QMessageBox,
    QSplitter, QStatusBar, QLineEdit, QGroupBox, QGridLayout, QCheckBox,
    QProgressDialog, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QColor, QAction, QPainter, QPixmap

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ── Config ───────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_config():
    config_path = os.path.join(BASE_DIR, 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def load_message_template():
    msg_path = os.path.join(BASE_DIR, 'reminder_message.txt')
    with open(msg_path, 'r', encoding='utf-8') as f:
        return f.read().strip()

CONFIG = load_config()
SERVER_URL = CONFIG['server_url'].rstrip('/')
API_KEY = CONFIG['api_key']
REMINDER_HOUR = CONFIG.get('reminder_hour', 13)
REMINDER_MINUTE = CONFIG.get('reminder_minute', 0)
AUTO_SEND = CONFIG.get('auto_send_enabled', True)
CHROME_PROFILE = CONFIG.get(
    'chrome_profile_path',
    os.path.join(BASE_DIR, 'chrome-whatsapp-profile')
)

HEADERS = {'X-API-Key': API_KEY}

# ── Global WhatsApp Sender ───────────────────────────────────────
wa_sender = WhatsAppSender(CHROME_PROFILE)

# ── Colors ───────────────────────────────────────────────────────
BG_DARK = "#0f1117"
BG_CARD = "#1a1d2e"
BG_HOVER = "#252a3a"
TEXT_PRIMARY = "#e4e6eb"
TEXT_SECONDARY = "#8892b0"
ACCENT = "#6c8cff"
GREEN = "#25D366"
ORANGE = "#ffb74d"
RED = "#e74c3c"

STYLESHEET = f"""
    QMainWindow, QDialog {{ background: {BG_DARK}; }}
    QWidget {{ color: {TEXT_PRIMARY}; font-family: 'Segoe UI', 'Inter', sans-serif; }}
    QLabel {{ color: {TEXT_PRIMARY}; }}
    QPushButton {{
        background: {BG_CARD}; color: {TEXT_PRIMARY}; border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px; padding: 8px 18px; font-weight: 600; font-size: 12px;
    }}
    QPushButton:hover {{ background: {BG_HOVER}; border-color: {ACCENT}; }}
    QPushButton#sendBtn {{ background: {GREEN}; color: white; border: none; }}
    QPushButton#sendBtn:hover {{ background: #128C7E; }}
    QPushButton#primaryBtn {{ background: {ACCENT}; color: white; border: none; }}
    QPushButton#primaryBtn:hover {{ background: #5a6fd6; }}
    QTableWidget {{
        background: {BG_CARD}; border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px; gridline-color: rgba(255,255,255,0.04);
        selection-background-color: rgba(108,140,255,0.15);
    }}
    QTableWidget::item {{ padding: 6px 12px; border-bottom: 1px solid rgba(255,255,255,0.04); }}
    QTableWidget::item:hover {{ background: rgba(108,140,255,0.08); }}
    QHeaderView::section {{
        background: {BG_CARD}; color: {TEXT_SECONDARY}; border: none;
        padding: 10px 12px; font-size: 11px; font-weight: 700;
        text-transform: uppercase; border-bottom: 1px solid rgba(255,255,255,0.08);
    }}
    QLineEdit {{
        background: rgba(255,255,255,0.04); border: 1.5px solid rgba(255,255,255,0.1);
        border-radius: 8px; padding: 8px 14px; color: {TEXT_PRIMARY}; font-size: 12px;
    }}
    QLineEdit:focus {{ border-color: {ACCENT}; }}
    QStatusBar {{ background: {BG_CARD}; color: {TEXT_SECONDARY}; border-top: 1px solid rgba(255,255,255,0.06); }}
    QGroupBox {{
        background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px; margin-top: 12px; padding-top: 24px; font-weight: 700;
    }}
    QGroupBox::title {{ color: {TEXT_SECONDARY}; subcontrol-origin: margin; left: 16px; padding: 0 8px; }}
    QScrollArea {{ border: none; }}
    QCheckBox {{ color: {TEXT_PRIMARY}; spacing: 8px; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 2px solid rgba(255,255,255,0.2); }}
    QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
"""


# ── API Worker Thread ────────────────────────────────────────────
class ApiWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, url, method='GET', data=None):
        super().__init__()
        self.url = url
        self.method = method.upper()
        self.data = data

    def run(self):
        try:
            if self.method == 'GET':
                resp = requests.get(self.url, headers=HEADERS, timeout=15)
            elif self.method == 'POST':
                resp = requests.post(self.url, headers=HEADERS, json=self.data, timeout=15)
            elif self.method == 'PUT':
                resp = requests.put(self.url, headers=HEADERS, json=self.data, timeout=15)
            elif self.method == 'DELETE':
                resp = requests.delete(self.url, headers=HEADERS, timeout=15)
            else:
                resp = requests.post(self.url, headers=HEADERS, json=self.data, timeout=15)
            resp.raise_for_status()
            self.finished.emit(resp.json())
        except requests.exceptions.HTTPError as e:
            try:
                err_body = e.response.json().get('error', str(e))
            except Exception:
                err_body = str(e)
            self.error.emit(err_body)
        except Exception as e:
            self.error.emit(str(e))


# ── WhatsApp Browser Worker ──────────────────────────────────────
class WaBrowserWorker(QThread):
    """Start / wait-for-ready the Selenium browser in background."""
    ready = pyqtSignal()
    failed = pyqtSignal(str)

    def run(self):
        try:
            wa_sender.start_browser()
            if wa_sender.wait_until_ready(timeout=90):
                self.ready.emit()
            else:
                self.failed.emit("Timed out waiting for WhatsApp Web login.")
        except Exception as e:
            self.failed.emit(str(e))


class WaSendWorker(QThread):
    """Send a single WhatsApp message in the background."""
    finished = pyqtSignal(str, dict)  # phone, result

    def __init__(self, phone, message):
        super().__init__()
        self.phone = phone
        self.message = message

    def run(self):
        result = wa_sender.send_message(self.phone, self.message)
        self.finished.emit(self.phone, result)


class WaBatchWorker(QThread):
    """Send WhatsApp messages to a list of users sequentially."""
    progress = pyqtSignal(int, int, str, bool)  # current, total, info, success
    done = pyqtSignal(int, int)  # sent, failed

    def __init__(self, users, message_template):
        super().__init__()
        self.users = users  # list of {id, username, phone_number}
        self.message_template = message_template
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        sent = 0
        failed = 0
        total = len(self.users)
        for i, user in enumerate(self.users):
            if self._cancel:
                break
            phone = user.get('phone_number', '')
            if not phone:
                failed += 1
                self.progress.emit(i + 1, total, f"{user['username']}: no phone", False)
                continue
            msg = self.message_template.replace('{username}', user['username'])
            result = wa_sender.send_message(phone, msg)
            if result['success']:
                sent += 1
                self.progress.emit(i + 1, total, f"✅ {user['username']}", True)
                # Record on server
                try:
                    requests.post(
                        f"{SERVER_URL}/admin/api/send_reminder/{user['id']}",
                        headers=HEADERS, timeout=10)
                except Exception:
                    pass
            else:
                failed += 1
                self.progress.emit(
                    i + 1, total,
                    f"❌ {user['username']}: {result['error']}", False)
        self.done.emit(sent, failed)


# ── Chart Widget ─────────────────────────────────────────────────
class ScoreChart(FigureCanvas):
    def __init__(self, title, color, parent=None):
        self.fig = Figure(figsize=(5, 2.2), dpi=100)
        self.fig.patch.set_facecolor('#1a1d2e')
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.color = color
        self.title = title
        self._style_ax()

    def _style_ax(self):
        self.ax.set_facecolor('#1a1d2e')
        self.ax.tick_params(colors='#555a70', labelsize=8)
        self.ax.spines['bottom'].set_color('#333')
        self.ax.spines['left'].set_color('#333')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.set_title(self.title, color='#b0b8d1', fontsize=10, fontweight='bold', pad=8)

    def update_data(self, labels, scores):
        self.ax.clear()
        self._style_ax()
        if scores:
            x = range(len(scores))
            self.ax.fill_between(x, scores, alpha=0.15, color=self.color)
            self.ax.plot(x, scores, color=self.color, linewidth=2, marker='o', markersize=4)
            self.ax.set_xticks(list(x))
            self.ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=7)
        else:
            self.ax.text(0.5, 0.5, 'No data', ha='center', va='center', color='#555a70', transform=self.ax.transAxes)
        self.fig.tight_layout()
        self.draw()


# ── Account Form Dialog ──────────────────────────────────────────
class AccountFormDialog(QDialog):
    """Dialog for creating or editing a user account."""
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data  # None = create mode, dict = edit mode
        self.is_edit = user_data is not None
        self.setWindowTitle("Edit Account" if self.is_edit else "Add New Account")
        self.setMinimumSize(420, 320)
        self.result_data = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 28, 28, 28)

        # Header
        header = QLabel("✏️ Edit Account" if self.is_edit else "➕ Add New Account")
        header.setFont(QFont('Segoe UI', 16, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(header)

        # Form
        form_group = QGroupBox("Account Details")
        form_layout = QGridLayout()
        form_layout.setSpacing(12)

        lbl_user = QLabel("Username")
        lbl_user.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        if self.is_edit:
            self.username_input.setText(self.user_data.get('username', ''))
        form_layout.addWidget(lbl_user, 0, 0)
        form_layout.addWidget(self.username_input, 0, 1)

        lbl_phone = QLabel("Phone")
        lbl_phone.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700;")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+62... or 08...")
        if self.is_edit:
            self.phone_input.setText(self.user_data.get('phone_number', '') or '')
        form_layout.addWidget(lbl_phone, 1, 0)
        form_layout.addWidget(self.phone_input, 1, 1)

        lbl_pass = QLabel("Password")
        lbl_pass.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700;")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        if self.is_edit:
            self.password_input.setPlaceholderText("Leave blank to keep current")
        else:
            self.password_input.setPlaceholderText("Enter password")
        form_layout.addWidget(lbl_pass, 2, 0)
        form_layout.addWidget(self.password_input, 2, 1)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("💾 Save" if self.is_edit else "➕ Create")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumHeight(40)
        save_btn.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
        save_btn.clicked.connect(self.on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def on_save(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        phone = self.phone_input.text().strip()

        if not username:
            QMessageBox.warning(self, "Validation", "Username is required.")
            return
        if not self.is_edit and not password:
            QMessageBox.warning(self, "Validation", "Password is required for new accounts.")
            return

        self.result_data = {
            'username': username,
            'password': password,
            'phone_number': phone
        }
        self.accept()


# ── Confirm Delete Dialog ────────────────────────────────────────
class ConfirmDeleteDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Delete")
        self.setMinimumSize(380, 200)
        self.setup_ui(username)

    def setup_ui(self, username):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 28, 28, 28)

        icon_label = QLabel("⚠️")
        icon_label.setFont(QFont('Segoe UI', 32))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        msg = QLabel(f"Delete user <b>{username}</b>?<br>"
                     f"<span style='color:{TEXT_SECONDARY}; font-size: 11px;'>This will permanently remove the account and all their test scores.</span>")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setFont(QFont('Segoe UI', 12))
        layout.addWidget(msg)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setMinimumHeight(40)
        delete_btn.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
        delete_btn.setStyleSheet(f"background: {RED}; color: white; border: none; border-radius: 8px; padding: 8px 18px; font-weight: 600;")
        delete_btn.clicked.connect(self.accept)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)


# ── User Detail Dialog ───────────────────────────────────────────
class UserDetailDialog(QDialog):
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.setWindowTitle(f"User Detail — {user_data['username']}")
        self.setMinimumSize(650, 700)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel(f"👤 {self.user_data['username']}")
        header.setFont(QFont('Segoe UI', 18, QFont.Weight.Bold))
        layout.addWidget(header)

        # Info grid
        info_group = QGroupBox("User Information")
        info_layout = QGridLayout()
        info_layout.setSpacing(12)

        info_items = [
            ("📱 Phone", self.user_data.get('phone_number') or '—'),
            ("🕐 Last Test", self.user_data.get('last_exec') or 'Never'),
            ("📨 Last Reminder", self.user_data.get('last_reminder_sent') or 'Never'),
        ]
        for i, (label, value) in enumerate(info_items):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
            val = QLabel(value)
            val.setStyleSheet(f"font-size: 13px; font-weight: 600;")
            info_layout.addWidget(lbl, i, 0)
            info_layout.addWidget(val, i, 1)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Charts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setSpacing(12)

        sh = self.user_data.get('score_history', {})
        charts_config = [
            ("🎯 Go/No-Go Scores", ORANGE, sh.get('go_no_go', {})),
            ("🎨 Stroop Scores", ACCENT, sh.get('stroop', {})),
            ("😀 Emoji Scores", GREEN, sh.get('emoji', {})),
        ]
        for title, color, data in charts_config:
            chart = ScoreChart(title, color)
            chart.update_data(data.get('labels', []), data.get('scores', []))
            chart.setMinimumHeight(180)
            chart_layout.addWidget(chart)

        scroll.setWidget(chart_widget)
        layout.addWidget(scroll, 1)

        # Send reminder button
        phone = self.user_data.get('phone_number', '')
        send_btn = QPushButton("📲 Kirim Reminder WhatsApp")
        send_btn.setObjectName("sendBtn")
        send_btn.setFont(QFont('Segoe UI', 12, QFont.Weight.Bold))
        send_btn.setMinimumHeight(44)
        send_btn.setEnabled(bool(phone) and wa_sender.is_ready())
        if not wa_sender.is_ready():
            send_btn.setToolTip("Connect WhatsApp first from the main window")
        send_btn.clicked.connect(lambda: self.send_reminder())
        layout.addWidget(send_btn)

    def send_reminder(self):
        phone = self.user_data.get('phone_number', '')
        username = self.user_data.get('username', '')
        if not wa_sender.is_ready():
            QMessageBox.warning(self, "Not Connected",
                                "WhatsApp is not connected. Please connect first.")
            return
        if phone:
            self._worker = WaSendWorker(
                phone, load_message_template().replace('{username}', username))
            self._worker.finished.connect(
                lambda ph, res: self._on_sent(ph, res, username))
            self._worker.start()

    def _on_sent(self, phone, result, username):
        if result['success']:
            # Record on server
            try:
                requests.post(
                    f"{SERVER_URL}/admin/api/send_reminder/{self.user_data['id']}",
                    headers=HEADERS, timeout=10)
            except Exception:
                pass
            QMessageBox.information(self, "Sent",
                                    f"✅ Reminder sent to {username}")
        else:
            QMessageBox.warning(self, "Failed",
                                f"❌ {result['error']}")


# ── Main Window ──────────────────────────────────────────────────
class AdminWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CogStim Admin — Desktop")
        self.setMinimumSize(1100, 650)
        self.workers = []
        self.users_data = []
        self.reminder_sent_today = False

        self.setup_ui()
        self.setup_tray()
        self.setup_timers()
        self.load_users()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ── Header ──
        header_layout = QHBoxLayout()
        title = QLabel("🛡️ CogStim Admin")
        title.setFont(QFont('Segoe UI', 20, QFont.Weight.ExtraBold))
        title.setStyleSheet(f"color: {ACCENT};")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # WhatsApp connection controls
        self.wa_status_label = QLabel("⚪ WhatsApp: Disconnected")
        self.wa_status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        header_layout.addWidget(self.wa_status_label)

        self.wa_connect_btn = QPushButton("🟢 Connect WA")
        self.wa_connect_btn.setObjectName("sendBtn")
        self.wa_connect_btn.clicked.connect(self.connect_whatsapp)
        header_layout.addWidget(self.wa_connect_btn)

        self.wa_disconnect_btn = QPushButton("🔴 Disconnect")
        self.wa_disconnect_btn.setStyleSheet(f"background: {RED}; color: white; border: none;")
        self.wa_disconnect_btn.clicked.connect(self.disconnect_whatsapp)
        self.wa_disconnect_btn.setVisible(False)
        header_layout.addWidget(self.wa_disconnect_btn)

        self.auto_check = QCheckBox("Auto-send @1PM")
        self.auto_check.setChecked(AUTO_SEND)
        self.auto_check.setStyleSheet(f"font-size: 12px; font-weight: 600;")
        header_layout.addWidget(self.auto_check)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("primaryBtn")
        refresh_btn.clicked.connect(self.load_users)
        header_layout.addWidget(refresh_btn)

        add_user_btn = QPushButton("➕ Add Account")
        add_user_btn.setObjectName("primaryBtn")
        add_user_btn.clicked.connect(self.add_account)
        header_layout.addWidget(add_user_btn)

        main_layout.addLayout(header_layout)

        # ── Search ──
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search users...")
        self.search_box.textChanged.connect(self.filter_table)
        main_layout.addWidget(self.search_box)

        # ── Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "ID", "Username", "Last Exec", "Off Time",
            "Go/No-Go", "Stroop", "Emoji", "Phone", "Last Message",
            "Send", "Edit", "Delete"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(11, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(self.table.styleSheet() + "alternate-background-color: rgba(255,255,255,0.02);")
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)
        main_layout.addWidget(self.table, 1)

        # ── Status bar ──
        self.statusBar().showMessage("Ready")
        self.status_label = QLabel("")
        self.statusBar().addPermanentWidget(self.status_label)

    def setup_tray(self):
        # Create a simple colored icon for the tray
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(ACCENT))
        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))
        painter.setFont(QFont('Segoe UI', 16, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "C")
        painter.end()
        icon = QIcon(pixmap)

        self.tray_icon = QSystemTrayIcon(icon, self)
        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                padding: 4px 0;
            }
            QMenu::item {
                color: #1a1a1a;
                padding: 8px 24px;
                font-size: 12px;
                font-weight: 600;
            }
            QMenu::item:selected {
                background: #e8eaf6;
                color: #1a1a1a;
            }
            QMenu::separator {
                height: 1px;
                background: #e0e0e0;
                margin: 4px 8px;
            }
        """)

        show_action = QAction("Show Admin Console", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        refresh_action = QAction("Refresh Data", self)
        refresh_action.triggered.connect(self.load_users)
        tray_menu.addAction(refresh_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.setToolTip("CogStim Admin — Desktop")
        self.tray_icon.show()

    def setup_timers(self):
        # Check every 60 seconds for reminder time
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminder_time)
        self.reminder_timer.start(60000)

        # Auto-refresh every 5 minutes
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_users)
        self.refresh_timer.start(300000)

        # Reset daily flag at midnight
        self.midnight_timer = QTimer(self)
        self.midnight_timer.timeout.connect(self.reset_daily)
        self.midnight_timer.start(60000)

    def check_reminder_time(self):
        now = datetime.now()
        if (now.hour == REMINDER_HOUR and now.minute == REMINDER_MINUTE
                and not self.reminder_sent_today and self.auto_check.isChecked()):
            self.reminder_sent_today = True
            self.auto_send_reminders()

    def reset_daily(self):
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            self.reminder_sent_today = False

    def auto_send_reminders(self):
        """Fetch pending users and send WhatsApp reminders automatically."""
        if not wa_sender.is_ready():
            self.statusBar().showMessage("⚠️ Auto-send skipped: WhatsApp not connected")
            return
        self.statusBar().showMessage("🔔 Checking for pending users...")

        worker = ApiWorker(f"{SERVER_URL}/admin/api/check_pending")
        worker.finished.connect(self._on_pending_received)
        worker.error.connect(lambda e: self.statusBar().showMessage(f"❌ Error: {e}"))
        self.workers.append(worker)
        worker.start()

    def _on_pending_received(self, pending_users):
        users_with_phone = [u for u in pending_users if u.get('phone_number')]
        if not users_with_phone:
            msg = "✅ All users have completed today's test"
            self.statusBar().showMessage(msg)
            self.tray_icon.showMessage("CogStim Reminder", msg,
                                       QSystemTrayIcon.MessageIcon.Information, 5000)
            return

        template = load_message_template()
        self._batch_worker = WaBatchWorker(users_with_phone, template)
        self._batch_worker.progress.connect(self._on_batch_progress)
        self._batch_worker.done.connect(self._on_batch_done)
        self._batch_worker.start()

    def load_users(self):
        self.statusBar().showMessage("Loading users...")
        worker = ApiWorker(f"{SERVER_URL}/admin/api/users")
        worker.finished.connect(self._on_users_loaded)
        worker.error.connect(lambda e: self.statusBar().showMessage(f"❌ Error: {e}"))
        self.workers.append(worker)
        worker.start()

    def _on_users_loaded(self, data):
        self.users_data = data
        self.populate_table(data)
        self.statusBar().showMessage(f"✅ Loaded {len(data)} users")
        self.status_label.setText(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")

    def populate_table(self, data):
        self.table.setRowCount(len(data))
        for row, u in enumerate(data):
            items = [
                str(u['id']),
                u['username'],
                u.get('last_exec') or '—',
                u.get('off_time', 'Never'),
                str(u.get('score_go_nogo') if u.get('score_go_nogo') is not None else '—'),
                str(u.get('score_stroop') if u.get('score_stroop') is not None else '—'),
                str(u.get('score_emoji') if u.get('score_emoji') is not None else '—'),
                u.get('phone_number') or '—',
                u.get('last_reminder_sent') or '—',
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 1:  # Username column - make clickable looking
                    item.setForeground(QColor(ACCENT))
                    item.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
                self.table.setItem(row, col, item)

            # Send button
            send_btn = QPushButton("📲 Send")
            send_btn.setObjectName("sendBtn")
            send_btn.setEnabled(bool(u.get('phone_number')) and wa_sender.is_ready())
            uid, uname, uphone = u['id'], u['username'], u.get('phone_number', '')
            send_btn.clicked.connect(lambda checked, uid=uid, uname=uname, uphone=uphone: self._send_clicked(uid, uname, uphone))
            self.table.setCellWidget(row, 9, send_btn)

            # Edit button
            edit_btn = QPushButton("✏️ Edit")
            edit_btn.setStyleSheet(f"background: {ORANGE}; color: #1a1a1a; border: none; border-radius: 8px; padding: 6px 12px; font-weight: 600; font-size: 11px;")
            edit_btn.clicked.connect(lambda checked, _u=u: self.edit_account(_u))
            self.table.setCellWidget(row, 10, edit_btn)

            # Delete button
            del_btn = QPushButton("🗑️ Del")
            del_btn.setStyleSheet(f"background: {RED}; color: white; border: none; border-radius: 8px; padding: 6px 12px; font-weight: 600; font-size: 11px;")
            del_btn.clicked.connect(lambda checked, _uid=uid, _uname=uname: self.delete_account(_uid, _uname))
            self.table.setCellWidget(row, 11, del_btn)

    def _send_clicked(self, uid, uname, uphone):
        if not wa_sender.is_ready():
            QMessageBox.warning(self, "Not Connected",
                                "Connect WhatsApp first using the 🟢 Connect WA button.")
            return
        if uphone:
            template = load_message_template()
            msg = template.replace('{username}', uname)
            self.statusBar().showMessage(f"📲 Sending to {uname}...")
            worker = WaSendWorker(uphone, msg)
            worker.finished.connect(
                lambda ph, res, _uid=uid, _uname=uname: self._on_single_sent(ph, res, _uid, _uname))
            self.workers.append(worker)
            worker.start()

    def _on_single_sent(self, phone, result, uid, uname):
        if result['success']:
            try:
                requests.post(f"{SERVER_URL}/admin/api/send_reminder/{uid}",
                              headers=HEADERS, timeout=10)
            except Exception:
                pass
            self.statusBar().showMessage(f"✅ Reminder sent to {uname}")
            QTimer.singleShot(2000, self.load_users)
        else:
            self.statusBar().showMessage(f"❌ Failed for {uname}: {result['error']}")

    def filter_table(self, text):
        text = text.lower()
        filtered = [u for u in self.users_data if text in u['username'].lower() or text in (u.get('phone_number') or '')]
        self.populate_table(filtered)

    def on_row_double_clicked(self, row, col):
        username_item = self.table.item(row, 1)
        if not username_item:
            return
        username = username_item.text()
        user = next((u for u in self.users_data if u['username'] == username), None)
        if user:
            self.show_user_detail(user['id'])

    def show_user_detail(self, user_id):
        self.statusBar().showMessage("Loading user detail...")
        worker = ApiWorker(f"{SERVER_URL}/admin/api/user/{user_id}")
        worker.finished.connect(self._on_detail_loaded)
        worker.error.connect(lambda e: self.statusBar().showMessage(f"❌ Error: {e}"))
        self.workers.append(worker)
        worker.start()

    def _on_detail_loaded(self, data):
        self.statusBar().showMessage("Ready")
        dialog = UserDetailDialog(data, self)
        dialog.setStyleSheet(STYLESHEET)
        dialog.exec()

    # ── Account management ─────────────────────────
    def add_account(self):
        dialog = AccountFormDialog(self)
        dialog.setStyleSheet(STYLESHEET)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
            data = dialog.result_data
            self.statusBar().showMessage("Creating account...")
            worker = ApiWorker(f"{SERVER_URL}/admin/api/users/create", 'POST', data)
            worker.finished.connect(self._on_account_created)
            worker.error.connect(self._on_account_error)
            self.workers.append(worker)
            worker.start()

    def _on_account_created(self, result):
        self.statusBar().showMessage(f"✅ {result.get('message', 'Account created')}")
        QMessageBox.information(self, "Success", result.get('message', 'Account created successfully.'))
        self.load_users()

    def edit_account(self, user_data):
        dialog = AccountFormDialog(self, user_data=user_data)
        dialog.setStyleSheet(STYLESHEET)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
            data = dialog.result_data
            uid = user_data['id']
            self.statusBar().showMessage("Updating account...")
            worker = ApiWorker(f"{SERVER_URL}/admin/api/users/{uid}/edit", 'PUT', data)
            worker.finished.connect(self._on_account_edited)
            worker.error.connect(self._on_account_error)
            self.workers.append(worker)
            worker.start()

    def _on_account_edited(self, result):
        self.statusBar().showMessage(f"✅ {result.get('message', 'Account updated')}")
        QMessageBox.information(self, "Success", result.get('message', 'Account updated successfully.'))
        self.load_users()

    def delete_account(self, user_id, username):
        dialog = ConfirmDeleteDialog(username, self)
        dialog.setStyleSheet(STYLESHEET)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.statusBar().showMessage(f"Deleting {username}...")
            worker = ApiWorker(f"{SERVER_URL}/admin/api/users/{user_id}/delete", 'DELETE')
            worker.finished.connect(self._on_account_deleted)
            worker.error.connect(self._on_account_error)
            self.workers.append(worker)
            worker.start()

    def _on_account_deleted(self, result):
        self.statusBar().showMessage(f"✅ {result.get('message', 'Account deleted')}")
        QMessageBox.information(self, "Deleted", result.get('message', 'Account deleted successfully.'))
        self.load_users()

    def _on_account_error(self, error):
        self.statusBar().showMessage(f"❌ Error: {error}")
        QMessageBox.warning(self, "Error", f"Operation failed:\n{error}")

    # ── Window management ────────────────────────
    def closeEvent(self, event):
        """Minimize to tray instead of closing."""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "CogStim Admin",
            "App minimized to tray. Auto-reminders still active.",
            QSystemTrayIcon.MessageIcon.Information, 3000
        )

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def show_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def quit_app(self):
        wa_sender.quit()
        self.tray_icon.hide()
        QApplication.quit()

    # ── WhatsApp connection ───────────────────────
    def connect_whatsapp(self):
        self.wa_connect_btn.setEnabled(False)
        self.wa_connect_btn.setText("⏳ Connecting...")
        self.statusBar().showMessage("Starting WhatsApp Web browser... Scan QR if needed.")

        self._wa_browser_worker = WaBrowserWorker()
        self._wa_browser_worker.ready.connect(self._on_wa_ready)
        self._wa_browser_worker.failed.connect(self._on_wa_failed)
        self.workers.append(self._wa_browser_worker)
        self._wa_browser_worker.start()

    def _on_wa_ready(self):
        self.wa_status_label.setText("🟢 WhatsApp: Connected")
        self.wa_status_label.setStyleSheet(f"color: {GREEN}; font-size: 11px; font-weight: 600;")
        self.wa_connect_btn.setVisible(False)
        self.wa_disconnect_btn.setVisible(True)
        self.statusBar().showMessage("✅ WhatsApp Web connected!")
        self.load_users()  # refresh to enable Send buttons

    def _on_wa_failed(self, error):
        self.wa_connect_btn.setEnabled(True)
        self.wa_connect_btn.setText("🟢 Connect WA")
        self.wa_status_label.setText("🔴 WhatsApp: Failed")
        self.wa_status_label.setStyleSheet(f"color: {RED}; font-size: 11px; font-weight: 600;")
        self.statusBar().showMessage(f"❌ WhatsApp connection failed: {error}")
        QMessageBox.warning(self, "Connection Failed", f"Could not connect to WhatsApp Web:\n{error}")

    def disconnect_whatsapp(self):
        wa_sender.quit()
        self.wa_status_label.setText("⚪ WhatsApp: Disconnected")
        self.wa_status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        self.wa_connect_btn.setVisible(True)
        self.wa_connect_btn.setEnabled(True)
        self.wa_connect_btn.setText("🟢 Connect WA")
        self.wa_disconnect_btn.setVisible(False)
        self.statusBar().showMessage("WhatsApp disconnected.")
        self.load_users()  # refresh to disable Send buttons

    def _on_batch_progress(self, current, total, info, success):
        self.statusBar().showMessage(f"[{current}/{total}] {info}")

    def _on_batch_done(self, sent, failed):
        msg = f"✅ Auto-send complete: {sent} sent, {failed} failed"
        self.statusBar().showMessage(msg)
        self.tray_icon.showMessage("CogStim Reminder", msg,
                                   QSystemTrayIcon.MessageIcon.Information, 5000)
        self.load_users()


# ── Entry Point ──────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray
    app.setStyleSheet(STYLESHEET)

    window = AdminWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
