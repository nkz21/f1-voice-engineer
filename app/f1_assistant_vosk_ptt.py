import sys
import time
import queue
import threading
import logging
import json
import os

import tkinter as tk
from tkinter import ttk, messagebox

import pygame
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# --------------------------------------------------------------------- CONFIG

# >>> ADAPTER CE CHEMIN vers ton dossier modele Vosk FR <<<
VOSK_MODEL_PATH = r"C:\Users\nassi\Models\vosk-model-small-fr-0.22"

# Joystick Moza
MOZA_JOYSTICK_ID = 2
BOX_BUTTON_ID = 19

# Audio
SAMPLE_RATE = 16000
BLOCK_SIZE = 4000

# Logging
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(asctime)s - %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("F1VoiceEngineer")


# --------------------------------------------------------------------- PTT + VOSK

class PTTSTTController:
    """Gere le stream micro + la transcription Vosk en push-to-talk."""

    def __init__(self, event_queue, device_index=None):
        self.event_queue = event_queue
        self.device_index = device_index
        self.audio_queue = queue.Queue()
        self.cmd_queue = queue.Queue()
        self.running = True
        self.recording = False

        if not os.path.isdir(VOSK_MODEL_PATH):
            raise FileNotFoundError(
                f"Modele Vosk introuvable : {VOSK_MODEL_PATH}\n"
                "Adapte la constante VOSK_MODEL_PATH dans le script."
            )

        logger.info("[ASR] Chargement modele Vosk...")
        self.model = Model(VOSK_MODEL_PATH)
        logger.info("[ASR] Modele Vosk charge.")

        self.stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            dtype="int16",
            channels=1,
            callback=self._audio_callback,
            device=self.device_index,
        )

        self.stt_thread = threading.Thread(target=self._stt_worker, daemon=True)
        self.stt_thread.start()

    def start_session(self):
        if self.recording:
            return
        logger.info("[PTT] Debut session")
        self.recording = True
        self.cmd_queue.put("START")
        self.stream.start()

    def stop_session(self):
        if not self.recording:
            return
        logger.info("[PTT] Fin session")
        self.recording = False
        self.audio_queue.put(None)
        self.stream.stop()

    def shutdown(self):
        self.running = False
        self.audio_queue.put(None)
        self.cmd_queue.put("STOP_ALL")
        try:
            self.stream.stop()
        except Exception:
            pass

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"[AUDIO] {status}")
        if self.recording:
            self.audio_queue.put(bytes(indata))

    def _stt_worker(self):
        logger.info("[ASR] Thread STT demarre")
        while self.running:
            try:
                cmd = self.cmd_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if cmd == "STOP_ALL":
                break
            if cmd == "START":
                rec = KaldiRecognizer(self.model, SAMPLE_RATE)
                chunks = []
                while True:
                    data = self.audio_queue.get()
                    if data is None:
                        break
                    if rec.AcceptWaveform(data):
                        res = json.loads(rec.Result())
                        if res.get("text"):
                            chunks.append(res["text"].strip())
                try:
                    res = json.loads(rec.FinalResult())
                    if res.get("text"):
                        chunks.append(res["text"].strip())
                except Exception:
                    pass
                text = " ".join(t for t in chunks if t).strip()
                logger.info(f"[ASR] Transcription: {text}")
                self.event_queue.put(("ASR_RESULT", text))
        logger.info("[ASR] Thread STT arrete")


# --------------------------------------------------------------------- UI

