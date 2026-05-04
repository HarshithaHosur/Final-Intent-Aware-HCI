# 🔥 Here's Your Code with Level 1 + Level 3 AI Added
# 📦 First, Install New Dependencies
# 📄 Updated Code — `smart_assistant.py`
# ============================================================
#  GESTVOICE SMART ASSISTANT — Complete System + AI
#  Hackathon Project
#  Features: Hand Activation (3.5s stable) → Gesture + Voice
#            Context Awareness + 45s Inactivity Timer
#  AI: Fuzzy Matching + Intent Classification
# ============================================================

import cv2
import mediapipe as mp
import time
import math
import speech_recognition as sr
import pyttsx3
import threading
import pyautogui
import subprocess
import os
import sys
import io
import webbrowser
from PIL import Image
from cursor_control import CursorController

# Force UTF-8 encoding for Windows console to handle emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
#                     🆕 AI IMPORTS
# ============================================================
from fuzzywuzzy import fuzz, process
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import numpy as np
import google.generativeai as genai

# Prevent pyautogui from throwing errors at screen edge
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02

# ============================================================
#                     CONFIGURATION
# ============================================================

ACTIVATION_TIME = 1.2
STABILITY_THRESHOLD = 80
INACTIVITY_TIMEOUT = 60

SWIPE_THRESHOLD = 50
SWIPE_VERTICAL_LIMIT = 80
GESTURE_COOLDOWN = 0.5
SWIPE_FRAME_WINDOW = 8

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

VOICE_LISTEN_TIMEOUT = 2
VOICE_PHRASE_LIMIT = 4
TTS_RATE = 175
TTS_VOLUME = 0.9

# ============================================================
#                   SYSTEM STATES
# ============================================================

STATE_PASSIVE = "PASSIVE"
STATE_ACTIVATING = "ACTIVATING"
STATE_ACTIVE = "ACTIVE"
STATE_DICTATION = "DICTATION"

# ============================================================
#                 MEDIAPIPE SETUP
# ============================================================

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.6
)
mp_draw = mp.solutions.drawing_utils

LANDMARK_STYLE = mp_draw.DrawingSpec(color=(180, 0, 200), thickness=2, circle_radius=5)
CONNECTION_STYLE = mp_draw.DrawingSpec(color=(200, 0, 200), thickness=2)

# ============================================================
#                   TTS ENGINE SETUP
# ============================================================

engine = pyttsx3.init()
voices = engine.getProperty('voices')

for v in voices:
    if any(name in v.name.lower() for name in ['female', 'zira', 'hazel', 'samantha']):
        engine.setProperty('voice', v.id)
        break

engine.setProperty('rate', TTS_RATE)
engine.setProperty('volume', TTS_VOLUME)

# ============================================================
#                  VOICE RECOGNITION SETUP
# ============================================================

recognizer = sr.Recognizer()
# HYPER-FAST voice capturing -> changed to natural pacing for users who speak slower
recognizer.pause_threshold = 0.80     # Wait 0.8s of silence before cutting off (default is 0.8)
recognizer.non_speaking_duration = 0.50 # Keep audio buffer for natural pauses
# Adjustments for noisy background and picking up distant voices (earphones)
recognizer.dynamic_energy_threshold = True
recognizer.dynamic_energy_ratio = 1.2  # Less aggressive cutoff
recognizer.energy_threshold = 150      # Lower threshold to pick up quiet/distant voices easily

mic = sr.Microphone()

# ============================================================
#                  THREADING FLAGS
# ============================================================

tts_busy = threading.Event()
voice_command_result = {"text": None, "lock": threading.Lock()}

# ============================================================
#               CONTEXT AWARENESS MODULE
# ============================================================

def get_active_window_title():
    try:
        import pygetwindow as gw
        active = gw.getActiveWindow()
        if active:
            return active.title.lower()
    except Exception:
        pass
    return ""


def detect_context():
    title = get_active_window_title()
    if any(kw in title for kw in ['powerpoint', 'pptx', '.ppt', 'slide']):
        return 'powerpoint'
    elif any(kw in title for kw in ['chrome', 'firefox', 'edge', 'opera', 'brave', 'browser']):
        return 'browser'
    elif any(kw in title for kw in ['spotify', 'music', 'groove']):
        return 'spotify'
    elif any(kw in title for kw in ['vlc', 'media player', 'movies', 'video']):
        return 'vlc'
    elif any(kw in title for kw in ['code', 'visual studio', 'vscode', 'pycharm', 'sublime']):
        return 'code_editor'
    elif any(kw in title for kw in ['explorer', 'file', 'folder', 'this pc']):
        return 'file_explorer'
    elif any(kw in title for kw in ['notepad', 'word', '.docx', '.txt']):
        return 'text_editor'
    else:
        return 'default'


# ============================================================
#            CONTEXT-AWARE GESTURE ACTION MAPPING
# ============================================================

GESTURE_ACTION_MAP = {
    'swipe_right': {
        'powerpoint':    ('key', 'right',              'Next Slide'),
        'browser':       ('hotkey', ['alt', 'right'],   'Forward'),
        'spotify':       ('hotkey', ['ctrl', 'right'],  'Next Song'),
        'vlc':           ('hotkey', ['shift', 'right'], 'Skip Forward'),
        'code_editor':   ('hotkey', ['ctrl', 'pagedown'], 'Next Tab'),
        'file_explorer': ('hotkey', ['alt', 'right'],   'Forward'),
        'text_editor':   ('hotkey', ['ctrl', 'right'],  'Next Word'),
        'default':       ('key', 'right',              'Right Arrow'),
    },
    'swipe_left': {
        'powerpoint':    ('key', 'left',               'Previous Slide'),
        'browser':       ('hotkey', ['alt', 'left'],    'Back'),
        'spotify':       ('hotkey', ['ctrl', 'left'],   'Previous Song'),
        'vlc':           ('hotkey', ['shift', 'left'],  'Skip Backward'),
        'code_editor':   ('hotkey', ['ctrl', 'pageup'], 'Previous Tab'),
        'file_explorer': ('hotkey', ['alt', 'left'],    'Back'),
        'text_editor':   ('hotkey', ['ctrl', 'left'],   'Previous Word'),
        'default':       ('key', 'left',               'Left Arrow'),
    },
    'fist': {
        'powerpoint':    ('key', 'escape',             'Exit Slideshow'),
        'browser':       ('key', 'space',              'Pause/Scroll'),
        'spotify':       ('key', 'space',              'Play/Pause'),
        'vlc':           ('key', 'space',              'Play/Pause'),
        'code_editor':   ('hotkey', ['ctrl', 's'],     'Save File'),
        'file_explorer': ('key', 'escape',             'Close/Go Up'),
        'text_editor':   ('hotkey', ['ctrl', 's'],     'Save'),
        'default':       ('key', 'space',              'Play/Pause'),
    },
    'thumbs_up': {
        'powerpoint':    ('hotkey', ['ctrl', 'shift', 'right'], 'Volume Up'),
        'browser':       ('hotkey', ['ctrl', 'plus'],  'Zoom In'),
        'spotify':       ('key', 'volumeup',           'Volume Up'),
        'vlc':           ('key', 'volumeup',           'Volume Up'),
        'code_editor':   ('hotkey', ['ctrl', 'plus'],  'Zoom In'),
        'file_explorer': ('hotkey', ['ctrl', 'plus'],  'Zoom In'),
        'text_editor':   ('hotkey', ['ctrl', 'plus'],  'Zoom In'),
        'default':       ('key', 'volumeup',           'Volume Up'),
    },
    'thumbs_down': {
        'powerpoint':    ('hotkey', ['ctrl', 'shift', 'left'], 'Volume Down'),
        'browser':       ('hotkey', ['ctrl', 'minus'], 'Zoom Out'),
        'spotify':       ('key', 'volumedown',         'Volume Down'),
        'vlc':           ('key', 'volumedown',         'Volume Down'),
        'code_editor':   ('hotkey', ['ctrl', 'minus'], 'Zoom Out'),
        'file_explorer': ('hotkey', ['ctrl', 'minus'], 'Zoom Out'),
        'text_editor':   ('hotkey', ['ctrl', 'minus'], 'Zoom Out'),
        'default':       ('key', 'volumedown',         'Volume Down'),
    }
}


