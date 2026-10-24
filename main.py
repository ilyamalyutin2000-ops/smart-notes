# -*- coding: utf-8 -*-
import os
import json
import threading
import base64
import ssl
import urllib.request
import shutil
import time
from datetime import datetime
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.clipboard import Clipboard

# ============================================================
# НАСТРОЙКА
# ============================================================
Window.clearcolor = get_color_from_hex('#F4F6F9')
Window.softinput_mode = 'below_target'

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

OCR_API_KEY = "K86772432188957"

# === ТВОЙ ПУЛ КЛЮЧЕЙ (6 ШТУК) ===
API_KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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",
    "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"
]

MODEL_NAME = "openrouter/free"

BASE_DIR, NOTES_FOLDER, COURSES_FOLDER, CACHE_FILE = "", "", "", ""

def init_storage():
    global BASE_DIR, NOTES_FOLDER, COURSES_FOLDER, CACHE_FILE
    try:
        BASE_DIR = App.get_running_app().user_data_dir
        NOTES_FOLDER = os.path.join(BASE_DIR, "notes")
        COURSES_FOLDER = os.path.join(BASE_DIR, "courses")
        os.makedirs(NOTES_FOLDER, exist_ok=True)
        os.makedirs(COURSES_FOLDER, exist_ok=True)
        CACHE_FILE = os.path.join(BASE_DIR, "cache.json")
    except: 
        BASE_DIR, NOTES_FOLDER, COURSES_FOLDER, CACHE_FILE = ".", ".", ".", "cache.json"

# ============================================================
# УМНАЯ ФУНКЦИЯ ЗАПРОСА (С ПЕРЕКЛЮЧЕНИЕМ КЛЮЧЕЙ)
# ============================================================
def safe_openrouter_request(messages):
    if not API_KEYS:
        return "Ошибка: В коде не указан ни один API-ключ."

    # Пробуем каждый ключ по очереди
    for key in API_KEYS:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
            
            sys_instruction = {
                "role": "system", 
                "content": "Отвечай ИСКЛЮЧИТЕЛЬНО на русском языке. Не используй markdown-таблицы и сложные символы."
            }
            final_messages = [sys_instruction] + messages
            payload = {"model": MODEL_NAME, "messages": final_messages, "temperature": 0.5, "max_tokens": 1500}
            
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
            
            with urllib.request.urlopen(req, context=ssl_context, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result["choices"][0]["message"].get("content")
                
                if not content or not content.strip():
                    continue # Если пустой ответ, пробуем следующий ключ
                    
                return content.strip()
                
        except urllib.error.HTTPError as e:
            if e.code == 429:
                # Лимит исчерпан для этого ключа, идем к следующему
                continue 
            elif e.code == 401:
                # Ключ недействителен, идем к следующему
                continue
            else:
                return f"Ошибка API ({e.code})"
        except Exception:
            # Ошибка сети, пробуем следующий ключ
            continue
            
    # Если цикл прошел, а ответа нет - значит все ключи кончились
    return "Все ключи исчерпали лимит (429) или недействительны. Попробуйте позже."

def save_note(text):
    try:
        note_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        title = text.strip().split('\n')[0][:30] if text.strip() else "Без названия"
        with open(os.path.join(NOTES_FOLDER, f"{note_id}.json"), 'w', encoding='utf-8') as f: 
            json.dump({"id": note_id, "title": title, "text": text}, f, ensure_ascii=False)
        return True
    except: return False

# ============================================================
# КНОПКИ И ИНТЕРФЕЙС
# ============================================================
class ModernButton(Button):
    def __init__(self, **kwargs):
        self.bg_color = kwargs.pop('bg_color', (0.15, 0.45, 0.85, 1))
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            self.color_inst = Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(15)])
        self.bind(pos=self.update_rect, size=self.update_rect)
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

