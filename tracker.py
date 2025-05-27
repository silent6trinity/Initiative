import sys
import random
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QScrollArea, QFrame, QSizePolicy, QGraphicsOpacityEffect, QInputDialog
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QFont

TEST_CHARACTERS = ["Boblin", "Meat", "Branch", "Huff", "Timmy"]

class SharedGameState:
    def __init__(self, characters):
        self.characters = characters
        self.dead_flags = [False] * len(characters)
        self.turn_index = 0
        self.subscribers = []

    def subscribe(self, window):
        self.subscribers.append(window)

    def notify(self):
        for sub in self.subscribers:
            sub.render_cards()

    def mark_dead(self, index):
        self.dead_flags[index] = True
        if self.turn_index == index:
            self.next_turn()
        self.notify()

    def next_turn(self):
        original_index = self.turn_index
        while True:
            self.turn_index = (self.turn_index + 1) % len(self.characters)
            if not self.dead_flags[self.turn_index] or self.turn_index == original_index:
                break
        self.notify()

    def prev_turn(self):
        original_index = self.turn_index
        while True:
            self.turn_index = (self.turn_index - 1) % len(self.characters)
            if not self.dead_flags[self.turn_index] or self.turn_index == original_index:
                break
        self.notify()

class AnimatedCard(QFrame):
    def __init__(self, name, index, is_current, is_dead, on_death_callback):
        super().__init__()
        self.setGraphicsEffect(QGraphicsOpacityEffect(self))
        self.opacity_effect = self.graphicsEffect()

        self.setFixedHeight(70)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(self.base_style(is_current, is_dead))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        label = QLabel(f"{name} — DEAD" if is_dead else name)
        label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {'#ff6666' if is_dead else 'white'};")
        layout.addWidget(label, stretch=1)

        turn_label = QLabel("CURRENT TURN")
        turn_label.setFont(QFont("Segoe UI", 10, italic=True))
        turn_label.setStyleSheet("color: #a8d8ff;")
        turn_label.setVisible(is_current and not is_dead)
        layout.addWidget(turn_label)

        if not is_dead:
            kill_btn = QPushButton("💀")
            kill_btn.setFixedSize(30, 30)
            kill_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #ff4444;
                    border: none;
                    font-size: 18px;
                }
                QPushButton:hover {
                    color: #ff8888;
                }
            """)
            kill_btn.clicked.connect(lambda: on_death_callback(index))
            layout.addWidget(kill_btn)

    def base_style(self, active, dead):
        if dead:
            return "background-color: #550000; border: 2px solid #993333; border-radius: 12px;"
        return f"""
            background-color: {'#304050' if active else '#1e1e1e'};
            border: 2px solid {'#88ccff' if active else '#333'};
            border-radius: 12px;
        """

class TurnTracker(QWidget):
    def __init__(self, state: SharedGameState):
        super().__init__()
        self.setWindowTitle("🧭 Turn Tracker")
        self.setGeometry(400, 200, 420, 600)
        self.setStyleSheet("background-color: #121212; color: #ffffff;")
        self.state = state
        self.state.subscribe(self)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

        title = QLabel("Initiative Order")
        title.setFont(QFont("Georgia", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #ffffff;")
        self.layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none;")
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(12)
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)

        self.cards = []

        btns = QHBoxLayout()
        self.prev_btn = QPushButton("← Back")
        self.prev_btn.clicked.connect(self.state.prev_turn)
        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self.state.next_turn)
        for btn in (self.prev_btn, self.next_btn):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2e2e2e;
                    color: white;
                    padding: 10px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #444444;
                }
            """)
            btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            btns.addWidget(btn)
        self.layout.addLayout(btns)

        self.render_cards()

    def render_cards(self):
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.itemAt(i).widget().deleteLater()
        self.cards.clear()

        for i, (name, _) in enumerate(self.state.characters):
            is_current = (i == self.state.turn_index and not self.state.dead_flags[i])
            card = AnimatedCard(name, i, is_current, self.state.dead_flags[i], self.state.mark_dead)
            self.scroll_layout.addWidget(card)
            self.cards.append(card)

def get_characters(test_mode):
    if test_mode:
        return sorted([(name, random.randint(1, 20)) for name in TEST_CHARACTERS], key=lambda x: x[1], reverse=True)
    characters = []
    while True:
        name, ok = QInputDialog.getText(None, "Character Name", "Enter character name:")
        if not ok or not name:
            break
        init, ok = QInputDialog.getInt(None, f"Initiative for {name}", "Enter initiative:")
        if ok:
            characters.append((name, init))
    characters.sort(key=lambda x: x[1], reverse=True)
    return characters

def run_app(test_mode=False):
    app = QApplication(sys.argv)
    characters = get_characters(test_mode)
    state = SharedGameState(characters)

    tracker1 = TurnTracker(state)
    tracker1.show()

    tracker2 = TurnTracker(state)
    tracker2.move(tracker1.x() + tracker1.width() + 50, tracker1.y())
    tracker2.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    run_app(test_mode="-test" in sys.argv)