# ============================================================
#              VOICE COMMAND ACTION MAPPING
# ============================================================

VOICE_COMMANDS = {
    'open chrome':         lambda: subprocess.Popen(['start', 'chrome'], shell=True),
    'open browser':        lambda: subprocess.Popen(['start', 'chrome'], shell=True),
    'open notepad':        lambda: subprocess.Popen(['notepad.exe']),
    'open calculator':     lambda: subprocess.Popen(['calc.exe']),
    'open file explorer':  lambda: subprocess.Popen(['explorer.exe']),
    'open settings':       lambda: subprocess.Popen(['start', 'ms-settings:'], shell=True),
    'open spotify':        lambda: subprocess.Popen(['start', 'spotify:'], shell=True),
    'open whatsapp':       lambda: subprocess.Popen(['start', 'whatsapp:'], shell=True),
    'open word':           lambda: subprocess.Popen(['start', 'winword'], shell=True),
    'open excel':          lambda: subprocess.Popen(['start', 'excel'], shell=True),
    'open powerpoint':     lambda: subprocess.Popen(['start', 'powerpnt'], shell=True),
    'open vs code':        lambda: subprocess.Popen(['start', 'code'], shell=True),
    'open visual studio':  lambda: subprocess.Popen(['start', 'code'], shell=True),
    'open command prompt': lambda: subprocess.Popen(['cmd.exe']),
    'open terminal':       lambda: subprocess.Popen(['cmd.exe']),
    'open task manager':   lambda: subprocess.Popen(['taskmgr.exe']),
    'search drive d':      lambda: subprocess.Popen(['explorer.exe', 'D:\\']),
    'close window':        lambda: pyautogui.hotkey('alt', 'F4'),
    'minimize window':     lambda: pyautogui.hotkey('win', 'down'),
    'maximize window':     lambda: pyautogui.hotkey('win', 'up'),
    'switch window':       lambda: pyautogui.hotkey('alt', 'tab'),
    'show desktop':        lambda: pyautogui.hotkey('win', 'd'),
    'snap left':           lambda: pyautogui.hotkey('win', 'left'),
    'snap right':          lambda: pyautogui.hotkey('win', 'right'),
    'new tab':             lambda: pyautogui.hotkey('ctrl', 't'),
    'close tab':           lambda: pyautogui.hotkey('ctrl', 'w'),
    'reopen tab':          lambda: pyautogui.hotkey('ctrl', 'shift', 't'),
    'play':                lambda: pyautogui.press('playpause'),
    'pause':               lambda: pyautogui.press('playpause'),
    'play pause':          lambda: pyautogui.press('playpause'),
    'next song':           lambda: pyautogui.press('nexttrack'),
    'previous song':       lambda: pyautogui.press('prevtrack'),
    'volume up':           lambda: [pyautogui.press('volumeup') for _ in range(5)],
    'volume down':         lambda: [pyautogui.press('volumedown') for _ in range(5)],
    'mute':                lambda: pyautogui.press('volumemute'),
    'unmute':              lambda: pyautogui.press('volumemute'),
    'take screenshot':     lambda: pyautogui.hotkey('win', 'shift', 's'),
    'screenshot':          lambda: pyautogui.hotkey('win', 'shift', 's'),
    'lock screen':         lambda: pyautogui.hotkey('win', 'l'),
    'search':              lambda: pyautogui.hotkey('win', 's'),
    'select all':          lambda: pyautogui.hotkey('ctrl', 'a'),
    'copy':                lambda: pyautogui.hotkey('ctrl', 'c'),
    'paste':               lambda: pyautogui.hotkey('ctrl', 'v'),
    'cut':                 lambda: pyautogui.hotkey('ctrl', 'x'),
    'undo':                lambda: pyautogui.hotkey('ctrl', 'z'),
    'redo':                lambda: pyautogui.hotkey('ctrl', 'y'),
    'save':                lambda: pyautogui.hotkey('ctrl', 's'),
    'find':                lambda: pyautogui.hotkey('ctrl', 'f'),
    'start presentation':  lambda: pyautogui.press('F5'),
    'start slideshow':     lambda: pyautogui.press('F5'),
    'end presentation':    lambda: pyautogui.press('escape'),
    'next slide':          lambda: pyautogui.press('right'),
    'previous slide':      lambda: pyautogui.press('left'),
    'scroll up':           lambda: pyautogui.scroll(5),
    'scroll down':         lambda: pyautogui.scroll(-5),
    'page up':             lambda: pyautogui.press('pageup'),
    'page down':           lambda: pyautogui.press('pagedown'),
}


# ============================================================
#       🆕 LEVEL 3: AI VOICE INTENT CLASSIFIER
# ============================================================

class VoiceIntentClassifier:
    """
    AI-based intent recognition for voice commands.
    Uses TF-IDF + Naive Bayes to understand user intent
    even with different wording. Enhanced with 30+ intents.
    """
    
    def __init__(self):
        self.training_data = {
            'open_chrome': [
                'open chrome', 'launch chrome', 'start chrome',
                'open google chrome', 'launch browser', 'start browser',
                'open the browser', 'i want chrome', 'chrome open please',
                'can you open chrome', 'fire up chrome', 'fire up the browser',
                'use chrome', 'use chromee', 'get me chrome', 'browser please',
                'open my browser', 'go to chrome', 'run chrome',
            ],
            'open_notepad': [
                'open notepad', 'launch notepad', 'start notepad',
                'open text editor', 'open notes', 'notepad please',
                'run notepad', 'get notepad', 'text editor',
            ],
            'open_calculator': [
                'open calculator', 'launch calculator', 'start calculator',
                'calculator', 'open calc', 'i need calculator',
            ],
            'open_settings': [
                'open settings', 'launch settings', 'system settings',
                'windows settings', 'go to settings', 'preferences',
            ],
            'open_file_explorer': [
                'open file explorer', 'open explorer', 'open files',
                'file manager', 'my files', 'open my computer', 'this pc',
            ],
            'open_spotify': [
                'open spotify', 'launch spotify', 'start spotify',
                'play spotify', 'music app', 'open music',
            ],
            'open_whatsapp': [
                'open whatsapp', 'launch whatsapp', 'start whatsapp',
                'whatsapp please', 'go to whatsapp',
            ],
            'open_word': [
                'open word', 'launch word', 'start word',
                'microsoft word', 'open document editor', 'ms word',
            ],
            'open_excel': [
                'open excel', 'launch excel', 'start excel',
                'spreadsheet', 'microsoft excel', 'ms excel',
            ],
            'open_powerpoint': [
                'open powerpoint', 'launch powerpoint', 'start powerpoint',
                'presentation app', 'microsoft powerpoint', 'ppt', 'ms powerpoint',
            ],
            'open_vscode': [
                'open vs code', 'launch vs code', 'open visual studio code',
                'start vs code', 'open code editor', 'vscode', 'visual studio',
            ],
            'open_terminal': [
                'open terminal', 'launch terminal', 'open command prompt',
                'open cmd', 'command line', 'start terminal', 'run cmd',
            ],
            'open_task_manager': [
                'open task manager', 'task manager', 'launch task manager',
                'show processes', 'system monitor',
            ],
            'close_window': [
                'close window', 'close this', 'shut this window',
                'close the window', 'exit window', 'kill this window',
                'close it', 'shut it down', 'close the app', 'close app',
            ],
            'play_pause': [
                'play', 'pause', 'play music', 'pause music',
                'start playing', 'stop playing', 'resume',
                'play the song', 'pause the song', 'play it',
                'stop the music', 'continue playing', 'play pause',
            ],
            'next_track': [
                'next song', 'next track', 'skip song', 'skip this',
                'play next', 'next one', 'skip to next',
                'change song', 'forward song',
            ],
            'previous_track': [
                'previous song', 'last song', 'go back',
                'play previous', 'previous track', 'back one song',
            ],
            'volume_up': [
                'volume up', 'louder', 'increase volume',
                'turn it up', 'make it louder', 'raise volume',
                'more volume', 'crank it up',
            ],
            'volume_down': [
                'volume down', 'softer', 'decrease volume',
                'turn it down', 'make it quieter', 'lower volume',
                'less volume', 'reduce volume',
            ],
            'mute_unmute': [
                'mute', 'unmute', 'mute audio', 'unmute audio',
                'toggle mute', 'silence', 'mute sound',
            ],
            'take_screenshot': [
                'take screenshot', 'screenshot', 'capture screen',
                'take a screenshot', 'screen capture', 'snap screen',
                'print screen', 'capture this',
            ],
            'minimize': [
                'minimize', 'minimize window', 'hide window',
                'put it down', 'minimize this',
            ],
            'maximize': [
                'maximize', 'maximize window', 'full screen',
                'make it bigger', 'maximize this', 'fullscreen',
            ],
            'switch_window': [
                'switch window', 'alt tab', 'change window',
                'go to other window', 'switch app', 'next window',
            ],
            'show_desktop': [
                'show desktop', 'go to desktop', 'minimize all',
                'desktop', 'hide all windows',
            ],
            'save_file': [
                'save', 'save file', 'save this', 'save it',
                'save the file', 'ctrl s',
            ],
            'copy_text': [
                'copy', 'copy this', 'copy text', 'copy it', 'copy that',
            ],
            'paste_text': [
                'paste', 'paste this', 'paste text', 'paste it', 'paste that',
            ],
            'cut_text': [
                'cut', 'cut this', 'cut text', 'cut it',
            ],
            'undo_action': [
                'undo', 'undo that', 'undo this', 'go back', 'reverse',
            ],
            'redo_action': [
                'redo', 'redo that', 'redo this',
            ],
            'select_all': [
                'select all', 'select everything', 'highlight all',
            ],
            'find_text': [
                'find', 'search', 'find text', 'search for text', 'ctrl f',
            ],
            'new_tab': [
                'new tab', 'open new tab', 'open tab', 'add tab',
            ],
            'close_tab': [
                'close tab', 'close this tab', 'shut tab',
            ],
            'reopen_tab': [
                'reopen tab', 'restore tab', 'bring back tab', 'undo close tab',
            ],
            'next_slide': [
                'next slide', 'go to next slide', 'forward slide', 'next page',
            ],
            'previous_slide': [
                'previous slide', 'go back slide', 'last slide', 'back slide',
            ],
            'start_presentation': [
                'start presentation', 'start slideshow', 'begin presentation',
                'present', 'slideshow', 'begin slideshow',
            ],
            'scroll_up': [
                'scroll up', 'go up', 'page up', 'move up',
            ],
            'scroll_down': [
                'scroll down', 'go down', 'page down', 'move down',
            ],
            'lock_screen': [
                'lock screen', 'lock computer', 'lock pc', 'lock',
            ],
            'snap_left': [
                'snap left', 'move window left', 'window left',
            ],
            'snap_right': [
                'snap right', 'move window right', 'window right',
            ],
            'search_web': [
                'search for', 'google', 'look up', 'search the web',
                'web search', 'search online',
            ],
        }
        
        texts = []
        labels = []
        for intent, examples in self.training_data.items():
            for example in examples:
                texts.append(example)
                labels.append(intent)
        
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=1000,
                stop_words='english'
            )),
            ('classifier', MultinomialNB(alpha=0.1))
        ])
        
        self.pipeline.fit(texts, labels)
        print("[🧠 AI] Voice Intent Classifier trained with 40+ intents!")
    
    def predict_intent(self, user_text):
        user_text = user_text.lower().strip()
        prediction = self.pipeline.predict([user_text])[0]
        probabilities = self.pipeline.predict_proba([user_text])[0]
        confidence = max(probabilities)
        if confidence > 0.35:
            return prediction, confidence
        return 'unknown', confidence


