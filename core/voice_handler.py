
import threading
import time
import speech_recognition as sr
import pyttsx3
import sounddevice as sd

import sounddevice as sd
import numpy as np



try:
    import onnxruntime 
    import openwakeword
    from openwakeword.model import Model
    OWW_AVAILABLE = True
except ImportError as e:
    OWW_AVAILABLE = False
    print(f"OpenWakeWord import failed: {e}")
except Exception as e:
    OWW_AVAILABLE = False
    print(f"OpenWakeWord general error: {e}")


from PyQt6.QtCore import pyqtSignal, QObject
from . import config
# Using Ollama exclusively
from . import ollama_handler as ai_handler
from .car_state import CarState

class VoiceHandler(QObject):
    voice_status = pyqtSignal(str)

    def __init__(self, state: CarState):
        super().__init__()
        self.state = state
        self.running = False
        self.oww_model = None
        self.AUDIO_AVAILABLE = False
        
        try:
            self.recognizer = sr.Recognizer()

            self.recognizer = sr.Recognizer()
            # TTS engine initialized on demand in speak()
            self.AUDIO_AVAILABLE = True
            self.mic_lock = threading.Lock()
            self.is_processing = False
        except Exception as e:
            print(f"Audio Init Failed: {e}")
            self.AUDIO_AVAILABLE = False

    def start(self):
        """Starts the wake word detection loop in a separate thread."""
        if self.AUDIO_AVAILABLE:
            self.running = True
            threading.Thread(target=self._wake_word_loop, daemon=True).start()
        else:
            # Emit safely after a short delay to ensure UI is ready
            threading.Timer(1.0, lambda: self.voice_status.emit("Audio Unavailable. Text mode only.")).start()

    def stop(self):
        self.running = False


    def _wake_word_loop(self):
        """Listens for 'hey jarvis' wake word."""
        if not self.AUDIO_AVAILABLE or not OWW_AVAILABLE:
            if not OWW_AVAILABLE: self.voice_status.emit("Wake Word feature unavailable.")
            return
        
        try:
            # Check if models need downloading/loading
            openwakeword.utils.download_models(["hey_jarvis"])
            self.oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        except Exception as e:
            self.voice_status.emit(f"Error loading Wake Word: {e}")
            return

        CHUNK_SIZE = 1280
        RATE = 16000
        

        self.voice_status.emit("Say 'Hey Jarvis'...")

        while self.running:
            self.oww_model.reset() # Reset model state before listening
            try:
                # Open stream for wake word detection
                try:
                    with sd.InputStream(samplerate=RATE, blocksize=CHUNK_SIZE, channels=1, dtype='int16') as stream:
                        while self.running:
                            chunk, overflow = stream.read(CHUNK_SIZE)
                            
                            # Flatten if needed
                            audio_data = np.frombuffer(chunk, dtype=np.int16)
                            
                            prediction = self.oww_model.predict(audio_data)
                            
                            if prediction["hey_jarvis"] > 0.5 and not self.is_processing:
                                self.voice_status.emit("Wake Word Detected!")
                                # Stop this stream loop to release mic for SpeechRecognition
                                break
                except Exception as e:
                    self.voice_status.emit(f"Mic Error: {e}. Retrying...")
                    time.sleep(5) # Wait before retrying
                    continue

                # Stream is closed here. 
                if self.running:
                    self._handle_command()
                    self.voice_status.emit("Say 'Hey Jarvis'...")
                    time.sleep(1.0) # Cooldown to prevent self-triggering
            
            except Exception as e:
                self.voice_status.emit(f"Voice Loop Error: {e}")
                time.sleep(1)

            # Check if we should listen (simulated trigger or handling logic)
            if self.running and False: # force false for now
                 self._handle_command()
                 self.voice_status.emit("Say 'Hey Jarvis'...")


    def _handle_command(self):
        """Listens for command and sends to AI."""
        if not self.AUDIO_AVAILABLE: return
        if self.is_processing: return # Guard against multiple calls
        
        with self.mic_lock:
            self.is_processing = True
            self.state.is_listening = True
            self.voice_status.emit("Listening...")
            
            try:
                with sr.Microphone() as source:
                    # Short ambient adjust
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    try:
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
                    except sr.WaitTimeoutError:
                        self.voice_status.emit("Timeout - didn't hear command.")
                        self.is_processing = False
                        return
                    except Exception as e:
                        self.voice_status.emit(f"Listen Error: {e}")
                        self.is_processing = False
                        return

                try:
                    # STT
                    text = self.recognizer.recognize_google(audio)
                    self.voice_status.emit(f"You: {text}")

                    self.process_text_command(text, blocking=True)
                    
                except sr.UnknownValueError:
                    self.voice_status.emit("Sorry, I didn't verify that.")
                    self.speak("I didn't catch that.")
                except Exception as e:
                    self.voice_status.emit(f"Error: {e}")
                    print(f"Processing Error: {e}")

            except Exception as e:
                self.voice_status.emit(f"Mic Error: {e}")
                print(f"Mic Error: {e}")
            

            self.is_processing = False
            self.state.is_listening = False




    def speak(self, text):
        if self.AUDIO_AVAILABLE:
            try:
                self.state.ai_talking = True
                # Re-init engine locally to avoid threading/loop issues
                engine = pyttsx3.init()
                engine.setProperty('rate', 170)
                engine.say(text)
                engine.runAndWait()
                # Clean deletion of engine if needed, though pyttsx3 usually handles it
                del engine
                self.state.ai_talking = False
            except Exception as e:
                self.state.ai_talking = False
                print(f"TTS Error: {e}")
                # Fallback print
                self.voice_status.emit(f"TTS Failed: {e}")



    def process_text_command(self, text, blocking=False):
        """Processes a text command (from voice or UI)."""
        self.voice_status.emit(f"Processing: {text}")
        self.voice_status.emit("Thinking...")
        
        if blocking:
            self._process_text_logic(text)
        else:
            # Run in thread to not block UI (for UI text input)
            threading.Thread(target=self._process_text_logic, args=(text,)).start()


    def _process_text_logic(self, text):
        try:
            response_text = ai_handler.process_command(text, self.state)
            self.voice_status.emit(f"AI: {response_text}")
            self.speak(response_text)
        except Exception as e:
            self.voice_status.emit(f"AI Error: {e}")