class F1AssistantApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("F1 Voice Engineer")
        self.geometry("700x440")
        self.configure(bg="#0b0f1e")

        self.event_queue = queue.Queue()
        self.ptt_controller = None
        self.selected_device_index = tk.IntVar(value=-1)

        self._build_ui()
        self._init_audio_ptt()
        self._start_joystick_thread()
        self.after(50, self._process_events)

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabelframe", background="#0b0f1e", foreground="#c0c4e0")
        style.configure("TLabelframe.Label", background="#0b0f1e", foreground="#c0c4e0")

        padx, pady = 10, 5

        frame_audio = ttk.LabelFrame(self, text="Audio / Micro")
        frame_audio.pack(fill="x", padx=padx, pady=(pady, 0))

        tk.Label(frame_audio, text="Peripherique micro :", bg="#0b0f1e", fg="#c0c4e0").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )

        devices = sd.query_devices()
        input_devices = [
            f"{idx}: {dev['name']}"
            for idx, dev in enumerate(devices)
            if dev["max_input_channels"] > 0
        ]
        self.device_combo = ttk.Combobox(
            frame_audio, state="readonly", width=58, values=input_devices
        )
        self.device_combo.grid(row=0, column=1, padx=5, pady=5)
        if input_devices:
            self.device_combo.current(0)
            self.selected_device_index.set(int(input_devices[0].split(":", 1)[0]))
        self.device_combo.bind("<<ComboboxSelected>>", self._on_device_changed)

        frame_status = ttk.LabelFrame(self, text="Statut systeme")
        frame_status.pack(fill="x", padx=padx, pady=(pady, 0))

        self.status_audio = tk.StringVar(value="Audio : pret")
        self.status_box = tk.StringVar(value="Volant : attente...")
        self.status_asr = tk.StringVar(value="ASR : en attente")

        for var in (self.status_audio, self.status_box, self.status_asr):
            tk.Label(frame_status, textvariable=var, bg="#0b0f1e", fg="#a0e0a0",
                     anchor="w").pack(fill="x", padx=8, pady=2)

        frame_trans = ttk.LabelFrame(self, text="Transcription")
        frame_trans.pack(fill="both", expand=True, padx=padx, pady=(pady, 0))

        self.transcription_widget = tk.Text(
            frame_trans, height=6, wrap="word",
            bg="#111424", fg="#f0f0ff", font=("Consolas", 11),
            relief="flat", padx=8, pady=8
        )
        self.transcription_widget.pack(fill="both", expand=True, padx=5, pady=5)

        frame_ctrl = ttk.LabelFrame(self, text="Controles")
        frame_ctrl.pack(fill="x", padx=padx, pady=(pady, pady))

        tk.Button(
            frame_ctrl, text="Quitter", command=self._on_quit,
            bg="#ff0055", fg="white", relief="flat", padx=10
        ).pack(side="right", padx=5, pady=5)

        self.protocol("WM_DELETE_WINDOW", self._on_quit)

    def _on_device_changed(self, event=None):
        sel = self.device_combo.get()
        if not sel:
            return
        try:
            idx = int(sel.split(":", 1)[0])
            self.selected_device_index.set(idx)
            self._init_audio_ptt()
        except ValueError:
            pass

    def _init_audio_ptt(self):
        if self.ptt_controller:
            self.ptt_controller.shutdown()
            self.ptt_controller = None
        idx = self.selected_device_index.get()
        device_index = idx if idx >= 0 else None
        try:
            self.ptt_controller = PTTSTTController(self.event_queue, device_index=device_index)
            self.status_audio.set("Audio : pret (PTT actif)")
        except Exception as e:
            logger.exception("Erreur init PTTSTTController")
            self.status_audio.set(f"Audio : ERREUR -> {e}")
            messagebox.showerror("Erreur audio", str(e))

    def _start_joystick_thread(self):
        self.joy_running = True
        threading.Thread(target=self._joystick_worker, daemon=True).start()

    def _joystick_worker(self):
        pygame.init()
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        logger.info(f"[JS] {count} joystick(s) detecte(s)")
        if MOZA_JOYSTICK_ID >= count:
            self.event_queue.put(("JS_ERROR", f"Aucun joystick ID {MOZA_JOYSTICK_ID}"))
            return
        js = pygame.joystick.Joystick(MOZA_JOYSTICK_ID)
        js.init()
        logger.info(f"[JS] {js.get_name()} (boutons={js.get_numbuttons()})")
        self.event_queue.put(("JS_OK", js.get_name()))
        last = 0
        while self.joy_running:
            pygame.event.pump()
            try:
                state = js.get_button(BOX_BUTTON_ID)
            except pygame.error as e:
                self.event_queue.put(("JS_ERROR", str(e)))
                break
            if state == 1 and last == 0:
                self.event_queue.put(("BOX_PRESSED", None))
            elif state == 0 and last == 1:
                self.event_queue.put(("BOX_RELEASED", None))
            last = state
            time.sleep(0.01)
        pygame.quit()

    def _process_events(self):
        try:
            while True:
                evt, payload = self.event_queue.get_nowait()
                if evt == "JS_OK":
                    self.status_box.set(f"Volant : OK ({payload}) - PTT pret")
                elif evt == "JS_ERROR":
                    self.status_box.set(f"Volant : ERREUR -> {payload}")
                elif evt == "BOX_PRESSED":
                    self.status_box.set("Volant : Box ENFONCE - enregistrement...")
                    if self.ptt_controller:
                        self.ptt_controller.start_session()
                elif evt == "BOX_RELEASED":
                    self.status_box.set("Volant : Box RELACHE - transcription...")
                    self.status_asr.set("ASR : en cours...")
                    if self.ptt_controller:
                        self.ptt_controller.stop_session()
                elif evt == "ASR_RESULT":
                    text = (payload or "").strip()
                    self.transcription_widget.delete("1.0", tk.END)
                    self.transcription_widget.insert("1.0", text)
                    self.status_asr.set("ASR : OK")
        except queue.Empty:
            pass
        self.after(50, self._process_events)

    def _on_quit(self):
        self.joy_running = False
        if self.ptt_controller:
            self.ptt_controller.shutdown()
        self.destroy()


# --------------------------------------------------------------------- MAIN

if __name__ == "__main__":
    app = F1AssistantApp()
    app.mainloop()
