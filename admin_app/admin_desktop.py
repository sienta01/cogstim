"""
CogStim Desktop Admin App
- System tray support (minimize to taskbar)
- Auto-send WhatsApp reminders at 1:00 PM daily
- User management table with detail view
"""

import sys
import os
import json
import requests
import webbrowser
import urllib.parse
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QSystemTrayIcon, QMenu, QDialog, QScrollArea, QFrame, QMessageBox,
    QSplitter, QStatusBar, QLineEdit, QGroupBox, QGridLayout, QCheckBox
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

HEADERS = {'X-API-Key': API_KEY}

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
        self.method = method
        self.data = data

    def run(self):
        try:
            if self.method == 'GET':
                resp = requests.get(self.url, headers=HEADERS, timeout=15)
            else:
                resp = requests.post(self.url, headers=HEADERS, json=self.data, timeout=15)
            resp.raise_for_status()
            self.finished.emit(resp.json())
        except Exception as e:
            self.error.emit(str(e))


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
        send_btn.setEnabled(bool(phone))
        send_btn.clicked.connect(lambda: self.send_reminder())
        layout.addWidget(send_btn)

    def send_reminder(self):
        phone = self.user_data.get('phone_number', '')
        username = self.user_data.get('username', '')
        if phone:
            send_whatsapp(phone, username, self.user_data['id'])
            QMessageBox.information(self, "Sent", f"Reminder opened for {username}")


# ── Helper: Send WhatsApp ────────────────────────────────────────
def send_whatsapp(phone, username, user_id):
    """Open WhatsApp web with pre-filled message and record on server."""
    template = load_message_template()
    message = template.replace('{username}', username)
    phone_clean = phone.replace('+', '')
    url = f"https://wa.me/{phone_clean}?text={urllib.parse.quote(message)}"
    webbrowser.open(url)

    # Record reminder on server
    try:
        requests.post(f"{SERVER_URL}/admin/api/send_reminder/{user_id}",
                      headers=HEADERS, timeout=10)
    except Exception:
        pass


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

        self.auto_check = QCheckBox("Auto-send @1PM")
        self.auto_check.setChecked(AUTO_SEND)
        self.auto_check.setStyleSheet(f"font-size: 12px; font-weight: 600;")
        header_layout.addWidget(self.auto_check)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("primaryBtn")
        refresh_btn.clicked.connect(self.load_users)
        header_layout.addWidget(refresh_btn)

        main_layout.addLayout(header_layout)

        # ── Search ──
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search users...")
        self.search_box.textChanged.connect(self.filter_table)
        main_layout.addWidget(self.search_box)

        # ── Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "Username", "Last Exec", "Off Time",
            "Go/No-Go", "Stroop", "Emoji", "Phone", "Last Message", "Action"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)
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

        show_action = QAction("Show Admin", self)
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
        self.statusBar().showMessage("🔔 Checking for pending users...")

        worker = ApiWorker(f"{SERVER_URL}/admin/api/check_pending")
        worker.finished.connect(self._on_pending_received)
        worker.error.connect(lambda e: self.statusBar().showMessage(f"❌ Error: {e}"))
        self.workers.append(worker)
        worker.start()

    def _on_pending_received(self, pending_users):
        count = 0
        for user in pending_users:
            phone = user.get('phone_number', '')
            if phone:
                send_whatsapp(phone, user['username'], user['id'])
                count += 1

        msg = f"✅ Auto-reminders sent to {count} user(s)" if count else "✅ All users have completed today's test"
        self.statusBar().showMessage(msg)
        self.tray_icon.showMessage("CogStim Reminder", msg, QSystemTrayIcon.MessageIcon.Information, 5000)
        self.load_users()

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
            send_btn.setEnabled(bool(u.get('phone_number')))
            uid, uname, uphone = u['id'], u['username'], u.get('phone_number', '')
            send_btn.clicked.connect(lambda checked, uid=uid, uname=uname, uphone=uphone: self._send_clicked(uid, uname, uphone))
            self.table.setCellWidget(row, 9, send_btn)

    def _send_clicked(self, uid, uname, uphone):
        if uphone:
            send_whatsapp(uphone, uname, uid)
            self.statusBar().showMessage(f"📲 Reminder opened for {uname}")
            QTimer.singleShot(2000, self.load_users)

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
        self.tray_icon.hide()
        QApplication.quit()


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
