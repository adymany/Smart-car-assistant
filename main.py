
import sys
# Import VoiceHandler first to load onnxruntime/openwakeword before PyQt6 to avoid DLL conflicts

from core.voice_handler import VoiceHandler
from PyQt6.QtWidgets import QApplication
from ui.dashboard import Dashboard
from core.car_state import CarState

def main():
    app = QApplication(sys.argv)
    
    # Shared State
    state = CarState()
    
    # UI
    window = Dashboard(state)
    

    # Voice Handler
    voice = VoiceHandler(state)
    voice.voice_status.connect(window.update_voice_status)

    # Connect text input from UI to Voice Handler
    window.command_entered.connect(voice.process_text_command)
    # Connect manual listen button
    window.listen_requested.connect(lambda: voice._handle_command())
    
    voice.start()
    
    window.show()
    
    exit_code = app.exec()
    voice.stop()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