# Map intents to actions
INTENT_ACTIONS = {
    'open_chrome':       lambda t: subprocess.Popen(['start', 'chrome'], shell=True),
    'open_notepad':      lambda t: subprocess.Popen(['notepad.exe']),
    'open_calculator':   lambda t: subprocess.Popen(['calc.exe']),
    'open_settings':     lambda t: subprocess.Popen(['start', 'ms-settings:'], shell=True),
    'open_file_explorer':lambda t: subprocess.Popen(['explorer.exe']),
    'open_spotify':      lambda t: subprocess.Popen(['start', 'spotify:'], shell=True),
    'open_whatsapp':     lambda t: subprocess.Popen(['start', 'whatsapp:'], shell=True),
    'open_word':         lambda t: subprocess.Popen(['start', 'winword'], shell=True),
    'open_excel':        lambda t: subprocess.Popen(['start', 'excel'], shell=True),
    'open_powerpoint':   lambda t: subprocess.Popen(['start', 'powerpnt'], shell=True),
    'open_vscode':       lambda t: subprocess.Popen(['start', 'code'], shell=True),
    'open_terminal':     lambda t: subprocess.Popen(['cmd.exe']),
    'open_task_manager': lambda t: subprocess.Popen(['taskmgr.exe']),
    'close_window':      lambda t: pyautogui.hotkey('alt', 'F4'),
    'play_pause':        lambda t: pyautogui.press('playpause'),
    'next_track':        lambda t: pyautogui.press('nexttrack'),
    'previous_track':    lambda t: pyautogui.press('prevtrack'),
    'volume_up':         lambda t: [pyautogui.press('volumeup') for _ in range(5)],
    'volume_down':       lambda t: [pyautogui.press('volumedown') for _ in range(5)],
    'mute_unmute':       lambda t: pyautogui.press('volumemute'),
    'take_screenshot':   lambda t: pyautogui.hotkey('win', 'shift', 's'),
    'minimize':          lambda t: pyautogui.hotkey('win', 'down'),
    'maximize':          lambda t: pyautogui.hotkey('win', 'up'),
    'switch_window':     lambda t: pyautogui.hotkey('alt', 'tab'),
    'show_desktop':      lambda t: pyautogui.hotkey('win', 'd'),
    'save_file':         lambda t: pyautogui.hotkey('ctrl', 's'),
    'copy_text':         lambda t: pyautogui.hotkey('ctrl', 'c'),
    'paste_text':        lambda t: pyautogui.hotkey('ctrl', 'v'),
    'cut_text':          lambda t: pyautogui.hotkey('ctrl', 'x'),
    'undo_action':       lambda t: pyautogui.hotkey('ctrl', 'z'),
    'redo_action':       lambda t: pyautogui.hotkey('ctrl', 'y'),
    'select_all':        lambda t: pyautogui.hotkey('ctrl', 'a'),
    'find_text':         lambda t: pyautogui.hotkey('ctrl', 'f'),
    'new_tab':           lambda t: pyautogui.hotkey('ctrl', 't'),
    'close_tab':         lambda t: pyautogui.hotkey('ctrl', 'w'),
    'reopen_tab':        lambda t: pyautogui.hotkey('ctrl', 'shift', 't'),
    'next_slide':        lambda t: pyautogui.press('right'),
    'previous_slide':    lambda t: pyautogui.press('left'),
    'start_presentation':lambda t: pyautogui.press('F5'),
    'scroll_up':         lambda t: pyautogui.scroll(5),
    'scroll_down':       lambda t: pyautogui.scroll(-5),
    'lock_screen':       lambda t: pyautogui.hotkey('win', 'l'),
    'snap_left':         lambda t: pyautogui.hotkey('win', 'left'),
    'snap_right':        lambda t: pyautogui.hotkey('win', 'right'),
    'search_web':        lambda t: webbrowser.open(f"https://www.google.com/search?q={t}"),
}


# Initialize AI classifier
intent_classifier = VoiceIntentClassifier()

# ============================================================
#   🆕 LEVEL 4: SMART GENERATIVE AI (DO ANYTHING MODE)
# ============================================================

# API key: uses env var if set, otherwise falls back to hardcoded key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAdLzpi_OJOwf6jLQiTROSkDdz2GkmqvXw")

try:
    if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_API_KEY_HERE":
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        gemini_model = None
except Exception:
    gemini_model = None

# ============================================================
#              NOISE FILTERING & TEXT CLEANUP
# ============================================================

FILLER_WORDS = {'um', 'uh', 'like', 'so', 'please', 'just', 'actually',
                'basically', 'literally', 'okay', 'ok', 'well', 'right'}

NOISE_PHRASES = [
    'yeah', 'hmm', 'huh', 'ah', 'oh', 'what', 'hello', 'hi',
    'you know', 'i mean', 'never mind', 'no no', 'wait wait',
]

