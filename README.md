# F1 Voice Engineer

> Assistant vocal IA pour F1 25 — push-to-talk sur volant Moza, reconnaissance vocale offline, LLM et TTS.

[![GitHub Pages](https://img.shields.io/badge/Site-GitHub%20Pages-blue?logo=github)](https://nkz21.github.io/f1-voice-engineer/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Fonctionnalites

- **Push-to-talk** sur le bouton Box du volant Moza (joystick pygame)
- **Capture vocale en streaming** — aucun fichier temporaire cree
- **Reconnaissance vocale offline** via Vosk (modele FR local)
- **Telemetrie F1 25** via UDP port 20777 (en cours d'integration)
- **LLM** : envoi de la question + contexte course a une IA (OpenAI ou local)
- **TTS** : reponse audio comme un vrai ingenieur de course
- **UI desktop** propre avec tkinter

---

## Structure du projet

```
f1-voice-engineer/
├─ app/
│  ├─ f1_assistant_vosk_ptt.py   # Application principale
│  └─ requirements.txt
├─ site/
│  ├─ index.html                 # Landing page GitHub Pages
│  └─ style.css
└─ README.md
```

---

## Installation rapide (Windows)

```bash
git clone https://github.com/nkz21/f1-voice-engineer.git
cd f1-voice-engineer
python -m venv .venv
.venv\Scripts\activate
pip install -r app/requirements.txt
```

Telecharger un modele Vosk FR (ex. `vosk-model-small-fr-0.22`) et mettre a jour `VOSK_MODEL_PATH` dans `app/f1_assistant_vosk_ptt.py`, puis :

```bash
python app/f1_assistant_vosk_ptt.py
```

---

## Stack technique

| Composant | Technologie |
|-----------|------------|
| UI | Python tkinter |
| Input volant | pygame.joystick |
| Audio | sounddevice (streaming) |
| STT | Vosk (offline) |
| Telemetrie | UDP F1 25 (port 20777) |
| LLM | OpenAI / modele local |
| TTS | pyttsx3 / API TTS |

---

## Roadmap

- [x] Push-to-talk bouton Box volant Moza
- [x] Capture audio streaming (sans fichier temporaire)
- [x] Reconnaissance vocale Vosk offline
- [ ] Integration telemetrie F1 25 complete
- [ ] LLM avec prompt tyre/fuel/gap
- [ ] TTS reponse vocale
- [ ] Build Windows .exe (PyInstaller + GitHub Actions)

---

## Liens

- Site : https://nkz21.github.io/f1-voice-engineer/
- Repo : https://github.com/nkz21/f1-voice-engineer

---

Developpe par [nkz21](https://github.com/nkz21) — open source MIT
