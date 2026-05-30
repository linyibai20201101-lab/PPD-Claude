from enum import Enum
from PyQt5.QtCore import QObject, QTimer, pyqtSignal


class TimerState(Enum):
    IDLE = "idle"
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"
    PAUSED = "paused"


class PomodoroTimer(QObject):
    tick = pyqtSignal(int, int)          # remaining_seconds, total_seconds
    state_changed = pyqtSignal(str)      # TimerState value
    pomodoro_completed = pyqtSignal()    # 一个番茄完成
    session_completed = pyqtSignal(str)  # work / short_break / long_break

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self._state = TimerState.IDLE
        self._remaining = 0
        self._total = 0
        self._pomodoro_count = 0
        self._paused_state = None

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

    @property
    def state(self) -> TimerState:
        return self._state

    @property
    def remaining(self) -> int:
        return self._remaining

    @property
    def total(self) -> int:
        return self._total

    @property
    def pomodoro_count(self) -> int:
        return self._pomodoro_count

    def start_work(self):
        self._timer.stop()
        self._state = TimerState.WORK
        self._total = self.config["work_duration"] * 60
        self._remaining = self._total
        self._paused_state = None
        self._timer.start()
        self.state_changed.emit(self._state.value)
        self.tick.emit(self._remaining, self._total)

    def start_break(self, is_long: bool = False):
        self._timer.stop()
        if is_long:
            self._state = TimerState.LONG_BREAK
            self._total = self.config["long_break"] * 60
        else:
            self._state = TimerState.SHORT_BREAK
            self._total = self.config["short_break"] * 60
        self._remaining = self._total
        self._paused_state = None
        self._timer.start()
        self.state_changed.emit(self._state.value)
        self.tick.emit(self._remaining, self._total)

    def pause(self):
        if self._state in (TimerState.WORK, TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            self._paused_state = self._state
            self._state = TimerState.PAUSED
            self._timer.stop()
            self.state_changed.emit(self._state.value)

    def resume(self):
        if self._state == TimerState.PAUSED and self._paused_state:
            self._state = self._paused_state
            self._paused_state = None
            self._timer.start()
            self.state_changed.emit(self._state.value)

    def reset(self):
        self._timer.stop()
        self._state = TimerState.IDLE
        self._remaining = 0
        self._total = 0
        self._paused_state = None
        self.state_changed.emit(self._state.value)
        self.tick.emit(0, 0)

    def skip(self):
        self._timer.stop()
        self._finish_session()

    def toggle_pause(self):
        if self._state == TimerState.PAUSED:
            self.resume()
        elif self._state in (TimerState.WORK, TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            self.pause()

    def _on_tick(self):
        self._remaining -= 1
        self.tick.emit(self._remaining, self._total)
        if self._remaining <= 0:
            self._finish_session()

    def _finish_session(self):
        finished_state = self._state
        if self._paused_state:
            finished_state = self._paused_state

        self._timer.stop()

        if finished_state == TimerState.WORK:
            self._pomodoro_count += 1
            self.pomodoro_completed.emit()
            self.session_completed.emit("work")
            if self._pomodoro_count % self.config["pomodoros_before_long"] == 0:
                if self.config["auto_start_break"]:
                    self.start_break(is_long=True)
                else:
                    self._state = TimerState.IDLE
                    self.state_changed.emit(self._state.value)
            else:
                if self.config["auto_start_break"]:
                    self.start_break(is_long=False)
                else:
                    self._state = TimerState.IDLE
                    self.state_changed.emit(self._state.value)
        else:
            self.session_completed.emit(finished_state.value)
            if self.config["auto_start_work"]:
                self.start_work()
            else:
                self._state = TimerState.IDLE
                self.state_changed.emit(self._state.value)
                self.tick.emit(0, 0)
