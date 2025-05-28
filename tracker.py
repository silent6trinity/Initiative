import sys
import random
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QInputDialog, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QTimer

from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QGraphicsOpacityEffect


TEST_CHARACTERS = ["Boblin", "Meat", "Branch", "Huff", "Timmy"]

class TrackerState:
    def __init__(self, characters):
        self.characters = characters
        self.dead_flags = [False] * len(characters)
        self.turn_index = 0
        self.subscribers = []

    def subscribe(self, tracker_view):
        self.subscribers.append(tracker_view)

    def notify_all(self):
        for view in self.subscribers:
            view.refresh()

    def advance_turn(self, delta):
        original_index = self.turn_index
        n = len(self.characters)
        for i in range(1, n+1):
            next_index = (self.turn_index + delta*i) % n
            if not self.dead_flags[next_index]:
                self.turn_index = next_index
                self.notify_all()
                return
        # fallback to original if everyone is dead
        self.turn_index = original_index
        self.notify_all()

    def toggle_dead(self, index):
        self.dead_flags[index] = not self.dead_flags[index]
        if index == self.turn_index and self.dead_flags[index]:
            self.advance_turn(1)
        else:
            self.notify_all()

class AnimatedCard(QFrame):
    def __init__(self, name, index, is_current=False, is_dead=False, on_dead_toggle=None):
        super().__init__()
        self.index = index
        self.on_dead_toggle = on_dead_toggle
        self.name = name
        self.setGraphicsEffect(QGraphicsOpacityEffect(self))
        self.opacity_effect = self.graphicsEffect()

        self.setFixedHeight(70)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        self.left = QVBoxLayout()
        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.turn_label = QLabel("CURRENT TURN")
        self.turn_label.setFont(QFont("Segoe UI", 10, italic=True))
        self.turn_label.setStyleSheet("color: #a8d8ff;")
        self.left.addWidget(self.name_label)
        self.left.addWidget(self.turn_label)
        layout.addLayout(self.left)

        self.skull_btn = QPushButton("💀")
        self.skull_btn.setFixedSize(36, 36)
        self.skull_btn.setStyleSheet("font-size: 18px; border-radius: 18px;")
        self.skull_btn.clicked.connect(self.mark_dead)
        layout.addWidget(self.skull_btn)

        self.refresh(is_current, is_dead)

    def mark_dead(self):
        if self.on_dead_toggle:
            self.on_dead_toggle(self.index)

    def refresh(self, is_current, is_dead):
        if is_dead:
            self.setStyleSheet("background-color: #330000; border: 2px solid #660000; border-radius: 10px;")
            self.name_label.setText(f"{self.name} (DEAD)")
            self.name_label.setStyleSheet("color: #aa6666; text-decoration: line-through;")
            self.turn_label.setVisible(False)
        else:
            bg = '#304050' if is_current else '#1e1e1e'
            border = '#88ccff' if is_current else '#333'
            self.setStyleSheet(f"background-color: {bg}; border: 2px solid {border}; border-radius: 10px;")
            self.name_label.setText(self.name)
            self.name_label.setStyleSheet("color: white;")
            self.turn_label.setVisible(is_current)

    def play_entrance_animation(self):
        if not self.isVisible():
            return
        fade = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade.setDuration(400)
        fade.setStartValue(0)
        fade.setEndValue(1)

        move = QPropertyAnimation(self, b"geometry")
        rect = self.geometry()
        move.setDuration(400)
        move.setStartValue(rect.adjusted(0, 20, 0, 20))
        move.setEndValue(rect)
        move.setEasingCurve(QEasingCurve.Type.OutBack)

        group = QParallelAnimationGroup()
        group.addAnimation(fade)
        group.addAnimation(move)
        group.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._anim_group = group

class TurnTracker(QWidget):
    def __init__(self, state: TrackerState):
        super().__init__()
        self.state = state
        self.state.subscribe(self)

        self.setWindowTitle("🧭 Turn Tracker")
        self.setGeometry(400, 200, 420, 600)
        self.setStyleSheet("background-color: #121212; color: #ffffff;")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

        title = QLabel("Initiative Order")
        title.setFont(QFont("Georgia", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none;")
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(12)
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)

        btns = QHBoxLayout()
        self.prev_btn = QPushButton("← Back")
        self.prev_btn.clicked.connect(lambda: self.state.advance_turn(-1))
        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(lambda: self.state.advance_turn(1))
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

        self.cards = []
        self.refresh()

    def refresh(self):
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.itemAt(i).widget().deleteLater()
        self.cards.clear()

        for i, (name, _) in enumerate(self.state.characters):
            is_current = (i == self.state.turn_index and not self.state.dead_flags[i])
            card = AnimatedCard(
                name, index=i,
                is_current=is_current,
                is_dead=self.state.dead_flags[i],
                on_dead_toggle=self.state.toggle_dead
            )
            self.scroll_layout.addWidget(card)
            self.cards.append(card)

            if is_current and not self.state.dead_flags[i]:
                QTimer.singleShot(50, card.play_entrance_animation)

def get_characters(test_mode=False):
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
    state = TrackerState(characters)

    tracker1 = TurnTracker(state)
    tracker2 = TurnTracker(state)
    tracker1.move(100, 100)
    tracker2.move(550, 100)

    tracker1.show()
    tracker2.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    run_app(test_mode="-test" in sys.argv)
