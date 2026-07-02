"""
CogStim Desktop Admin App
- System tray support (minimize to taskbar)
- Auto-send WhatsApp reminders at a customizable time daily (via Selenium automation)
- User management table with detail view
"""

import sys
import os
import json
import csv
import logging
import requests
from datetime import datetime, timedelta

from whatsapp_sender import WhatsAppSender

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QSystemTrayIcon, QMenu, QDialog, QScrollArea, QFrame, QMessageBox,
    QSplitter, QStatusBar, QLineEdit, QGroupBox, QGridLayout, QCheckBox,
    QProgressDialog, QTextEdit, QSpinBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal, QObject
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

def save_config(cfg):
    """Persist the current configuration back to config.json."""
    config_path = os.path.join(BASE_DIR, 'config.json')
    with open(config_path, 'w') as f:
        json.dump(cfg, f, indent=4)

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
    QPushButton#sendBtn {{ background: #1a8a4a; color: white; border: none; }}
    QPushButton#sendBtn:hover {{ background: #14693a; }}
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
    QTextEdit#logOutput {{
        background: #111320; color: #c8d0e0; font-family: 'Cascadia Code', 'Consolas', monospace;
        font-size: 11px; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;
        padding: 8px; selection-background-color: rgba(108,140,255,0.25);
    }}