def clean_command_text(text):
    """Remove filler words and clean up command text."""
    words = text.split()
    cleaned = [w for w in words if w not in FILLER_WORDS]
    result = ' '.join(cleaned).strip()
    return result if result else text

def is_noise(text):
    """Check if text is background noise / not a real command."""
    if len(text) < 2:
        return True
    if text in NOISE_PHRASES:
        return True
    return False

# ============================================================
#         ROBUST "BOSS" PREFIX DETECTION (FUZZY & ACCENTS)
# ============================================================

BOSS_EXACT_PREFIXES = [
    'boss', 'bos', 'baas', 'boos', 'baws', 'bosh', 'bose', 'bus'
]

BOSS_TWO_WORD_PREFIXES = [
    'hey boss', 'ok boss', 'okay boss', 'hey bos', 'hey baas',
    'ok bos', 'ok baas'
]

def normalize_indian_accents(text):
    """Normalize Indian pronunciation variations for voice commands."""
    text = text.lower().strip()
    
    # Prefix spaces to avoid partial word replacements if needed, but simple replaces work well
    # for these specific phonetic misrecognitions
    replacements = {
        ' bos ': ' boss ', ' baas ': ' boss ', ' boos ': ' boss ', ' baws ': ' boss ',
        ' opun ': ' open ', ' opan ': ' open ', 
        ' krome': ' chrome', ' crome': ' chrome',
        'not ped': 'notepad', 'note pad': 'notepad', 'notpad': 'notepad',
    }
    
    # Pad text to handle first-word replacements reliably with spaces
    padded = f" {text} "
    for old, new in replacements.items():
        padded = padded.replace(old, new)
        
    return padded.strip()

def extract_boss_command(text):
    """
    Extract the command after the 'Boss' prefix.
    Returns:
      - command string if Boss prefix found
      - '' (empty) if just 'Boss' was said with no command
      - None if no Boss prefix detected
    """
    text = text.lower().strip()
    words = text.split()
    if not words:
        return None
    
    if len(words) >= 2:
        two_word = words[0] + ' ' + words[1]
        for prefix in BOSS_TWO_WORD_PREFIXES:
            if two_word == prefix:
                return ' '.join(words[2:]).strip()
        if fuzz.ratio(two_word, 'hey boss') > 65:
            return ' '.join(words[2:]).strip()
    
    first = words[0]
    for prefix in BOSS_EXACT_PREFIXES:
        if first == prefix:
            return ' '.join(words[1:]).strip()
            
    if fuzz.ratio(first, 'boss') > 60:
        return ' '.join(words[1:]).strip()
        
    return None

# ============================================================
#          INDEX FINGER POINTING DETECTION (for cursor)
# ============================================================

def is_index_pointing(landmarks, handedness='Right'):
    """Check if only index finger is extended (pointing gesture for cursor)."""
    tips = [4, 8, 12, 16, 20]
    pips = [2, 5, 9, 13, 17]
    index_up = landmarks[tips[1]].y < landmarks[pips[1]].y
    middle_down = landmarks[tips[2]].y >= landmarks[pips[2]].y
    ring_down = landmarks[tips[3]].y >= landmarks[pips[3]].y
    pinky_down = landmarks[tips[4]].y >= landmarks[pips[4]].y
    return index_up and middle_down and ring_down and pinky_down

def execute_smart_ai_command(text):
    if not gemini_model:
        return False
    
    prompt = f"""You are a Windows voice assistant. User says: "{text}"
Write Python code using 'pyautogui', 'os', 'subprocess', or 'time' to fulfill the request.
- To open an unmapped app or folder universally, use Windows Search: `pyautogui.hotkey('win', 's'); time.sleep(0.5); pyautogui.write('target_name', interval=0.01); time.sleep(0.5); pyautogui.press('enter')`
- To type strictly requested dictation, use `pyautogui.write('...', interval=0.02)`.
- If opening an app AND typing, use `time.sleep(3.0)` between opening and typing.
- [CRITICAL NOISE FILTER]: If the text looks like fragmented background static, overlapping room conversations, or random nonsense (e.g., "yeah okay", "what time is it over there"), silently ignore it and return exactly the word NONE.
Return ONLY raw Python code. Do NOT wrap in markdown or backticks. If impossible or if it is just noise, return NONE.
"""
    try:
        response = gemini_model.generate_content(prompt)
        code = response.text.strip()
        
        # Clean up possible markdown code blocks from Gemini
        if code.startswith("```"):
            lines = code.split("\n")
            if len(lines) >= 3:
                code = "\n".join(lines[1:-1])
        code = code.replace("`", "").strip()
        if code.startswith("python"):
            code = code[6:].strip()
            
        if code and code.upper() != "NONE":
            print(f"[Smart AI] Executing generated code:\n{code}")
            # Dynamic execution allows the AI to control the laptop natively
            exec(code, {"os": os, "subprocess": subprocess, "pyautogui": pyautogui, "time": time})
            return True
    except Exception as e:
        print(f"[Smart AI Error] {e}")
    return False

def execute_vision_command(text):
    """
    Takes a screenshot and asks Gemini to analyze the screen for visual actions.
    """
    if not gemini_model:
        return False
    
    try:
        # 1. Take a temporary screenshot
        screenshot = pyautogui.screenshot()
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # 2. Formulate the vision-aware prompt
        res_w, res_h = pyautogui.size()
        prompt = f"""You are a Windows Vision Assistant.
Current Screen Resolution: {res_w}x{res_h}
User Request: "{text}"
Look at the attached screen image.
- If they want to open a video or click a button, find the [X, Y] center coordinates.
- Format your response as raw Python: `pyautogui.click(X, Y)`
- If it's a video on YouTube, find the thumbnail center.
- Use `pyautogui.moveTo(X, Y)` before clicking for smoothness.
- If you can't see the target, return NONE.
Return ONLY raw Python code.
"""
        # Note: Gemini 1.5 Flash supports multimodal image input
        response = gemini_model.generate_content([
            prompt, 
            {"mime_type": "image/png", "data": img_byte_arr}
        ])
        
        code = response.text.strip().replace("`", "").replace("python", "").strip()
        if code and code.upper() != "NONE":
            print(f"[Vision Brain] Executing: {code}")
            exec(code, {"pyautogui": pyautogui, "time": time})
            return True
    except Exception as e:
        print(f"[Vision Error] {e}")
    return False


# ============================================================
#              GESTURE RECOGNITION MODULE
# ============================================================

class GestureRecognizer:
    """Recognizes static gestures and dynamic swipes from hand landmarks."""

    def __init__(self):
        self.wrist_history = []
        self.last_gesture_time = 0
        self.frame_count = 0

    def get_finger_states(self, landmarks, handedness='Right'):
        tips = [4, 8, 12, 16, 20]
        pips = [2, 5, 9, 13, 17]
        states = []
        if handedness == 'Right':
            states.append(landmarks[tips[0]].x < landmarks[pips[0]].x)
        else:
            states.append(landmarks[tips[0]].x > landmarks[pips[0]].x)
        for i in range(1, 5):
            states.append(landmarks[tips[i]].y < landmarks[pips[i]].y)
        return states

    def detect_static_gesture(self, landmarks, handedness='Right'):
        fingers = self.get_finger_states(landmarks, handedness)
        thumb_up = fingers[0]
        other_fingers = fingers[1:]
        all_others_closed = not any(other_fingers)
        all_closed = not any(fingers)
        if all_closed or (not thumb_up and all_others_closed):
            return 'fist'
        if thumb_up and all_others_closed:
            wrist_y = landmarks[0].y
            middle_base_y = landmarks[9].y
            if wrist_y > middle_base_y:
                return 'thumbs_up'
            else:
                return 'thumbs_down'
        return None

    def detect_swipe(self, landmarks, frame_width):
        wrist = landmarks[0]
        wrist_x = int(wrist.x * frame_width)
        wrist_y = int(wrist.y * CAMERA_HEIGHT)
        self.wrist_history.append((wrist_x, wrist_y, time.time()))
        if len(self.wrist_history) > SWIPE_FRAME_WINDOW:
            self.wrist_history.pop(0)
        if len(self.wrist_history) < SWIPE_FRAME_WINDOW:
            return None
        start_x, start_y, start_t = self.wrist_history[0]
        end_x, end_y, end_t = self.wrist_history[-1]
        dx = end_x - start_x
        dy = abs(end_y - start_y)
        time_diff = end_t - start_t
        if time_diff > 0.6:
            return None
        if abs(dx) > SWIPE_THRESHOLD and dy < SWIPE_VERTICAL_LIMIT:
            self.wrist_history.clear()
            return 'swipe_right' if dx > 0 else 'swipe_left'
        return None

    def recognize(self, landmarks, handedness, frame_width):
        current_time = time.time()
        if current_time - self.last_gesture_time < GESTURE_COOLDOWN:
            self.detect_swipe(landmarks, frame_width)
            return None
        static = self.detect_static_gesture(landmarks, handedness)
        if static:
            self.last_gesture_time = current_time
            self.wrist_history.clear()
            return static
        swipe = self.detect_swipe(landmarks, frame_width)
        if swipe:
            self.last_gesture_time = current_time
            return swipe
        return None