KV = """
#:import SlideTransition kivy.uix.screenmanager.SlideTransition
#:import ModernButton __main__.ModernButton

<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        ScreenManager:
            id: content_manager
            transition: SlideTransition(direction='left', duration=0.2)
            
            Screen:
                name: 'chat'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(10)
                    spacing: dp(10)
                    ScrollView:
                        id: chat_scroll
                        BoxLayout:
                            id: chat_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(10)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(55)
                        spacing: dp(8)
                        TextInput:
                            id: chat_input
                            hint_text: 'Вопрос...'
                            multiline: False
                            on_text_validate: root.send_chat_message()
                        ModernButton:
                            text: '▶'
                            size_hint_x: None
                            width: dp(55)
                            bg_color: (0.15, 0.45, 0.85, 1)
                            on_release: root.send_chat_message()

            Screen:
                name: 'new'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(15)
                    spacing: dp(15)
                    Label:
                        id: photo_status
                        text: 'Вставьте текст:'
                        size_hint_y: None
                        height: dp(30)
                    TextInput:
                        id: manual_text
                        hint_text: 'Введите конспект...'
                        multiline: True
                        size_hint_y: 1
                    ModernButton:
                        text: 'Сохранить'
                        size_hint_y: None
                        height: dp(55)
                        bg_color: (0.2, 0.6, 0.4, 1)
                        on_release: root.save_manual_text()

            Screen:
                name: 'learn'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(15)
                    spacing: dp(15)
                    TextInput:
                        id: learn_text_input
                        hint_text: 'Вставьте конспект для обучения...'
                        multiline: True
                        size_hint_y: 0.3
                    BoxLayout:
                        size_hint_y: None
                        height: dp(55)
                        spacing: dp(10)
                        ModernButton:
                            text: 'План'
                            bg_color: (0.2, 0.6, 0.4, 1)
                            on_release: root.start_learning()
                    ScrollView:
                        id: lessons_scroll
                        BoxLayout:
                            id: lessons_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(8)
                    ScrollView:
                        id: learn_scroll
                        BoxLayout:
                            id: learn_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(10)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(55)
                        spacing: dp(8)
                        TextInput:
                            id: learn_input
                            hint_text: 'Ваш ответ...'
                            multiline: False
                            on_text_validate: root.send_learn_message()
                        ModernButton:
                            text: '▶'
                            size_hint_x: None
                            width: dp(55)
                            bg_color: (0.55, 0.3, 0.8, 1)
                            on_release: root.send_learn_message()

        BoxLayout:
            size_hint_y: None
            height: dp(60)
            spacing: dp(8)
            padding: dp(5), dp(5)
            canvas.before:
                Color:
                    rgba: 1, 1, 1, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            ModernButton:
                id: btn_nav_chat
                text: 'Чат'
                bg_color: (0.4, 0.4, 0.45, 1)
                on_release: root.switch_nav('chat')
            ModernButton:
                id: btn_nav_new
                text: 'Загрузка'
                bg_color: (0.4, 0.4, 0.45, 1)
                on_release: root.switch_nav('new')
            ModernButton:
                id: btn_nav_learn
                text: 'Обучение'
                bg_color: (0.4, 0.4, 0.45, 1)
                on_release: root.switch_nav('learn')
"""

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_history = []
        self.learning_context = ""
        self.course_cache = {}
        Clock.schedule_once(self.setup_app, 0.5)

    def setup_app(self, dt):
        init_storage()
        self.switch_nav('chat')

    def switch_nav(self, name):
        self.ids.content_manager.current = name
        self.ids.btn_nav_chat.color_inst.rgba = (0.15, 0.45, 0.85, 1) if name == 'chat' else (0.4, 0.4, 0.45, 1)
        self.ids.btn_nav_new.color_inst.rgba = (0.15, 0.45, 0.85, 1) if name == 'new' else (0.4, 0.4, 0.45, 1)
        self.ids.btn_nav_learn.color_inst.rgba = (0.15, 0.45, 0.85, 1) if name == 'learn' else (0.4, 0.4, 0.45, 1)

    def save_manual_text(self):
        text = self.ids.manual_text.text.strip()
        if text:
            if save_note(text):
                self.ids.manual_text.text = ''
                self.ids.photo_status.text = 'Сохранено!'
            else:
                self.ids.photo_status.text = 'Ошибка сохранения'

    def send_chat_message(self):
        text = self.ids.chat_input.text.strip()
        if not text: return
        self.ids.chat_input.text = ''
        
        self.add_bubble(self.ids.chat_container, text, is_user=True)
        self.chat_history.append({'role': 'user', 'content': text})
        
        loading = Label(text='...', size_hint_y=None, height=dp(30))
        self.ids.chat_container.add_widget(loading)
        
        def worker():
            try:
                ans = safe_openrouter_request(self.chat_history)
                if ans and not ans.startswith("Ошибка") and not ans.startswith("Все ключи"):
                    self.chat_history.append({'role': 'assistant', 'content': ans})
                self.update_chat(ans, loading)
            except Exception as e: self.update_chat(f"Ошибка: {e}", loading)
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_chat(self, answer, loading):
        if loading and loading.parent: self.ids.chat_container.remove_widget(loading)
        self.add_bubble(self.ids.chat_container, answer, is_user=False)

    def start_learning(self):
        text = self.ids.learn_text_input.text.strip()
        if not text: 
            self.add_bubble(self.ids.learn_container, "Вставьте текст для обучения!", is_user=False)
            return
            
        self.learning_context = text
        self.ids.learn_container.clear_widgets()
        self.ids.lessons_container.clear_widgets()
        self.add_bubble(self.ids.learn_container, "Составляю план...", is_user=False)
        
        def worker():
            try:
                prompt = f"Составь план из 3 пунктов. ТОЛЬКО цифры. Текст:\n{text[:2000]}"
                ans = safe_openrouter_request([{"role": "user", "content": prompt}])
                
                # Если все ключи сдохли или пустой ответ
                if not ans or len(ans) < 5 or ans.startswith("Все ключи"): 
                    self.update_learn(f"Не удалось составить план.\n{ans}", None)
                    return
                    
                self.show_lessons(ans, text)
            except Exception as e: 
                self.update_learn(f"Ошибка: {e}", None)
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def show_lessons(self, raw_plan, context):
        self.ids.learn_container.clear_widgets()
        self.add_bubble(self.ids.learn_container, "План готов:", is_user=False)
        for line in [l.strip() for l in raw_plan.split('\n') if l.strip()]:
            if line[0].isdigit():
                btn = ModernButton(text=line, size_hint_y=None, height=dp(50), bg_color=(0.15, 0.45, 0.85, 1))
                btn.bind(on_release=lambda b, l=line: self.start_lesson(l))
                self.ids.lessons_container.add_widget(btn)

    def start_lesson(self, lesson_title):
        self.ids.learn_container.clear_widgets()
        self.add_bubble(self.ids.learn_container, f"Урок: {lesson_title}", is_user=False)
        if lesson_title in self.course_cache:
            self.add_bubble(self.ids.learn_container, self.course_cache[lesson_title], is_user=False)
            return
        def worker():
            try:
                prompt = f"Объясни '{lesson_title}'. Без таблиц. Текст:\n{self.learning_context[:2000]}"
                ans = safe_openrouter_request([{"role": "user", "content": prompt}])
                if ans and not ans.startswith("Ошибка") and not ans.startswith("Все ключи"): 
                    self.course_cache[lesson_title] = ans
                self.update_learn(ans, None)
            except: pass
        threading.Thread(target=worker, daemon=True).start()

    def send_learn_message(self):
        text = self.ids.learn_input.text.strip()
        if not text: return
        self.ids.learn_input.text = ''
        self.add_bubble(self.ids.learn_container, text, is_user=True)
        def worker():
            ans = safe_openrouter_request([{"role": "user", "content": text}])
            self.update_learn(ans, None)
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_learn(self, answer, loading):
        if loading and loading.parent: self.ids.learn_container.remove_widget(loading)
        self.add_bubble(self.ids.learn_container, answer, is_user=False)

    def add_bubble(self, container, text, is_user):
        row = BoxLayout(orientation='horizontal', size_hint_y=None, spacing=dp(5))
        bubble = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        
        lbl = Label(
            text=text, size_hint_y=None, text_size=(dp(250), None), 
            halign='right' if is_user else 'left', valign='top',
            color=(0, 0, 0, 1), markup=False
        )
        
        with bubble.canvas.before:
            Color(*(0.85, 0.92, 1, 1) if is_user else (1, 1, 1, 1))
            rect = Rectangle(pos=bubble.pos, size=bubble.size)
        bubble.bind(pos=lambda *x: setattr(rect, 'pos', bubble.pos))
        bubble.bind(size=lambda *x: setattr(rect, 'size', bubble.size))
        
        lbl.padding = (dp(10), dp(10))
        
        def update_height(instance, texture_size):
            instance.height = texture_size[1] + dp(20)
            bubble.height = instance.height + dp(40)
            row.height = bubble.height
            container.height = container.minimum_height
            
        lbl.bind(texture_size=update_height)
        bubble.add_widget(lbl)
        
        btn_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(5))
        btn_copy = ModernButton(text="📋 Копировать", font_size='12sp', bg_color=(0.8, 0.85, 0.9, 1))
        btn_copy.bind(on_release=lambda x: Clipboard.copy(text))
        btn_row.add_widget(btn_copy)
        
        if is_user:
            btn_repeat = ModernButton(text="🔄 Повторить", font_size='12sp', bg_color=(0.6, 0.8, 1, 1))
            btn_repeat.bind(on_release=lambda x: self.send_chat_message())
            btn_row.add_widget(btn_repeat)
            
        bubble.add_widget(btn_row)
        
        if is_user:
            row.add_widget(Label(size_hint_x=0.05))
            row.add_widget(bubble)
        else:
            row.add_widget(bubble)
            row.add_widget(Label(size_hint_x=0.05))
            
        container.add_widget(row)
        Clock.schedule_once(lambda dt: setattr(container, 'height', container.minimum_height), 0.1)

class NotesApp(App):
    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    NotesApp().run()
