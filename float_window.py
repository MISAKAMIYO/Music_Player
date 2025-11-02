import sys
from PyQt5.QtCore import QDateTime, QObject, Qt, QPoint, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont, QMouseEvent
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QSlider, QPushButton

class ProgressManager(QObject):
    """统一的进度管理器"""
    progress_updated = pyqtSignal(int, int)  # 当前位置, 总时长
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_position = 0
        self.total_duration = 0
        self.last_progress_value = -1
        self.progress_threshold = 5  # 只有变化超过5才更新
        self.update_interval = 100   # 更新间隔(ms)
        self.last_update_time = 0
        self.update_timer.timeout.connect(self.emit_progress)
        self.update_timer.start()
        
    def set_position(self, position):
        self.current_position = position
        
    def set_duration(self, duration):
        self.total_duration = duration
        
    def emit_progress(self):
        if self.total_duration > 0:
            self.progress_updated.emit(self.current_position, self.total_duration)
            
class FloatWindow(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.main_window = main_window
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 80)
        
        # 初始位置（屏幕右下角）
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.move(screen_geometry.width() - 320, screen_geometry.height() - 100)
        
        self.dragging = False
        self.drag_position = QPoint()
        self.last_progress_value = -1
        self.progress_threshold = 5
        
        self.init_ui()
        self.setup_connections()
        
    def update_position(self, position):
        # 节流控制
        current_time = QDateTime.currentMSecsSinceEpoch()
        if current_time - self.last_update_time < self.update_interval:
            return
        self.last_update_time = current_time
        
        if self.media_player.duration() <= 0:
            return
            
        progress = int(1000 * position / self.media_player.duration())
        
        # 变化阈值控制
        if abs(progress - self.last_progress_value) < self.progress_threshold:
            return
            
        self.last_progress_value = progress
        self.progress_slider.setValue(progress)
        
        # 更新时间显示
        self.current_time_label.setText(self.format_time(position))
        self.total_time_label.setText(self.format_time(self.media_player.duration()))
        
    def init_ui(self):
        # 创建控件
        self.prev_btn = QPushButton("◀◀")
        self.play_btn = QPushButton("▶")
        self.next_btn = QPushButton("▶▶")
        self.progress_slider = QSlider(Qt.Horizontal)
        
        # 设置样式
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(70, 70, 70, 180);
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 14px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background-color: rgba(100, 100, 100, 200);
            }
            QSlider::groove:horizontal {
                background: rgba(100, 100, 100, 100);
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: rgba(255, 255, 255, 200);
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -3px 0;
            }
            QSlider::sub-page:horizontal {
                background: rgba(70, 130, 180, 200);
                border-radius: 3px;
            }
        """)
        
        # 布局
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.play_btn)
        layout.addWidget(self.next_btn)
        layout.addWidget(self.progress_slider)
        self.setLayout(layout)
        
    def setup_connections(self):
        # 连接按钮信号
        self.prev_btn.clicked.connect(self.main_window.play_previous)
        self.play_btn.clicked.connect(self.toggle_play)
        self.next_btn.clicked.connect(self.main_window.play_next)
        
        # 连接进度条信号
        self.progress_slider.sliderMoved.connect(self.seek_position)
        self.progress_slider.sliderPressed.connect(self.progress_pressed)
        self.progress_slider.sliderReleased.connect(self.progress_released)
        
        # 设置定时器更新进度
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(500)  # 每500ms更新一次
        
    def toggle_play(self):
        if self.main_window.media_player.state() == self.main_window.media_player.PlayingState:
            self.main_window.pause_song()
            self.play_btn.setText("▶")
        else:
            self.main_window.play_song()
            self.play_btn.setText("❚❚")
            
    def update_progress(self):
        if (hasattr(self.main_window, 'media_player') and 
            self.main_window.media_player.duration() > 0 and
            not self.progress_slider.isSliderDown()):
            
            position = self.main_window.media_player.position()
            duration = self.main_window.media_player.duration()
            progress = int(1000 * position / duration) if duration > 0 else 0
            self.progress_slider.setValue(progress)
            
            # 更新播放按钮状态
            if self.main_window.media_player.state() == self.main_window.media_player.PlayingState:
                self.play_btn.setText("❚❚")
            else:
                self.play_btn.setText("▶")
                
    def seek_position(self, value):
        if self.main_window.media_player.duration() > 0:
            position = int(value * self.main_window.media_player.duration() / 1000)
            self.main_window.media_player.setPosition(position)
            
    def progress_pressed(self):
        self.was_playing = self.main_window.media_player.state() == self.main_window.media_player.PlayingState
        if self.was_playing:
            self.main_window.media_player.pause()
            
    def progress_released(self):
        if hasattr(self, 'was_playing') and self.was_playing:
            self.main_window.media_player.play()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制半透明圆角背景
        painter.setBrush(QBrush(QColor(40, 40, 40, 180)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()
            
    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)