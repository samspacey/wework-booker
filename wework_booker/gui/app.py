"""Main GUI application for WeWork Booker."""

import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QProgressBar,
    QTextEdit,
    QPushButton,
    QGroupBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..config import Config
from .booking_thread import BookingThread


class BookingApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.booking_thread = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("WeWork Desk Booker")
        self.setFixedSize(400, 520)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Credentials section
        creds_group = QGroupBox("Credentials")
        creds_layout = QVBoxLayout(creds_group)

        # Email
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        email_label.setFixedWidth(70)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your.email@company.com")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        creds_layout.addLayout(email_layout)

        # Password
        pass_layout = QHBoxLayout()
        pass_label = QLabel("Password:")
        pass_label.setFixedWidth(70)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter your password")
        pass_layout.addWidget(pass_label)
        pass_layout.addWidget(self.password_input)
        creds_layout.addLayout(pass_layout)

        # Show password checkbox
        self.show_password = QCheckBox("Show password")
        self.show_password.toggled.connect(self.toggle_password_visibility)
        creds_layout.addWidget(self.show_password)

        layout.addWidget(creds_group)

        # Location display
        location_layout = QHBoxLayout()
        location_label = QLabel("Location:")
        location_label.setFixedWidth(70)
        self.location_display = QLabel("10 York Rd")
        self.location_display.setStyleSheet("color: #666; font-style: italic;")
        location_layout.addWidget(location_label)
        location_layout.addWidget(self.location_display)
        location_layout.addStretch()
        layout.addLayout(location_layout)

        # Booking days section
        days_group = QGroupBox("Booking Days")
        days_layout = QHBoxLayout(days_group)

        self.day_checkboxes = {}
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
            cb = QCheckBox(day)
            if day in ["Wed", "Thu"]:
                cb.setChecked(True)
            self.day_checkboxes[day] = cb
            days_layout.addWidget(cb)

        layout.addWidget(days_group)

        # Weeks ahead
        weeks_layout = QHBoxLayout()
        weeks_label = QLabel("Weeks Ahead:")
        self.weeks_spin = QSpinBox()
        self.weeks_spin.setRange(1, 4)
        self.weeks_spin.setValue(2)
        weeks_layout.addWidget(weeks_label)
        weeks_layout.addWidget(self.weeks_spin)
        weeks_layout.addStretch()
        layout.addLayout(weeks_layout)

        # Progress section
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)

        # Results section
        results_label = QLabel("Results:")
        layout.addWidget(results_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(100)
        self.results_text.setFont(QFont("Menlo", 11))
        layout.addWidget(self.results_text)

        # Start button
        self.start_button = QPushButton("Start Booking")
        self.start_button.setFixedHeight(40)
        self.start_button.clicked.connect(self.start_booking)
        layout.addWidget(self.start_button)

    def toggle_password_visibility(self, checked: bool):
        """Toggle password field visibility."""
        if checked:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

    def get_selected_days(self) -> list[str]:
        """Get list of selected booking days."""
        day_map = {
            "Mon": "monday",
            "Tue": "tuesday",
            "Wed": "wednesday",
            "Thu": "thursday",
            "Fri": "friday",
        }
        return [
            day_map[short]
            for short, cb in self.day_checkboxes.items()
            if cb.isChecked()
        ]

    def validate_inputs(self) -> bool:
        """Validate user inputs."""
        if not self.email_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter your email")
            return False

        if not self.password_input.text():
            QMessageBox.warning(self, "Validation Error", "Please enter your password")
            return False

        if not self.get_selected_days():
            QMessageBox.warning(
                self, "Validation Error", "Please select at least one booking day"
            )
            return False

        return True

    def set_ui_enabled(self, enabled: bool):
        """Enable or disable UI controls."""
        self.email_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.show_password.setEnabled(enabled)
        self.weeks_spin.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        for cb in self.day_checkboxes.values():
            cb.setEnabled(enabled)

    def start_booking(self):
        """Start the booking process."""
        if not self.validate_inputs():
            return

        # Create config from UI values
        config = Config(
            email=self.email_input.text().strip(),
            password=self.password_input.text(),
            location="10 York Rd",
            booking_days=self.get_selected_days(),
            headless=True,
            weeks_ahead=self.weeks_spin.value(),
            debug=False,
        )

        # Reset UI
        self.progress_bar.setValue(0)
        self.results_text.clear()
        self.set_ui_enabled(False)
        self.start_button.setText("Booking...")

        # Create and start thread
        self.booking_thread = BookingThread(config)
        self.booking_thread.status_update.connect(self.on_status_update)
        self.booking_thread.progress_update.connect(self.on_progress_update)
        self.booking_thread.booking_result.connect(self.on_booking_result)
        self.booking_thread.finished_booking.connect(self.on_booking_finished)
        self.booking_thread.error_occurred.connect(self.on_error)
        self.booking_thread.start()

    def on_status_update(self, message: str):
        """Handle status update from booking thread."""
        self.status_label.setText(message)

    def on_progress_update(self, progress: int):
        """Handle progress update from booking thread."""
        self.progress_bar.setValue(progress)

    def on_booking_result(self, date_str: str, success: bool):
        """Handle individual booking result."""
        status = "Successful" if success else "Failed"
        color = "green" if success else "red"
        self.results_text.append(f'<span style="color: {color}">{date_str}: {status}</span>')

    def on_error(self, error_message: str):
        """Handle error from booking thread."""
        self.status_label.setText(f"Error: {error_message}")
        self.status_label.setStyleSheet("color: red;")

    def on_booking_finished(self, results: dict):
        """Handle booking completion."""
        self.set_ui_enabled(True)
        self.start_button.setText("Start Booking")

        if results:
            success_count = sum(1 for v in results.values() if v)
            total_count = len(results)
            self.status_label.setText(f"Complete: {success_count}/{total_count} successful")
            self.status_label.setStyleSheet("color: green;" if success_count == total_count else "color: orange;")
        else:
            self.status_label.setStyleSheet("color: red;")


def run():
    """Run the GUI application."""
    app = QApplication(sys.argv)
    window = BookingApp()
    window.show()
    sys.exit(app.exec())