"""


# ── Qt Log Handler ───────────────────────────────────────────────
class LogSignalBridge(QObject):
    """Bridge to forward log records from any thread to the GUI thread."""
    new_record = pyqtSignal(str)


class QtLogHandler(logging.Handler):
    """A logging.Handler that emits a Qt signal for every log record."""
    def __init__(self):
        super().__init__()
        self.bridge = LogSignalBridge()
        self.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)-7s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))

    def emit(self, record):
        try:
            msg = self.format(record)
            self.bridge.new_record.emit(msg)
        except Exception:
            pass


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
    progress = pyqtSignal(int, int, str, bool, int)  # current, total, info, success, user_id
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
            uid = user.get('id', 0)
            if not phone:
                failed += 1
                self.progress.emit(i + 1, total, f"{user['username']}: no phone", False, uid)
                continue
            msg = self.message_template.replace('{username}', user['username'])
            result = wa_sender.send_message(phone, msg)
            if result['success']:
                sent += 1
                self.progress.emit(i + 1, total, f"✅ {user['username']}", True, uid)
                # Record on server
                try:
                    requests.post(
                        f"{SERVER_URL}/admin/api/send_reminder/{uid}",
                        headers=HEADERS, timeout=10)
                except Exception:
                    pass
            else:
                failed += 1
                self.progress.emit(
                    i + 1, total,
                    f"❌ {user['username']}: {result['error']}", False, uid)
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
        self._annotation = None
        self._plot_data = None  # (x_vals, y_vals, labels, y_suffix)
        self.mpl_connect('motion_notify_event', self._on_hover)

    def _style_ax(self):
        self.ax.set_facecolor('#1a1d2e')
        self.ax.tick_params(colors='#555a70', labelsize=8)
        self.ax.spines['bottom'].set_color('#333')
        self.ax.spines['left'].set_color('#333')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.set_title(self.title, color='#b0b8d1', fontsize=10, fontweight='bold', pad=8)

    def wheelEvent(self, event):
        """Pass wheel events to parent scroll area instead of consuming them."""
        event.ignore()

    def _on_hover(self, event):
        """Show annotation on nearest data point when hovering."""
        if not self._plot_data or event.inaxes != self.ax:
            if self._annotation and self._annotation.get_visible():
                self._annotation.set_visible(False)
                self.draw_idle()
            return

        x_vals, y_vals, labels, y_suffix = self._plot_data
        if not x_vals:
            return

        # Find nearest point
        min_dist = float('inf')
        nearest_idx = 0
        for i, (xv, yv) in enumerate(zip(x_vals, y_vals)):
            dist = abs(event.xdata - xv)
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i

        # Only show if reasonably close
        x_range = max(x_vals) - min(x_vals) if len(x_vals) > 1 else 1
        if min_dist > x_range * 0.15:
            if self._annotation and self._annotation.get_visible():
                self._annotation.set_visible(False)
                self.draw_idle()
            return

        xp, yp = x_vals[nearest_idx], y_vals[nearest_idx]
        lbl = labels[nearest_idx] if nearest_idx < len(labels) else ''
        val_text = f"{int(yp)}{y_suffix}" if yp == int(yp) else f"{yp:.1f}{y_suffix}"
        text = f"{lbl}\n{val_text}"

        # Position tooltip: flip horizontally near right edge, vertically near top
        x_min, x_max = self.ax.get_xlim()
        y_min, y_max = self.ax.get_ylim()
        near_right = (xp - x_min) / (x_max - x_min) > 0.75 if x_max != x_min else False
        near_top = (yp - y_min) / (y_max - y_min) > 0.7 if y_max != y_min else False
        x_off = -80 if near_right else 10
        y_off = -30 if near_top else 14
        offset = (x_off, y_off)

        if self._annotation is None:
            self._annotation = self.ax.annotate(
                text, xy=(xp, yp), xytext=offset,
                textcoords='offset points',
                fontsize=8, color='white', clip_on=False,
                bbox=dict(boxstyle='round,pad=0.4', fc='#333850', ec=self.color, alpha=0.95),
                arrowprops=dict(arrowstyle='->', color=self.color, lw=1.2))
        else:
            self._annotation.xy = (xp, yp)
            self._annotation.set_text(text)
            self._annotation.xyann = offset
            self._annotation.set_visible(True)
        self.draw_idle()

    def update_data(self, labels, scores, y_suffix=''):
        self.ax.clear()
        self._style_ax()
        self._annotation = None
        self._plot_data = None
        if scores:
            # Filter out None values for plotting
            valid = [(i, s) for i, s in enumerate(scores) if s is not None]
            if valid:
                x_vals, y_vals = zip(*valid)
                valid_labels = [labels[i] for i in x_vals] if labels else []
                self._plot_data = (list(x_vals), list(y_vals), valid_labels, y_suffix)
                self.ax.fill_between(x_vals, y_vals, alpha=0.15, color=self.color)
                self.ax.plot(x_vals, y_vals, color=self.color, linewidth=2, marker='o', markersize=4)
                all_x = range(len(scores))
                self.ax.set_xticks(list(all_x))
                self.ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=7)
                if y_suffix:
                    from matplotlib.ticker import FuncFormatter
                    self.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{int(v)}{y_suffix}'))
            else:
                self.ax.text(0.5, 0.5, 'No data', ha='center', va='center', color='#555a70', transform=self.ax.transAxes)
        else:
            self.ax.text(0.5, 0.5, 'No data', ha='center', va='center', color='#555a70', transform=self.ax.transAxes)
        self.fig.tight_layout(rect=[0, 0, 0.95, 0.92])  # Extra room for tooltip (top + right)
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


# ── Admin Notes Dialog ───────────────────────────────────────────
class NotesDialog(QDialog):
    """Dialog for viewing/editing the admin notes of a user."""
    def __init__(self, username, notes, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Admin Notes — {username}")
        self.setMinimumSize(440, 340)
        self.result_notes = None
        self.setup_ui(username, notes)

    def setup_ui(self, username, notes):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 28, 28, 28)

        header = QLabel(f"🗒️ Notes for {username}")
        header.setFont(QFont('Segoe UI', 16, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(header)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Write admin notes about this user...")
        self.notes_edit.setPlainText(notes or '')
        self.notes_edit.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(255,255,255,0.04); border: 1.5px solid rgba(255,255,255,0.1);
                border-radius: 8px; padding: 10px; color: {TEXT_PRIMARY}; font-size: 12px;
            }}
            QTextEdit:focus {{ border-color: {ACCENT}; }}
        """)
        layout.addWidget(self.notes_edit, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("💾 Save Notes")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumHeight(40)
        save_btn.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
        save_btn.clicked.connect(self.on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def on_save(self):
        self.result_notes = self.notes_edit.toPlainText().strip()
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
            ("Go/No-Go", ORANGE, sh.get('go_no_go', {})),
            ("Stroop", ACCENT, sh.get('stroop', {})),
            ("Emoji", GREEN, sh.get('emoji', {})),
        ]
        for name, color, data in charts_config:
            # Score chart
            score_chart = ScoreChart(f"{name} — Score", color)
            score_chart.update_data(data.get('labels', []), data.get('scores', []))
            score_chart.setMinimumHeight(180)
            chart_layout.addWidget(score_chart)

            # Latency chart
            rt_data = data.get('reaction_time', [])
            if any(v and v > 0 for v in rt_data):
                latency_chart = ScoreChart(f"{name} — Latency", color)
                latency_chart.update_data(data.get('labels', []), rt_data, y_suffix='ms')
                latency_chart.setMinimumHeight(180)
                chart_layout.addWidget(latency_chart)

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


# ── Send Now Dialog ──────────────────────────────────────────────
class SendNowDialog(QDialog):
    """Dialog to select which users to send a WhatsApp reminder to right now."""

    def __init__(self, users, parent=None):
        super().__init__(parent)
        self.users = users
        self.selected_users = []
        self.setWindowTitle("Send Reminder Now")
        self.setMinimumSize(440, 500)
        self._checkboxes = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("📨 Select Recipients")
        title.setFont(QFont('Segoe UI', 15, QFont.Weight.Bold))
        layout.addWidget(title)

        hint = QLabel("Choose which users to send the reminder to:")
        hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(hint)

        # Select all / none buttons
        sel_row = QHBoxLayout()
        sel_all = QPushButton("Select All")
        sel_all.setFixedHeight(28)
        sel_all.setStyleSheet("font-size: 11px; padding: 2px 12px;")
        sel_all.clicked.connect(lambda: self._set_all(True))
        sel_none = QPushButton("Clear All")
        sel_none.setFixedHeight(28)
        sel_none.setStyleSheet("font-size: 11px; padding: 2px 12px;")
        sel_none.clicked.connect(lambda: self._set_all(False))
        sel_row.addWidget(sel_all)
        sel_row.addWidget(sel_none)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        # Scrollable checkbox list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        cb_layout = QVBoxLayout(container)
        cb_layout.setSpacing(6)
        cb_layout.setContentsMargins(4, 4, 4, 4)

        for u in self.users:
            phone = u.get('phone_number', '')
            label = f"{u['username']}  ({phone})"
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setFont(QFont('Segoe UI', 11))
            cb_layout.addWidget(cb)
            self._checkboxes.append((cb, u))

        cb_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        send_btn = QPushButton("📨 Send to Selected")
        send_btn.setObjectName("sendBtn")
        send_btn.setMinimumHeight(40)
        send_btn.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
        send_btn.clicked.connect(self._on_send)
        btn_row.addWidget(send_btn)
        layout.addLayout(btn_row)

    def _set_all(self, checked):
        for cb, _ in self._checkboxes:
            cb.setChecked(checked)

    def _on_send(self):
        self.selected_users = [u for cb, u in self._checkboxes if cb.isChecked()]
        if not self.selected_users:
            QMessageBox.warning(self, "No Selection", "Select at least one user.")
            return
        self.accept()


# ── Main Window ──────────────────────────────────────────────────
class AdminWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CogStim Admin — Desktop")
        self.setMinimumSize(1250, 650)
        self.workers = []
        self.users_data = []
        self.reminder_sent_today = False
        self.msg_failures = {}  # {user_id: error_string} – tracks send failures

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
        self.wa_disconnect_btn.setStyleSheet(f"background: {RED}; color: white; border: none; border-radius: 8px;")
        self.wa_disconnect_btn.clicked.connect(self.disconnect_whatsapp)
        self.wa_disconnect_btn.setVisible(False)
        header_layout.addWidget(self.wa_disconnect_btn)

        self.auto_check = QCheckBox("Auto-send")
        self.auto_check.setChecked(AUTO_SEND)
        self.auto_check.setStyleSheet(f"font-size: 12px; font-weight: 600;")
        self.auto_check.toggled.connect(self._on_reminder_settings_changed)
        header_layout.addWidget(self.auto_check)

        at_label = QLabel("at")
        at_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 600;")
        header_layout.addWidget(at_label)

        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 23)
        self.hour_spin.setValue(REMINDER_HOUR)
        self.hour_spin.setFixedWidth(52)
        self.hour_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hour_spin.setStyleSheet(f"""
            QSpinBox {{
                background: rgba(255,255,255,0.04); border: 1.5px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 4px; color: {TEXT_PRIMARY}; font-size: 12px; font-weight: 700;
            }}
            QSpinBox:focus {{ border-color: {ACCENT}; }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: 14px; }}
        """)
        self.hour_spin.valueChanged.connect(self._on_reminder_settings_changed)
        header_layout.addWidget(self.hour_spin)

        colon_label = QLabel(":")
        colon_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 700;")
        header_layout.addWidget(colon_label)

        self.minute_spin = QSpinBox()
        self.minute_spin.setRange(0, 59)
        self.minute_spin.setValue(REMINDER_MINUTE)
        self.minute_spin.setFixedWidth(52)
        self.minute_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minute_spin.setStyleSheet(self.hour_spin.styleSheet())
        self.minute_spin.valueChanged.connect(self._on_reminder_settings_changed)
        header_layout.addWidget(self.minute_spin)

        self.send_now_btn = QPushButton("📨 Send Now")
        self.send_now_btn.setObjectName("sendBtn")
        self.send_now_btn.setToolTip("Choose recipients and send reminder now")
        self.send_now_btn.clicked.connect(self.open_send_now_dialog)
        header_layout.addWidget(self.send_now_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("primaryBtn")
        refresh_btn.clicked.connect(self.load_users)
        header_layout.addWidget(refresh_btn)

        add_user_btn = QPushButton("➕ Add Account")
        add_user_btn.setObjectName("primaryBtn")
        add_user_btn.clicked.connect(self.add_account)
        header_layout.addWidget(add_user_btn)

        export_btn = QPushButton("💾 Export CSV")
        export_btn.setObjectName("primaryBtn")
        export_btn.clicked.connect(self.export_csv)
        header_layout.addWidget(export_btn)

        main_layout.addLayout(header_layout)

        # ── Search ──
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search users...")
        self.search_box.textChanged.connect(self.filter_table)
        main_layout.addWidget(self.search_box)

        # ── Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            "ID", "Username", "Status", "Last Exec", "Off Time",
            "Go/No-Go", "Stroop", "Emoji", "Phone", "Admin Notes",
            "Last Message", "Msg Status", "Actions"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(self.table.styleSheet() + "alternate-background-color: rgba(255,255,255,0.02);")
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)

        # ── Log Output Panel (resizable via splitter) ──
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 4, 0, 0)
        log_layout.setSpacing(4)

        log_header_layout = QHBoxLayout()
        log_label = QLabel("📋 Log Output")
        log_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700;")
        log_header_layout.addWidget(log_label)
        log_header_layout.addStretch()

        clear_log_btn = QPushButton("Clear")
        clear_log_btn.setFixedHeight(24)
        clear_log_btn.setStyleSheet(f"font-size: 10px; padding: 2px 10px;")
        clear_log_btn.clicked.connect(lambda: self.log_output.clear())
        log_header_layout.addWidget(clear_log_btn)
        log_layout.addLayout(log_header_layout)

        self.log_output = QTextEdit()
        self.log_output.setObjectName("logOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("WhatsApp automation logs will appear here...")
        log_layout.addWidget(self.log_output)

        # ── Splitter: Table ↕ Log ──
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.table)
        splitter.addWidget(log_container)
        splitter.setStretchFactor(0, 3)   # table gets 75%
        splitter.setStretchFactor(1, 1)   # log gets 25%
        splitter.setHandleWidth(6)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: rgba(255,255,255,0.06);
                border-radius: 3px;
                margin: 2px 40px;
            }}
            QSplitter::handle:hover {{
                background: {ACCENT};
            }}
        """)
        main_layout.addWidget(splitter, 1)

        # ── Attach log handler ──
        self._qt_log_handler = QtLogHandler()
        self._qt_log_handler.bridge.new_record.connect(self._append_log)
        wa_logger = logging.getLogger("WhatsAppSender")
        wa_logger.addHandler(self._qt_log_handler)

        # ── Status bar ──
        self.statusBar().showMessage("Ready")
        self.status_label = QLabel("")
        self.statusBar().addPermanentWidget(self.status_label)

    def _append_log(self, text: str):
        """Append a formatted log line to the output panel."""
        # Color-code by level
        if "ERROR" in text:
            color = RED
        elif "WARNING" in text:
            color = ORANGE
        elif "✅" in text:
            color = GREEN
        else:
            color = "#c8d0e0"
        self.log_output.append(f'<span style="color:{color}">{text}</span>')
        # Auto-scroll to bottom
        sb = self.log_output.verticalScrollBar()
        sb.setValue(sb.maximum())

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
        target_hour = self.hour_spin.value()
        target_minute = self.minute_spin.value()
        if (now.hour == target_hour and now.minute == target_minute
                and not self.reminder_sent_today and self.auto_check.isChecked()):
            self.reminder_sent_today = True
            self.auto_send_reminders()

    def reset_daily(self):
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            self.reminder_sent_today = False

    def _on_reminder_settings_changed(self):
        """Persist reminder settings to config.json when user changes them."""
        CONFIG['auto_send_enabled'] = self.auto_check.isChecked()
        CONFIG['reminder_hour'] = self.hour_spin.value()
        CONFIG['reminder_minute'] = self.minute_spin.value()
        save_config(CONFIG)
        time_str = f"{self.hour_spin.value():02d}:{self.minute_spin.value():02d}"
        state = "enabled" if self.auto_check.isChecked() else "disabled"
        self.statusBar().showMessage(f"⏰ Auto-reminder {state} at {time_str}")

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

    def open_send_now_dialog(self):
        """Open dialog to select recipients and send reminders immediately."""
        if not wa_sender.is_ready():
            QMessageBox.warning(self, "Not Connected",
                                "Connect WhatsApp first using the 🟢 Connect WA button.")
            return
        self.statusBar().showMessage("Fetching user list...")
        worker = ApiWorker(f"{SERVER_URL}/admin/api/users")
        worker.finished.connect(self._on_users_for_send_now)
        worker.error.connect(lambda e: self.statusBar().showMessage(f"❌ Error: {e}"))
        self.workers.append(worker)
        worker.start()

    def _on_users_for_send_now(self, all_users):
        users_with_phone = [u for u in all_users if u.get('phone_number')]
        if not users_with_phone:
            QMessageBox.information(self, "No Recipients", "No users with phone numbers found.")
            return
        dialog = SendNowDialog(users_with_phone, self)
        dialog.setStyleSheet(STYLESHEET)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_users:
            template = load_message_template()
            self._batch_worker = WaBatchWorker(dialog.selected_users, template)
            self._batch_worker.progress.connect(self._on_batch_progress)
            self._batch_worker.done.connect(self._on_batch_done)
            self._batch_worker.start()
            self.statusBar().showMessage(f"📲 Sending to {len(dialog.selected_users)} users...")

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
        self.table.resizeColumnsToContents()  # Auto-fit then allow manual resize
        self.statusBar().showMessage(f"✅ Loaded {len(data)} users")
        self.status_label.setText(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")

    def _format_score_latency(self, score, latency):
        """Format a score cell as 'score (latency ms)' or just '—'."""
        if score is None:
            return '—'
        if latency is not None:
            return f"{score}  ({latency}ms)"
        return str(score)

    @staticmethod
    def _utc_to_local(utc_str):
        """Convert a UTC datetime string (from server) to local time string."""
        if not utc_str:
            return ''
        try:
            utc_dt = datetime.strptime(utc_str, '%Y-%m-%d %H:%M')
            # Convert UTC -> local by adding the local UTC offset
            import time as _time
            local_offset = timedelta(seconds=-_time.timezone if _time.daylight == 0 else -_time.altzone)
            local_dt = utc_dt + local_offset
            return local_dt.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            return utc_str  # Return as-is if parsing fails

    def populate_table(self, data):
        self.table.setRowCount(len(data))
        for row, u in enumerate(data):
            self.table.setRowHeight(row, 40)

            # Convert UTC timestamps to local time
            last_exec_local = self._utc_to_local(u.get('last_exec') or '')
            last_reminder_local = self._utc_to_local(u.get('last_reminder_sent') or '')

            # Test completion status — compare local date
            today_done = False
            if last_exec_local:
                try:
                    last_exec_date = datetime.strptime(last_exec_local[:10], '%Y-%m-%d').date()
                    today_done = last_exec_date == datetime.now().date()
                except (ValueError, IndexError):
                    pass
            status_text = "✅ Done" if today_done else "⏳ Not Done"
            status_color = GREEN if today_done else ORANGE

            # Score + latency combined strings
            go_nogo_str = self._format_score_latency(
                u.get('score_go_nogo'), u.get('latency_go_nogo'))
            stroop_str = self._format_score_latency(
                u.get('score_stroop'), u.get('latency_stroop'))
            emoji_str = self._format_score_latency(
                u.get('score_emoji'), u.get('latency_emoji'))

            # Message failure status
            uid = u['id']
            if uid in self.msg_failures:
                msg_status_text = "❌ Failed"
                msg_status_color = RED
            else:
                msg_status_text = "—"
                msg_status_color = TEXT_SECONDARY

            notes = u.get('admin_notes') or ''
            notes_display = (notes[:30] + '…') if len(notes) > 30 else notes or '—'

            items = [
                (str(u['id']), None),
                (u['username'], None),
                (status_text, status_color),
                (last_exec_local or '—', None),
                (u.get('off_time', 'Never'), None),
                (go_nogo_str, None),
                (stroop_str, None),
                (emoji_str, None),
                (u.get('phone_number') or '—', None),
                (notes_display, TEXT_SECONDARY),
                (last_reminder_local or '—', None),
                (msg_status_text, msg_status_color),
            ]
            for col, (text, color) in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 1:  # Username column - make clickable looking
                    item.setForeground(QColor(ACCENT))
                    item.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
                elif color:  # Status / Msg Status columns
                    item.setForeground(QColor(color))
                    item.setFont(QFont('Segoe UI', 9, QFont.Weight.Bold))
                if col == 9:  # Admin Notes column
                    item.setToolTip(f"{notes}\n\n(Double-click to edit)" if notes
                                    else "Double-click to add notes")
                self.table.setItem(row, col, item)

            uname, uphone = u['username'], u.get('phone_number', '')

            # Actions column — Send | Edit | Delete in one cell
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            send_btn = QPushButton("📨")
            send_btn.setFixedHeight(26)
            send_btn.setToolTip("Send Reminder")
            send_btn.setStyleSheet(f"background: #1a8a4a; border: none; border-radius: 6px; padding: 4px 8px; font-size: 12px;")
            send_btn.setEnabled(bool(u.get('phone_number')))
            send_btn.clicked.connect(lambda checked, uid=uid, uname=uname, uphone=uphone: self._send_clicked(uid, uname, uphone))
            actions_layout.addWidget(send_btn)

            edit_btn = QPushButton("📝")
            edit_btn.setFixedHeight(26)
            edit_btn.setToolTip("Edit Account")
            edit_btn.setStyleSheet(f"background: {ACCENT}; border: none; border-radius: 6px; padding: 4px 8px; font-size: 12px;")
            edit_btn.clicked.connect(lambda checked, _u=u: self.edit_account(_u))
            actions_layout.addWidget(edit_btn)

            del_btn = QPushButton("🗑️")
            del_btn.setFixedHeight(26)
            del_btn.setToolTip("Delete Account")
            del_btn.setStyleSheet(f"background: {RED}; border: none; border-radius: 6px; padding: 4px 8px; font-size: 12px;")
            del_btn.clicked.connect(lambda checked, _uid=uid, _uname=uname: self.delete_account(_uid, _uname))
            actions_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 12, actions_widget)

    def export_csv(self):
        """Export all historical score data to a CSV file."""
        default_name = f"cogstim_scores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export All Scores to CSV", default_name,
            "CSV Files (*.csv);;All Files (*)")
        if not filepath:
            return

        self.statusBar().showMessage("Fetching all score data for export...")
        worker = ApiWorker(f"{SERVER_URL}/admin/api/scores/export")
        worker.finished.connect(lambda data: self._write_csv(filepath, data))
        worker.error.connect(lambda e: QMessageBox.warning(
            self, "Export Failed", f"Could not fetch data:\n{e}"))
        self.workers.append(worker)
        worker.start()

    def _write_csv(self, filepath, data):
        """Write fetched score data to CSV."""
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Username", "Phone", "Test Type", "Score",
                    "Accuracy (%)", "Reaction Time (ms)", "Timestamp"
                ])
                for s in data:
                    writer.writerow([
                        s.get('username', ''),
                        s.get('phone_number', ''),
                        s.get('test_type', ''),
                        s.get('score', ''),
                        s.get('accuracy') if s.get('accuracy') is not None else '',
                        s.get('reaction_time') if s.get('reaction_time') is not None else '',
                        s.get('timestamp', ''),
                    ])
            self.statusBar().showMessage(
                f"✅ Exported {len(data)} score records to {os.path.basename(filepath)}")
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Could not save CSV:\n{e}")

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
            # Clear any previous failure
            self.msg_failures.pop(uid, None)
            try:
                requests.post(f"{SERVER_URL}/admin/api/send_reminder/{uid}",
                              headers=HEADERS, timeout=10)
            except Exception:
                pass
            self.statusBar().showMessage(f"✅ Reminder sent to {uname}")
            QTimer.singleShot(2000, self.load_users)
        else:
            self.msg_failures[uid] = result.get('error', 'Unknown error')
            self.statusBar().showMessage(f"❌ Failed for {uname}: {result['error']}")
            QTimer.singleShot(500, self.load_users)  # Refresh to show failure indicator

    def filter_table(self, text):
        text = text.lower()
        filtered = [u for u in self.users_data if text in u['username'].lower() or text in (u.get('phone_number') or '')]
        self.populate_table(filtered)

    def on_row_double_clicked(self, row, col):
        # Column 9 = Admin Notes — double-click to edit
        if col == 9:
            uid_item = self.table.item(row, 0)
            if uid_item:
                uid = int(uid_item.text())
                user = next((u for u in self.users_data if u['id'] == uid), None)
                if user:
                    self.edit_notes(user)
            return

        # Column 11 = Msg Status — click to show failure detail
        if col == 11:
            uid_item = self.table.item(row, 0)
            if uid_item:
                uid = int(uid_item.text())
                if uid in self.msg_failures:
                    uname_item = self.table.item(row, 1)
                    uname = uname_item.text() if uname_item else str(uid)
                    QMessageBox.warning(
                        self, "Message Failure Detail",
                        f"Failed to send to <b>{uname}</b>:<br><br>"
                        f"<span style='color:{RED}'>{self.msg_failures[uid]}</span>")
            return

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

    def edit_notes(self, user):
        """Open the admin notes editor for a user and save changes to the server."""
        dialog = NotesDialog(user['username'], user.get('admin_notes') or '', self)
        dialog.setStyleSheet(STYLESHEET)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_notes is not None:
            uid = user['id']
            self.statusBar().showMessage(f"Saving notes for {user['username']}...")
            worker = ApiWorker(f"{SERVER_URL}/admin/api/users/{uid}/notes", 'PUT',
                               {'notes': dialog.result_notes})
            worker.finished.connect(self._on_notes_saved)
            worker.error.connect(self._on_account_error)
            self.workers.append(worker)
            worker.start()

    def _on_notes_saved(self, result):
        self.statusBar().showMessage(f"✅ {result.get('message', 'Notes updated')}")
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

    def _on_batch_progress(self, current, total, info, success, user_id):
        self.statusBar().showMessage(f"[{current}/{total}] {info}")
        if success:
            self.msg_failures.pop(user_id, None)
        else:
            # Extract error message from the info string after the colon
            err = info.split(': ', 1)[-1] if ': ' in info else info
            self.msg_failures[user_id] = err

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