# ============================================================
#              ACTION EXECUTOR MODULE
# ============================================================

def execute_gesture_action(gesture_name, context):
    if gesture_name not in GESTURE_ACTION_MAP:
        return None
    context_map = GESTURE_ACTION_MAP[gesture_name]
    action = context_map.get(context, context_map.get('default'))
    if not action:
        return None
    action_type, action_value, description = action
    try:
        if action_type == 'key':
            pyautogui.press(action_value)
        elif action_type == 'hotkey':
            pyautogui.hotkey(*action_value)
    except Exception as e:
        print(f"[Action Error] {e}")
    return description


# ============================================================
#   🆕 ENHANCED VOICE COMMAND EXECUTOR WITH AI
# ============================================================

def execute_voice_command(text):
    """
    Execute voice command using AI pipeline:
    1. Special commands (type, search, folder, scroll)
    2. AI Intent Classifier
    3. Fuzzy Matching
    4. Dynamic app opener (Windows Search)
    5. Generative AI (Gemini - do ANYTHING)
    """
    text = text.lower().strip()
    
    # Skip noise
    if is_noise(text):
        return None
    
    # Special commands first: Typing anything
    if text.startswith('type ') or ' type ' in text or text.startswith('write ') or ' write ' in text:
        # Extract everything after 'type' or 'write'
        if 'type ' in text:
            content = text.split('type ', 1)[1].strip()
        else:
            content = text.split('write ', 1)[1].strip()
            
        if content:
            pyautogui.typewrite(content, interval=0.03)
            return f"Typed: {content}"
        return None
    
    if text.startswith('search for '):
        query = text[11:].strip()
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            return f"Searching: {query}"
        return None
    
    # ── Dynamic Folder Searching via os.walk ──
    if 'open ' in text and (' folder' in text or ' directory' in text):
        raw_name = text.replace('open', '').replace('my', '').replace('folder', '').replace('the', '').replace('directory', '').strip()
        if raw_name:
            search_paths = [os.path.expanduser('~'), "D:\\"]
            for base_path in search_paths:
                if not os.path.exists(base_path): continue
                for root, dirs, files in os.walk(base_path):
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in ['appdata', 'windows', 'program files']]
                    for d in dirs:
                        if raw_name in d.lower():
                            os.startfile(os.path.join(root, d))
                            return f"Opened folder: {d}"
                    if root.count(os.sep) - base_path.count(os.sep) > 1:
                        del dirs[:]
    
    # --- Continuous Scroll Logic ---
    if 'scroll down' in text:
        system_state_global['scroll_speed'] = -200
        return "Scrolling down"
    if 'scroll up' in text:
        system_state_global['scroll_speed'] = 200
        return "Scrolling up"
    if 'scroll slowly' in text:
        system_state_global['scroll_speed'] = -80
        return "Scrolling slowly"
    if 'stop scroll' in text or 'stop' == text:
        system_state_global['scroll_speed'] = 0
        return "Scrolling stopped"
        
    # --- Vision Logic (Contextual Screen Actions) ---
    visual_keywords = ['this video', 'play button', 'click this', 'open this', 'on screen']
    if any(kw in text for kw in visual_keywords):
        success = execute_vision_command(text)
        if success: return "Executing visual action"
    
    # ── 🧠 LEVEL 3: Try AI Intent Classification ──
    is_hardcoded = any(text == cmd or text.startswith(cmd) for cmd in VOICE_COMMANDS.keys())
    
    intent, confidence = intent_classifier.predict_intent(text)
    
    if intent != 'unknown' and confidence > 0.5:
        if not (text.startswith('open ') and not is_hardcoded and intent == 'open_chrome'):
            if intent in INTENT_ACTIONS:
                INTENT_ACTIONS[intent](text)
                return f"[AI {int(confidence*100)}%] {intent.replace('_', ' ').title()}"
    
    # ── 🧠 LEVEL 1: Try Fuzzy Matching ──
    command_list = list(VOICE_COMMANDS.keys())
    best_match, fuzzy_score = process.extractOne(
        text, 
        command_list, 
        scorer=fuzz.partial_ratio
    )
    
    if fuzzy_score > 75:
        VOICE_COMMANDS[best_match]()
        return f"[Fuzzy {fuzzy_score}%] {best_match.title()}"
    
    # ── Fallback: Exact/partial keyword match ──
    if text in VOICE_COMMANDS:
        VOICE_COMMANDS[text]()
        return f"Executed: {text}"
    
    for cmd, func in VOICE_COMMANDS.items():
        if cmd in text:
            func()
            return f"Executed: {cmd}"
    
    # ── 🆕 DYNAMIC APP OPENER: Try Windows Search for unknown apps ──
    if text.startswith('open ') or text.startswith('launch ') or text.startswith('start '):
        app_name = text.split(' ', 1)[1].strip()
        if app_name:
            try:
                # Try direct start command first
                subprocess.Popen(['start', app_name], shell=True)
                return f"[Dynamic] Opening: {app_name}"
            except Exception:
                try:
                    # Fallback: Use Windows Search
                    pyautogui.hotkey('win', 's')
                    time.sleep(0.5)
                    pyautogui.write(app_name, interval=0.02)
                    time.sleep(0.5)
                    pyautogui.press('enter')
                    return f"[Search] Opening: {app_name}"
                except Exception:
                    pass
            
    # ── 🧠 LEVEL 4: SMART GENERATIVE AI (DO ANYTHING MODE) ──
    try:
        if 'gemini_model' in globals() and gemini_model:
            success = execute_smart_ai_command(text)
            if success:
                return f"[Gemini AI] Dynamic Action Executed"
    except Exception:
        pass
    
    return None


# ============================================================
#                  TTS SPEAKER MODULE
# ============================================================

def speak(message):
    if tts_busy.is_set():
        return
    def _speak():
        tts_busy.set()
        try:
            engine.say(message)
            engine.runAndWait()
        except Exception:
            pass
        tts_busy.clear()
    threading.Thread(target=_speak, daemon=True).start()


# ============================================================
#              VOICE LISTENER MODULE
# ============================================================

system_state_global = None

