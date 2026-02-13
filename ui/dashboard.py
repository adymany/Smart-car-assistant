from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QWidget,
                             QHBoxLayout, QFrame, QProgressBar, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygon


try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
    class MapView(QWebEngineView):
        def set_html(self, html):
            self.setHtml(html)
except ImportError:
    HAS_WEBENGINE = False

    class MapView(QLabel):
        def __init__(self):
            super().__init__()
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setStyleSheet("background-color: #222; color: #888;")
            self.setText("Map Unavailable\n(Running in Lite Mode)")
            

        def set_html(self, html):
            # Strip HTML tags for basic text display or just show status
            if "Navigating to" in html:
                self.setText(html.split("Navigating to: ")[1].split("<")[0])
            else:
                self.setText(html)

from core import car_state



import math


class Car3DWidget(QWidget):
    def __init__(self, state):
        super().__init__()
        self.state = state
        self.angle = 0
        self.particles = [] # For AC animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(50)
        self.setMinimumSize(300, 200)

    def animate(self):
        self.angle = (self.angle + 2) % 360
        
        # AC Particles Logic
        if self.state.ac_on:
            # Add new particle
            import random
            if random.random() < 0.3:
                # (x, y, z) inside cabin
                self.particles.append([random.randint(-20, 20), random.randint(-40, -20), random.randint(-15, 15), 1.0]) # x,y,z, opacity
        
        # Update particles
        for p in self.particles:
            p[1] -= 2 # Move up/forward? Let's spread them out
            p[3] -= 0.05 # Fade out
        self.particles = [p for p in self.particles if p[3] > 0]
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        import math
        
        # Center of widget
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        
        # Common Projection Helper
        rad = math.radians(self.angle)
        pitch = math.radians(15)

        def project(x, y, z):
            # Rotate Y (yaw)
            rx = x * math.cos(rad) - z * math.sin(rad)
            rz = x * math.sin(rad) + z * math.cos(rad)
            ry = y 
            # Rotate X (pitch)
            ry2 = ry * math.cos(pitch) - rz * math.sin(pitch)
            rz2 = ry * math.sin(pitch) + rz * math.cos(pitch)
            # Perspective
            if 500 + rz2 == 0: factor = 1
            else: factor = 500 / (500 + rz2)
            px = rx * factor + cx
            py = ry2 * factor + cy
            return QPoint(int(px), int(py))

        
        # 1. DRAW GRID (Bottom Layer)
        painter.setPen(QPen(QColor(0, 50, 100, 50)))
        grid_y = 15 + 25 # HB + offset
        for i in range(-5, 6):
            g = i * 40
            # X lines
            p1 = project(-200, grid_y, g)
            p2 = project(200, grid_y, g)
            painter.drawLine(p1, p2)
            # Z lines
            p3 = project(g, grid_y, -200)
            p4 = project(g, grid_y, 200)
            painter.drawLine(p3, p4)

        # 2. DRAW HEADLIGHTS (If ON)
        # Assuming car faces +X or -X? 
        # In vertices: x is forward/back. Let's assume +L is front.
        L, W, HB = 120, 50, 15
        
        if self.state.lights_on:
            # Front corners: (L, HB, -W) and (L, HB, W) -> but slightly inside
            # Let's say headlights are at (L, HB-5, -W+10) and (L, HB-5, W-10)
            hl_y = HB - 5
            hl_z_offset = W - 15
            
            beam_length = 200
            beam_width_end = 60
            
            # Left Headlight
            start_l = (L, hl_y, -hl_z_offset)
            end_l1 = (L + beam_length, hl_y + 20, -hl_z_offset - beam_width_end)
            end_l2 = (L + beam_length, hl_y + 20, -hl_z_offset + beam_width_end)
            
            # Right Headlight
            start_r = (L, hl_y, hl_z_offset)
            end_r1 = (L + beam_length, hl_y + 20, hl_z_offset - beam_width_end)
            end_r2 = (L + beam_length, hl_y + 20, hl_z_offset + beam_width_end)
            
            painter.setPen(Qt.PenStyle.NoPen)
            beam_color = QColor(0, 255, 255, 60) # Cyber blue-ish transparency
            
            for start, end1, end2 in [(start_l, end_l1, end_l2), (start_r, end_r1, end_r2)]:
                p_start = project(*start)
                p_end1 = project(*end1)
                p_end2 = project(*end2)
                
                # Beam Glow
                painter.setBrush(beam_color)
                painter.drawPolygon(QPolygon([p_start, p_end1, p_end2]))
                
                # Focused Source
                painter.setBrush(QColor(255, 255, 255, 200))
                painter.drawEllipse(p_start, 5, 5)


        # 3. DRAW CAR WIREFRAME
        pen = QPen(QColor(0, 212, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        verts = [
            (-L, HB, -W), (L, HB, -W), (L, HB, W), (-L, HB, W),  # Bottom
            (-L, -HB, -W), (L, -HB, -W), (L, -HB, W), (-L, -HB, W), # Top Body
            (-L*0.4, -HB, -W*0.9), (L*0.3, -HB, -W*0.9), (L*0.3, -HB, W*0.9), (-L*0.4, -HB, W*0.9), # Cabin Base
            (-L*0.2, -HB-25, -W*0.7), (L*0.1, -HB-25, -W*0.7), (L*0.1, -HB-25, W*0.7), (-L*0.2, -HB-25, W*0.7) # Roof
        ]
        edges = [
            (0,1), (1,2), (2,3), (3,0), (4,5), (5,6), (6,7), (7,4), # Loops
            (0,4), (1,5), (2,6), (3,7), # Pillars
            (8,12), (9,13), (10,14), (11,15), (12,13), (13,14), (14,15), (15,12), # Cabin
            (8,9), (9,10), (10,11), (11,8)
        ]
        
        # Project Verts
        p_verts = [project(x,y,z) for x,y,z in verts]
        for i, j in edges:
            painter.drawLine(p_verts[i], p_verts[j])

        # Wheels
        wheel_settings = [ (L*0.6, HB+10, -(W+5)), (L*0.6, HB+10, W+5), (-L*0.6, HB+10, -(W+5)), (-L*0.6, HB+10, W+5) ]
        painter.setPen(QPen(QColor(0, 100, 200))) 
        for wx, wy, wz in wheel_settings:
            w_pts = []
            for i in range(8):
                ang = math.radians(i * 45)
                w_pts.append(project(wx + 20*math.cos(ang), wy + 20*math.sin(ang), wz))
            painter.drawPolygon(QPolygon(w_pts))

        # 4. DRAW AC PARTICLES (If ON)
        if self.state.ac_on:
            painter.setPen(Qt.PenStyle.NoPen)
            for x, y, z, opacity in self.particles:
                 pt = project(x, y, z)
                 # Color: Cyan/White wisp
                 painter.setBrush(QColor(200, 255, 255, int(opacity * 150)))
                 painter.drawEllipse(pt, 2, 8) # Vertical-ish wisps



class VoiceVisualizerWidget(QWidget):
    def __init__(self, state):
        super().__init__()
        self.state = state
        self.points = [0] * 30
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30) # High refresh for smooth 3D
        self.setMinimumSize(250, 250)
        self.yaw = 0
        self.pitch = 0
        self.pulse = 0

    def animate(self):
        self.yaw = (self.yaw + 3) % 360
        self.pitch = (self.pitch + 2) % 360
        
        import random
        # Only react to AI audio or listening state
        if self.state.ai_talking or self.state.is_listening:
            self.pulse = (self.pulse + 0.5) % (math.pi * 2)
            for i in range(len(self.points)):
                # Vibrant reaction
                target = random.randint(10, 40)
                self.points[i] = self.points[i] * 0.7 + target * 0.3
        else:
            # Slower, calm idle or nearly still
            self.pulse = 0
            for i in range(len(self.points)):
                self.points[i] = self.points[i] * 0.9 # Fade to 0
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        
        # 3D Projection Helpers
        rad_y = math.radians(self.yaw)
        rad_p = math.radians(self.pitch)
        
        def project_3d(x, y, z):
            # Rotate Y
            rx = x * math.cos(rad_y) - z * math.sin(rad_y)
            rz = x * math.sin(rad_y) + z * math.cos(rad_y)
            # Rotate X
            ry = y * math.cos(rad_p) - rz * math.sin(rad_p)
            rz2 = y * math.sin(rad_p) + rz * math.cos(rad_p)
            
            factor = 400 / (400 + rz2)
            return QPoint(int(rx * factor + cx), int(ry * factor + cy))

        # Colors
        base_color = QColor(0, 212, 255) # Siri Blue
        if self.state.is_listening:
            base_color = QColor(0, 255, 150) # Listen Green
            
        # Draw 3 Perpendicular Rings
        num_rings = 4
        radius = 80
        
        for ring_idx in range(num_rings):
            # Pulse effect
            reaction = math.sin(self.pulse + ring_idx) * 10 if self.pulse > 0 else 0
            r = radius + reaction
            
            painter.setPen(QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 150 - ring_idx * 30), 2))
            
            points = []
            for i in range(31):
                ang = math.radians(i * (360 / 30))
                # Distort rings based on AI activity
                noise = self.points[i % 30] * 0.2 if self.pulse > 0 else 0
                r_noise = r + noise
                
                # Each ring is on a different plane
                if ring_idx == 0: # X-Y Plane
                    x, y, z = r_noise * math.cos(ang), r_noise * math.sin(ang), 0
                elif ring_idx == 1: # X-Z Plane
                    x, y, z = r_noise * math.cos(ang), 0, r_noise * math.sin(ang)
                elif ring_idx == 2: # Y-Z Plane
                    x, y, z = 0, r_noise * math.cos(ang), r_noise * math.sin(ang)
                else: # Diagonal
                    x, y, z = r_noise * math.cos(ang) * 0.7, r_noise * math.sin(ang) * 0.7, r_noise * math.sin(ang) * 0.7
                
                points.append(project_3d(x, y, z))
            
            painter.drawPolyline(QPolygon(points))

        # Inner Glowing Core
        if self.state.ai_talking or self.state.is_listening:
            core_size = 40 + int(math.sin(self.pulse * 2) * 10)
            grad_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 100)
            painter.setBrush(grad_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(cx - core_size//2, cy - core_size//2, core_size, core_size)



class Dashboard(QMainWindow):
    def __init__(self, state: car_state.CarState):
        super().__init__()
        self.state = state
        self.setWindowTitle("CarAI Assistant")
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        self.setMinimumSize(1000, 600)

        self.init_ui()
        
        # update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(500) # update every 500ms



    

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        # Cyberpunk / AI Styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f0f1a;
            }
            QLabel {
                color: #00d4ff;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit {
                background-color: rgba(20, 20, 40, 200);
                border: 1px solid #00d4ff;
                border-radius: 15px;
                color: white;
                padding: 10px;
                font-size: 16px;
            }
        """)
        
        # Top Level Layout (Vertical)
        top_layout = QVBoxLayout(central)
        top_layout.setContentsMargins(20, 20, 20, 20)
        
        # Dashboard Content (Horizontal)
        content_layout = QHBoxLayout()
        top_layout.addLayout(content_layout, 1)


        # Left Panel (Controls)
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(20, 30, 50, 150);
                border: 1px solid #00d4ff;
                border-radius: 15px;
            }
        """)
        
        label_style = "font-size: 18px; font-weight: bold; color: white; margin-bottom: 10px;"
        left_layout.addWidget(QLabel("CONTROLS", styleSheet=label_style))

        # AC Control
        self.ac_btn = QPushButton("❄️ AC SYSTEM")
        self.ac_btn.setCheckable(True)
        self.ac_btn.setStyleSheet(self.get_btn_style())
        self.ac_btn.clicked.connect(self.toggle_ac)
        left_layout.addWidget(self.ac_btn)

        # Lights Control
        self.lights_btn = QPushButton("💡 HEADLIGHTS")
        self.lights_btn.setCheckable(True)
        self.lights_btn.setStyleSheet(self.get_btn_style())
        self.lights_btn.clicked.connect(self.toggle_lights)
        left_layout.addWidget(self.lights_btn)


        # Wipers Control
        self.wipers_btn = QPushButton("🌧️ WIPERS")
        self.wipers_btn.setCheckable(True)
        self.wipers_btn.setStyleSheet(self.get_btn_style())
        self.wipers_btn.clicked.connect(self.toggle_wipers)
        left_layout.addWidget(self.wipers_btn)

        left_layout.addSpacing(20)
        
        # New Feature: Battery Status
        left_layout.addWidget(QLabel("ENERGY SOURCE", styleSheet="color: #00ffaa; font-size: 14px; font-weight: bold;"))
        self.battery_bar = QProgressBar()
        self.battery_bar.setValue(85)
        self.battery_bar.setTextVisible(True)
        self.battery_bar.setFormat("85% [ELECTRIC]")
        self.battery_bar.setStyleSheet("""
            QProgressBar {
                background-color: #111;
                border: 1px solid #00ffaa;
                border-radius: 5px;
                text-align: center;
                color: #00ffaa;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00aa66, stop:1 #00ffaa);
            }
        """)
        left_layout.addWidget(self.battery_bar)

        left_layout.addStretch()
        
        # Manual Listen Button
        self.listen_btn = QPushButton("🎤 ACTIVATE VOICE")
        self.listen_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d4ff, stop:1 #0055ff);
                color: white;
                font-weight: bold;
                font-size: 16px;
                padding: 15px;
                border: none;
                border-radius: 25px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #44eeff, stop:1 #0088ff);
            }
            QPushButton:pressed {
                background-color: #0044aa;
            }
        """)
        self.listen_btn.clicked.connect(self.manual_listen)
        left_layout.addWidget(self.listen_btn)

        content_layout.addWidget(left_panel, 1)


        # Center Panel (Speed & Map & 3D Car)
        center_panel = QFrame()
        center_layout = QVBoxLayout(center_panel)
        center_panel.setStyleSheet("background: transparent;")
        
        # Speedometer (Now smaller/secondary)
        self.speed_label = QLabel("85")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speed_label.setStyleSheet("""
            font-size: 30px; 
            font-weight: bold; 
            color: #555;
            background-color: rgba(0,0,0,50);
            border: 1px solid #333;
            border-radius: 10px;
            padding: 5px;
        """)
        
        # Voice Visualizer (Main Central Element)
        self.voice_visualizer = VoiceVisualizerWidget(self.state)
        
        # 3D Car Widget
        self.car_model = Car3DWidget(self.state)
        
        # AC Display
        self.ac_display = QLabel("AC: OFF  --°C")
        self.ac_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ac_display.setStyleSheet("""
            font-size: 24px;
            color: #00ffaa;
            background-color: rgba(0, 50, 0, 100);
            border: 1px solid #00ffaa;
            border-radius: 10px;
            padding: 10px;
            margin-top: 10px;
        """)

        speed_container = QWidget()
        speed_layout = QHBoxLayout(speed_container)
        speed_layout.addWidget(QLabel("SPEED: "))
        speed_layout.addWidget(self.speed_label)
        speed_layout.addWidget(QLabel("KM/H"))
        
        center_layout.addWidget(self.voice_visualizer, 0, Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.car_model, 1, Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(speed_container, 0, Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.ac_display)
        
        # New Feature: Music Visualization / Area
        music_area = QFrame()
        music_area.setStyleSheet("background: rgba(0,0,0,50); border-radius: 10px; border-bottom: 2px solid #00d4ff;")
        music_layout = QHBoxLayout(music_area)
        music_icon = QLabel("🎵")
        music_icon.setStyleSheet("font-size: 24px;")
        music_info = QLabel("CyberTrack 2077 - Night City FM")
        music_info.setStyleSheet("color: #00d4ff; font-size: 14px; font-style: italic;")
        music_layout.addWidget(music_icon)
        music_layout.addWidget(music_info)
        music_layout.addStretch()
        center_layout.addWidget(music_area)

        center_layout.addWidget(self.ac_display)
        
        # Map Placeholder (Smaller now)
        self.map_view = MapView()
        self.map_view.setMaximumHeight(200)

        if HAS_WEBENGINE:
             self.map_view.setHtml("""
                <html><body style='background:#0f0f1a;color:#00d4ff;display:flex;justify-content:center;align-items:center;height:100%;font-family:sans-serif;'>
                <div style="border: 2px solid #00d4ff; padding: 10px; border-radius: 10px;">
                    <h3>NAV ONLINE</h3>
                </div>
                </body></html>
            """)
        else:
             # Cyberpunk Lite Mode Map
             self.map_view.setText("NAV SYSTEM\nTARGET: N/A")
             self.map_view.setStyleSheet("""
                QLabel { 
                    background-color: rgba(0, 20, 40, 200); 
                    color: #00ffaa; 
                    font-family: Consolas; 
                    font-size: 12px; 
                    border: 2px solid #00d4ff; 
                    border-radius: 10px;
                    padding: 10px;
                }
             """)
        
        center_layout.addWidget(self.map_view)
        content_layout.addWidget(center_panel, 2)

        # Right Panel (Voice Log)
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setStyleSheet("background-color: #2a2a2a; border-radius: 10px; padding: 10px;")
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("font-size: 14px; color: #ddd; font-family: Consolas;")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        right_layout.addWidget(QLabel("Voice Assistant Log:"))
        right_layout.addWidget(self.status_label, 1)
        
        content_layout.addWidget(right_panel, 1)
        
        # Input Field
        from PyQt6.QtWidgets import QLineEdit
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type a command (e.g., 'Turn on AC')...")
        self.text_input.setStyleSheet("padding: 10px; font-size: 16px; background: #333; color: white; border: 1px solid #555; border-radius: 5px; margin-top: 10px;")
        self.text_input.returnPressed.connect(self.handle_text_input)
        top_layout.addWidget(self.text_input)


    def handle_text_input(self):
        text = self.text_input.text()
        if text:
            self.text_input.clear()
            self.update_voice_status(f"You (Type): {text}")
            self.command_entered.emit(text)


    def get_btn_style(self):
        return """
            QPushButton {
                background-color: rgba(255, 255, 255, 10); 
                color: #00d4ff; 
                padding: 15px; 
                border: 1px solid #0055ff;
                border-radius: 10px;
                font-size: 14px;
                text-align: left;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: rgba(0, 212, 255, 50);
                border: 1px solid #00d4ff;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(0, 212, 255, 20);
            }
        """

    def toggle_ac(self):
        self.state.ac_on = self.ac_btn.isChecked()
        self.ac_btn.setText(f"AC: {'ON' if self.state.ac_on else 'OFF'}")
        
    def toggle_lights(self):
        self.state.lights_on = self.lights_btn.isChecked()
        self.lights_btn.setText(f"Lights: {'ON' if self.state.lights_on else 'OFF'}")

    def toggle_wipers(self):
        self.state.wipers_on = self.wipers_btn.isChecked()
        self.wipers_btn.setText(f"Wipers: {'ON' if self.state.wipers_on else 'OFF'}")

    def manual_listen(self):
        # Trigger manual listening logic
        self.listen_requested.emit()

    # Define signals
    command_entered = pyqtSignal(str)
    listen_requested = pyqtSignal()


    def update_voice_status(self, text):
        self.status_label.setText(text)


    def update_ui(self):
        """Updates UI elements based on car_state."""
        # Update Speed
        self.speed_label.setText(str(self.state.speed))
        # Sync Button States
        self.ac_btn.setChecked(self.state.ac_on)
        self.ac_btn.setText(f"AC: {'ON' if self.state.ac_on else 'OFF'}")
        
        self.lights_btn.setChecked(self.state.lights_on)
        self.lights_btn.setText(f"Lights: {'ON' if self.state.lights_on else 'OFF'}")
        
        self.wipers_btn.setChecked(self.state.wipers_on)

        self.wipers_btn.setText(f"Wipers: {'ON' if self.state.wipers_on else 'OFF'}")
        
        # Update AC Display
        ac_status = "ON" if self.state.ac_on else "OFF"
        self.ac_display.setText(f"AC: {ac_status}  {self.state.ac_temp}°C")
        if self.state.ac_on:
             self.ac_display.setStyleSheet("""
                font-size: 24px; color: #00ffaa; background-color: rgba(0, 50, 0, 150);
                border: 1px solid #00ffaa; border-radius: 10px; padding: 10px; margin-top: 10px;
             """)
        else:
             self.ac_display.setStyleSheet("""
                font-size: 24px; color: #555; background-color: rgba(20, 20, 20, 150);
                border: 1px solid #555; border-radius: 10px; padding: 10px; margin-top: 10px;
             """)

        # Nav
        if self.state.destination:
             if HAS_WEBENGINE:
                 self.map_view.setHtml(f"""
                    <html><body style='background:#222;color:#1e90ff;display:flex;justify-content:center;align-items:center;height:100%;font-family:sans-serif;'>
                    <h1>Navigating to: {self.state.destination}</h1>
                    </body></html>
                """)
             else:
                 self.map_view.set_html(f"Navigating to: {self.state.destination}")