def voice_callback(recognizer, audio):
    try:
        # Try recognition with multiple language hints for better accuracy
        text = None
        for lang in ['en-IN', 'en-US']:
            try:
                text = recognizer.recognize_google(audio, language=lang).lower().strip()
                if text:
                    break
            except sr.UnknownValueError:
                continue
        
        if not text:
            return
        
        print(f"[MIC] Heard: '{text}'")
        current_state = system_state_global['state']

        # ── GLOBAL: Deactivate terminates system (no prefix needed) ──
        if any(kw in text for kw in ['deactivate', 'shut down system', 'stop the program']):
            system_state_global['terminate_system'] = True
            speak("Deactivating the system completely. Goodbye!")
            return

        # ── PASSIVE STATE: Listen for activation (no prefix needed) ──
        if current_state == STATE_PASSIVE:
            if 'activate' in text or 'hey assistant' in text or 'wake up' in text:
                system_state_global['voice_activate'] = True
            return

        # ── DICTATION STATE: Type everything (no prefix needed) ──
        elif current_state == STATE_DICTATION:
            if 'stop dictation' in text or 'end dictation' in text or 'exit dictation' in text:
                system_state_global['dictation_stop'] = True
                return
            
            pyautogui.write(text + " ", interval=0.01)
            system_state_global['last_interaction'] = time.time()
            system_state_global['last_action'] = f"Dictating..."
            system_state_global['action_display_time'] = time.time()

        # ── ACTIVE STATE: Require "Boss" prefix for commands ──
        elif current_state == STATE_ACTIVE:
            # Sleep/passive commands work without Boss prefix
            if any(kw in text for kw in ['go to sleep', 'stop listening', 'passive', 'sleep']):
                system_state_global['voice_deactivate'] = True
                speak("Going to sleep.")
                return

            # Apply accent normalization before matching
            text = normalize_indian_accents(text)

            # ── ROBUST "BOSS" PREFIX GATE (fuzzy matching) ──
            command = extract_boss_command(text)
            
            if command == '':
                # User just said "Boss" with no command
                speak("Yes, boss? I'm listening.")
                system_state_global['last_action'] = "🎤 Boss listening..."
                system_state_global['action_display_time'] = time.time()
                return
            
            if command is None:
                # No Boss prefix detected → silently ignore
                return
            
            print(f"[BOSS] Heard: '{text}' → Command: '{command}'")
            
            # Clean up filler words
            command = clean_command_text(command)
            if len(command) < 2:
                return

            # ── Check for dictation mode entry ──
            if any(kw in command for kw in ['start dictation', 'enter dictation', 'dictation mode']):
                system_state_global['dictation_start'] = True
                return

            # ── Check for cursor mode toggle ──
            if any(kw in command for kw in ['cursor mode', 'mouse mode', 'enable cursor', 'enable mouse']):
                system_state_global['cursor_enabled'] = True
                speak("Cursor mode enabled. Point your index finger.")
                system_state_global['last_interaction'] = time.time()
                system_state_global['last_action'] = "🖱️ Cursor mode ON"
                system_state_global['action_display_time'] = time.time()
                return
            
            if any(kw in command for kw in ['stop cursor', 'disable cursor', 'stop mouse', 'disable mouse']):
                system_state_global['cursor_enabled'] = False
                system_state_global['cursor_active'] = False
                speak("Cursor mode disabled.")
                system_state_global['last_interaction'] = time.time()
                system_state_global['last_action'] = "🖱️ Cursor mode OFF"
                system_state_global['action_display_time'] = time.time()
                return

            # ── Process through full AI pipeline ──
            result = execute_voice_command(command)
            if result:
                system_state_global['last_interaction'] = time.time()
                system_state_global['last_action'] = f"🎤 {result}"
                system_state_global['action_display_time'] = time.time()
                speak(f"Done. {result}")
            else:
                system_state_global['last_action'] = f"🎤 Ignored noise"
                system_state_global['action_display_time'] = time.time()

    except sr.UnknownValueError:
        pass
    except Exception as e:
        pass

def voice_listener_loop(system_state_ref):
    global system_state_global
    system_state_global = system_state_ref

    with mic as source:
        # Deep calibration for background noise
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
        # Put a cap on the threshold so that distant voices are still picked up
        if recognizer.energy_threshold > 400:
            recognizer.energy_threshold = 400

    # Uses a dedicated background thread so the mic stream is never dropped
    recognizer.listen_in_background(mic, voice_callback, phrase_time_limit=VOICE_PHRASE_LIMIT)

    while True:
        time.sleep(1)


# ============================================================
#              HAND STABILITY TRACKER
# ============================================================

class StabilityTracker:
    def __init__(self):
        self.positions = []
        self.stable_start_time = None

    def update(self, wrist_x, wrist_y):
        current_time = time.time()
        self.positions.append((wrist_x, wrist_y, current_time))
        if len(self.positions) > 15:
            self.positions.pop(0)
        if len(self.positions) < 5:
            return False, 0
        xs = [p[0] for p in self.positions]
        ys = [p[1] for p in self.positions]
        x_range = max(xs) - min(xs)
        y_range = max(ys) - min(ys)
        is_stable = (x_range < STABILITY_THRESHOLD) and (y_range < STABILITY_THRESHOLD)
        if is_stable:
            if self.stable_start_time is None:
                self.stable_start_time = current_time
            elapsed = current_time - self.stable_start_time
            return True, elapsed
        else:
            self.stable_start_time = None
            return False, 0

    def reset(self):
        self.positions.clear()
        self.stable_start_time = None


# ============================================================
#                  UI DRAWING MODULE
# ============================================================

_C = {
    'hdr_passive':    (35,  18,  72),
    'hdr_activating': (18,  45,  80),
    'hdr_active':     (18,  55,  18),
    'acc_passive':    (100, 40, 160),
    'acc_activating': (40, 160, 220),
    'acc_active':     (50, 180,  50),
    't_passive':   (90,  90, 200),
    't_activating':(40, 180, 220),
    't_active':    (90, 220,  90),
    't_white':     (235, 235, 235),
    't_grey':      (150, 150, 150),
    't_cyan':      (210, 210,  50),
    't_pill_border':(60, 160, 60),
    'bar_bg':      (38,  38,  38),
    'bar_ok':      (55, 200,  55),
    'bar_warn':    (40, 200, 200),
    'bar_crit':    (40,  40, 220),
    'strip_bg':    (12,  12,  12),
}

HEADER_H = 72


def _rect_alpha(img, pt1, pt2, color, alpha):
    ov = img.copy()
    cv2.rectangle(ov, pt1, pt2, color, -1)
    cv2.addWeighted(ov, alpha, img, 1 - alpha, 0, img)


def draw_ui(img, state, fps, progress=0, context="", last_action="",
            action_display_time=0, inactivity_remaining=0, detected_gesture=""):
    h, w = img.shape[:2]

    if state == STATE_ACTIVE:
        hdr_col = _C['hdr_active'];  acc_col = _C['acc_active']
        lbl_col = _C['t_active'];    lbl_txt = "SYSTEM ACTIVE"
    elif state == STATE_ACTIVATING:
        hdr_col = _C['hdr_activating']; acc_col = _C['acc_activating']
        lbl_col = _C['t_activating'];   lbl_txt = "ACTIVATING"
    else:
        hdr_col = _C['hdr_passive']; acc_col = _C['acc_passive']
        lbl_col = _C['t_passive'];   lbl_txt = "SYSTEM PASSIVE"

    _rect_alpha(img, (0, 0), (w, HEADER_H), hdr_col, 0.60)
    cv2.line(img, (0, HEADER_H), (w, HEADER_H), acc_col, 2)

    _rect_alpha(img, (0, h - 26), (w, h), _C['strip_bg'], 0.72)
    cv2.line(img, (0, h - 26), (w, h - 26), (55, 55, 55), 1)

    cv2.putText(img, lbl_txt, (16, 42),
                cv2.FONT_HERSHEY_DUPLEX, 1.05, lbl_col, 2, cv2.LINE_AA)

    if state == STATE_PASSIVE:
        hint = "SHOW  HAND   or   SAY  'ACTIVATE'"
        (tw, _), _ = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.60, 1)
        cv2.putText(img, hint, ((w - tw) // 2, 63),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, _C['t_white'], 1, cv2.LINE_AA)

    elif state == STATE_ACTIVATING:
        bx1, bx2 = 16, w - 16
        by1, by2 = HEADER_H + 8, HEADER_H + 24
        fill = int(progress * (bx2 - bx1))
        cv2.rectangle(img, (bx1, by1), (bx2, by2), _C['bar_bg'], -1)
        cv2.rectangle(img, (bx1, by1), (bx1 + fill, by2), _C['t_activating'], -1)
        pct = f"{int(progress * 100)}%"
        cv2.putText(img, pct, (bx2 + 4, by2 - 1),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.46, _C['t_activating'], 1, cv2.LINE_AA)
        cv2.putText(img, "Hold your hand steady...", (bx1, by2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, _C['t_grey'], 1, cv2.LINE_AA)

    else:
        if context:
            ctx = f"[ {context.upper()} ]"
            (cw, _), _ = cv2.getTextSize(ctx, cv2.FONT_HERSHEY_SIMPLEX, 0.56, 1)
            cv2.putText(img, ctx, (w - cw - 14, 42),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.56, _C['t_cyan'], 1, cv2.LINE_AA)

        bx1, bx2 = 16, w - 16
        by1, by2 = HEADER_H + 6, HEADER_H + 18
        ratio = max(inactivity_remaining / INACTIVITY_TIMEOUT, 0)
        fill = int(ratio * (bx2 - bx1))
        bar_col = _C['bar_ok'] if ratio > 0.5 else _C['bar_warn'] if ratio > 0.2 else _C['bar_crit']
        cv2.rectangle(img, (bx1, by1), (bx2, by2), _C['bar_bg'], -1)
        cv2.rectangle(img, (bx1, by1), (bx1 + fill, by2), bar_col, -1)
        cv2.putText(img, f"timeout  {int(inactivity_remaining)}s", (bx1, by2 + 17),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.43, bar_col, 1, cv2.LINE_AA)

        if detected_gesture:
            badge = f"  {detected_gesture.replace('_', ' ').upper()}  "
            (bw, bh), _ = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 1)
            gx, gy = 16, HEADER_H + 54
            _rect_alpha(img, (gx - 4, gy - bh - 4), (gx + bw + 4, gy + 6),
                        (20, 70, 20), 0.75)
            cv2.rectangle(img, (gx - 4, gy - bh - 4), (gx + bw + 4, gy + 6),
                          _C['acc_active'], 1)
            cv2.putText(img, badge, (gx, gy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.58, _C['t_active'], 1, cv2.LINE_AA)

        if last_action and (time.time() - action_display_time) < 3.0:
            (aw, ah), _ = cv2.getTextSize(last_action, cv2.FONT_HERSHEY_SIMPLEX, 0.56, 1)
            ax, ay = 16, h - 38
            _rect_alpha(img, (ax - 6, ay - ah - 5), (ax + aw + 10, ay + 7),
                        (30, 30, 30), 0.80)
            cv2.rectangle(img, (ax - 6, ay - ah - 5), (ax + aw + 10, ay + 7),
                          _C['t_pill_border'], 1)
            cv2.putText(img, last_action, (ax, ay),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.56, _C['t_cyan'], 1, cv2.LINE_AA)

    cv2.putText(img, f"{int(fps)} fps", (8, h - 7),
                cv2.FONT_HERSHEY_SIMPLEX, 0.41, _C['t_grey'], 1, cv2.LINE_AA)
    quit_lbl = "Q  \u2014  quit"
    (qw, _), _ = cv2.getTextSize(quit_lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.41, 1)
    cv2.putText(img, quit_lbl, (w - qw - 8, h - 7),
                cv2.FONT_HERSHEY_SIMPLEX, 0.41, _C['t_grey'], 1, cv2.LINE_AA)

    return img


# ============================================================
#                    MAIN SYSTEM LOOP
# ============================================================

def main():
    print("=" * 60)
    print("  GESTVOICE SMART ASSISTANT + AI + CURSOR CONTROL")
    print("  🧠 AI: Fuzzy Matching + Intent Classifier + Gemini")
    print("  🖱️ Cursor: Index finger tracking + Pinch click")
    print("  🎤 Voice: Say 'Siri <command>' to execute")
    print("  Starting up...")
    print("=" * 60)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)

    if not cap.isOpened():
        print("[ERROR] Cannot open camera!")
        return

    print("[OK] Camera opened")

    stability_tracker = StabilityTracker()
    gesture_recognizer = GestureRecognizer()
    cursor_controller = CursorController()

    # Get screen size for window positioning
    screen_w, screen_h = pyautogui.size()
    SMALL_WIN_W, SMALL_WIN_H = 320, 240
    WIN_NAME = "GestVoice — Smart Assistant + AI"
    window_positioned = False

    system_state = {
        'state': STATE_PASSIVE,
        'voice_activate': False,
        'voice_deactivate': False,
        'dictation_start': False,
        'dictation_stop': False,
        'terminate_system': False,
        'scroll_speed': 0,
        'last_interaction': time.time(),
        'last_action': '',
        'action_display_time': 0,
        'cursor_enabled': True,     # Cursor mode available by default
        'cursor_active': False,     # Whether cursor is currently tracking
    }

    voice_thread = threading.Thread(
        target=voice_listener_loop,
        args=(system_state,),
        daemon=True
    )
    voice_thread.start()
    print("[OK] Voice listener started")

    current_state = STATE_PASSIVE
    last_interaction_time = time.time()
    prev_time = time.time()
    active_announced = False

    print("[OK] System is PASSIVE — show hand or say 'Activate'")
    print("[OK] Voice commands require 'Boss' prefix (e.g. 'Boss open chrome')")
    print("-" * 60)

    # Create named window for positioning
    cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)

    while True:
        if system_state.get('terminate_system', False):
            break

        # Handle Continuous Scrolling
        if system_state.get('scroll_speed', 0) != 0:
            pyautogui.scroll(system_state['scroll_speed'])

        success, img = cap.read()
        if not success:
            continue

        img = cv2.flip(img, 1)
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        imgRGB.flags.writeable = False
        results = hands.process(imgRGB)
        imgRGB.flags.writeable = True

        curr_time = time.time()
        fps = 1 / (curr_time - prev_time + 1e-9)
        prev_time = curr_time

        hand_detected = False
        hand_landmarks = None
        handedness = 'Right'

        if results.multi_hand_landmarks and results.multi_handedness:
            hand_detected = True
            hand_landmarks = results.multi_hand_landmarks[0].landmark
            handedness = results.multi_handedness[0].classification[0].label

            mp_draw.draw_landmarks(
                img, results.multi_hand_landmarks[0],
                mp_hands.HAND_CONNECTIONS,
                LANDMARK_STYLE, CONNECTION_STYLE
            )

        progress = 0
        context = ''
        detected_gesture = ''
        inactivity_remaining = INACTIVITY_TIMEOUT

        if current_state == STATE_PASSIVE:

            # Release cursor if it was active
            if system_state.get('cursor_active', False):
                cursor_controller.release()
                system_state['cursor_active'] = False

            if system_state['voice_activate']:
                system_state['voice_activate'] = False
                current_state = STATE_ACTIVE
                last_interaction_time = time.time()
                active_announced = False
                stability_tracker.reset()
                print("[STATE] Voice activated → ACTIVE")
                speak("Voice activated! System is now active.")

            elif hand_detected:
                wrist = hand_landmarks[0]
                wrist_x = int(wrist.x * CAMERA_WIDTH)
                wrist_y = int(wrist.y * CAMERA_HEIGHT)
                is_stable, elapsed = stability_tracker.update(wrist_x, wrist_y)
                if is_stable:
                    current_state = STATE_ACTIVATING
                    progress = min(elapsed / ACTIVATION_TIME, 1.0)

            else:
                stability_tracker.reset()

        elif current_state == STATE_ACTIVATING:

            if hand_detected:
                wrist = hand_landmarks[0]
                wrist_x = int(wrist.x * CAMERA_WIDTH)
                wrist_y = int(wrist.y * CAMERA_HEIGHT)
                is_stable, elapsed = stability_tracker.update(wrist_x, wrist_y)

                if is_stable:
                    progress = min(elapsed / ACTIVATION_TIME, 1.0)
                    if elapsed >= ACTIVATION_TIME:
                        current_state = STATE_ACTIVE
                        last_interaction_time = time.time()
                        active_announced = False
                        stability_tracker.reset()
                        gesture_recognizer.wrist_history.clear()
                        print("[STATE] Hand stable → ACTIVE")
                else:
                    current_state = STATE_PASSIVE
                    progress = 0
            else:
                current_state = STATE_PASSIVE
                stability_tracker.reset()
                progress = 0

        elif current_state == STATE_ACTIVE:

            if not active_announced:
                speak("System active! Use gestures or say Boss followed by a command.")
                active_announced = True

            context = detect_context()
            inactivity_remaining = max(
                0, INACTIVITY_TIMEOUT - (time.time() - last_interaction_time)
            )

            if system_state['last_interaction'] > last_interaction_time:
                last_interaction_time = system_state['last_interaction']

            if system_state['dictation_start']:
                system_state['dictation_start'] = False
                current_state = STATE_DICTATION
                active_announced = False
                # Release cursor when entering dictation
                if system_state.get('cursor_active', False):
                    cursor_controller.release()
                    system_state['cursor_active'] = False
                speak("Dictation mode started. Speech is muted.")
                print("[STATE] Command → DICTATION")
                continue

            if system_state['voice_deactivate']:
                system_state['voice_deactivate'] = False
                current_state = STATE_PASSIVE
                active_announced = False
                stability_tracker.reset()
                if system_state.get('cursor_active', False):
                    cursor_controller.release()
                    system_state['cursor_active'] = False
                print("[STATE] Voice deactivated → PASSIVE")
                continue
                
            if inactivity_remaining <= 0:
                current_state = STATE_PASSIVE
                active_announced = False
                stability_tracker.reset()
                if system_state.get('cursor_active', False):
                    cursor_controller.release()
                    system_state['cursor_active'] = False
                speak("No activity detected. Going to sleep.")
                print("[STATE] Timeout → PASSIVE")
                continue

            if hand_detected:
                cursor_enabled = system_state.get('cursor_enabled', True)
                cursor_active = system_state.get('cursor_active', False)

                if cursor_enabled:
                    # Check for static gestures first (they override cursor)
                    static_gesture = gesture_recognizer.detect_static_gesture(
                        hand_landmarks, handedness
                    )
                    
                    if static_gesture and (curr_time - gesture_recognizer.last_gesture_time >= GESTURE_COOLDOWN):
                        # Static gesture detected → exit cursor, execute gesture
                        if cursor_active:
                            cursor_controller.release()
                            system_state['cursor_active'] = False
                            cursor_active = False
                        
                        gesture_recognizer.last_gesture_time = curr_time
                        gesture_recognizer.wrist_history.clear()
                        detected_gesture = static_gesture
                        last_interaction_time = curr_time
                        system_state['last_interaction'] = last_interaction_time
                        action_desc = execute_gesture_action(static_gesture, context)
                        if action_desc:
                            action_text = f"✋ {static_gesture.replace('_', ' ').title()} → {action_desc} [{context}]"
                            system_state['last_action'] = action_text
                            system_state['action_display_time'] = curr_time
                            print(f"[GESTURE] {action_text}")
                            speak(action_desc)
                    else:
                        # No static gesture → check for index pointing (cursor)
                        pointing = is_index_pointing(hand_landmarks, handedness)
                        
                        if pointing or cursor_active:
                            # Cursor tracking mode
                            system_state['cursor_active'] = True
                            cursor_info = cursor_controller.update(hand_landmarks, img)
                            last_interaction_time = curr_time
                            system_state['last_interaction'] = last_interaction_time
                            
                            if cursor_info.get('left_click'):
                                system_state['last_action'] = "🖱️ Left Click"
                                system_state['action_display_time'] = curr_time
                            elif cursor_info.get('right_click'):
                                system_state['last_action'] = "🖱️ Right Click"
                                system_state['action_display_time'] = curr_time
                            elif cursor_info.get('dragging'):
                                system_state['last_action'] = "🖱️ Dragging"
                                system_state['action_display_time'] = curr_time
                            
                            # Check for swipes even during cursor mode
                            swipe = gesture_recognizer.detect_swipe(
                                hand_landmarks, CAMERA_WIDTH
                            )
                            if swipe and (curr_time - gesture_recognizer.last_gesture_time >= GESTURE_COOLDOWN):
                                cursor_controller.release()
                                system_state['cursor_active'] = False
                                gesture_recognizer.last_gesture_time = curr_time
                                detected_gesture = swipe
                                last_interaction_time = curr_time
                                system_state['last_interaction'] = last_interaction_time
                                action_desc = execute_gesture_action(swipe, context)
                                if action_desc:
                                    action_text = f"✋ {swipe.replace('_', ' ').title()} → {action_desc} [{context}]"
                                    system_state['last_action'] = action_text
                                    system_state['action_display_time'] = curr_time
                                    print(f"[GESTURE] {action_text}")
                                    speak(action_desc)
                        else:
                            # Not pointing, no gesture → check swipes only
                            if cursor_active:
                                cursor_controller.release()
                                system_state['cursor_active'] = False
                            swipe = gesture_recognizer.detect_swipe(
                                hand_landmarks, CAMERA_WIDTH
                            )
                            if swipe and (curr_time - gesture_recognizer.last_gesture_time >= GESTURE_COOLDOWN):
                                gesture_recognizer.last_gesture_time = curr_time
                                detected_gesture = swipe
                                last_interaction_time = curr_time
                                system_state['last_interaction'] = last_interaction_time
                                action_desc = execute_gesture_action(swipe, context)
                                if action_desc:
                                    action_text = f"✋ {swipe.replace('_', ' ').title()} → {action_desc} [{context}]"
                                    system_state['last_action'] = action_text
                                    system_state['action_display_time'] = curr_time
                                    print(f"[GESTURE] {action_text}")
                                    speak(action_desc)
                else:
                    # Cursor disabled → use original gesture recognition only
                    gesture = gesture_recognizer.recognize(
                        hand_landmarks, handedness, CAMERA_WIDTH
                    )
                    if gesture:
                        detected_gesture = gesture
                        last_interaction_time = curr_time
                        system_state['last_interaction'] = last_interaction_time
                        action_desc = execute_gesture_action(gesture, context)
                        if action_desc:
                            action_text = f"✋ {gesture.replace('_', ' ').title()} → {action_desc} [{context}]"
                            system_state['last_action'] = action_text
                            system_state['action_display_time'] = curr_time
                            print(f"[GESTURE] {action_text}")
                            speak(action_desc)
            else:
                # No hand detected → release cursor
                if system_state.get('cursor_active', False):
                    cursor_controller.release()
                    system_state['cursor_active'] = False

        elif current_state == STATE_DICTATION:
            
            inactivity_remaining = max(
                0, INACTIVITY_TIMEOUT - (time.time() - last_interaction_time)
            )
            
            if system_state['last_interaction'] > last_interaction_time:
                last_interaction_time = system_state['last_interaction']

            if system_state['dictation_stop']:
                system_state['dictation_stop'] = False
                current_state = STATE_ACTIVE
                active_announced = False
                speak("Dictation ended. Back to command mode.")
                print("[STATE] Dictation → ACTIVE")
                continue
                
            if inactivity_remaining <= 0:
                current_state = STATE_PASSIVE
                active_announced = False
                stability_tracker.reset()
                speak("Dictation timed out. Going to sleep.")
                print("[STATE] Timeout → PASSIVE")
                continue

            if hand_detected:
                gesture = gesture_recognizer.recognize(
                    hand_landmarks, handedness, CAMERA_WIDTH
                )
                if gesture:
                    detected_gesture = gesture
                    last_interaction_time = time.time()
                    system_state['last_interaction'] = last_interaction_time
                    action_desc = execute_gesture_action(gesture, context)
                    if action_desc:
                        action_text = f"✋ {gesture.replace('_', ' ').title()} → {action_desc} [{context}]"
                        system_state['last_action'] = action_text
                        system_state['action_display_time'] = time.time()
                        print(f"[GESTURE] {action_text}")
                        speak(action_desc)

        system_state['state'] = current_state

        img = draw_ui(
            img,
            state=current_state,
            fps=fps,
            progress=progress,
            context=context,
            last_action=system_state.get('last_action', ''),
            action_display_time=system_state.get('action_display_time', 0),
            inactivity_remaining=inactivity_remaining if current_state == STATE_ACTIVE else 0,
            detected_gesture=detected_gesture
        )

        # Resize frame for small window display
        img_small = cv2.resize(img, (SMALL_WIN_W, SMALL_WIN_H))
        cv2.imshow(WIN_NAME, img_small)

        # Position window at top-right corner (once)
        if not window_positioned:
            cv2.resizeWindow(WIN_NAME, SMALL_WIN_W, SMALL_WIN_H)
            cv2.moveWindow(WIN_NAME, screen_w - SMALL_WIN_W - 10, 10)
            try:
                cv2.setWindowProperty(WIN_NAME, cv2.WND_PROP_TOPMOST, 1)
            except Exception:
                pass
            window_positioned = True

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    if system_state.get('cursor_active', False):
        cursor_controller.release()
    print("\n[EXIT] Shutting down...")
    cap.release()
    cv2.destroyAllWindows()
    print("[EXIT] Done. Goodbye!")


if __name__ == "__main__":
    main()

