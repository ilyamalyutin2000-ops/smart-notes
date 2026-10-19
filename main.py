# -*- coding: utf-8 -*-
import os
import json
import threading
import base64
import ssl
import urllib.request
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
from kivy.uix.popup import Popup
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.animation import Animation

# ============================================================
# НАСТРОЙКА
# ============================================================
Window.clearcolor = get_color_from_hex('#F4F6F9')

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

OCR_API_KEY = "K86772432188957"
OPENROUTER_API_KEY = "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"

NOTES_FOLDER = ""
def init_storage():
    global NOTES_FOLDER
    try:
        base = App.get_running_app().user_data_dir
        NOTES_FOLDER = os.path.join(base, "notes")
        os.makedirs(NOTES_FOLDER, exist_ok=True)
    except: NOTES_FOLDER = "."

# ============================================================
# БЕЗОПАСНЫЙ ЗАПРОС
# ============================================================
def safe_url_request(url, json_data=None, headers=None):
    try:
        data = json_data.encode('utf-8') if json_data else None
        req = urllib.request.Request(url, data=data, headers=headers or {}, method='POST' if data else 'GET')
        with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return f"Ошибка API ({e.code})"
    except Exception as e:
        return f"Ошибка сети: {str(e)}"

# ============================================================
# KV РАЗМЕТКА (Стиль Telegram)
# ============================================================
KV = """
#:import SlideTransition kivy.uix.screenmanager.SlideTransition

<ChatBubble@BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    padding: dp(10)
    spacing: dp(5)
    canvas.before:
        Color:
            rgba: root.bg_color if hasattr(root, 'bg_color') else (1,1,1,1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [15, 15, 0, 15] if root.is_user else [15, 15, 15, 0]

<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        
        # Экран контента
        ScreenManager:
            id: content_manager
            transition: SlideTransition(direction='left', duration=0.2)
            
            # === ЭКРАН ЧАТА ===
            Screen:
                name: 'chat'
                BoxLayout:
                    orientation: 'vertical'
                    
                    # Заголовок
                    Label:
                        text: 'Чат с ИИ'
                        size_hint_y: None
                        height: dp(50)
                        font_size: '20sp'
                        bold: True
                        color: 0.15, 0.45, 0.85, 1
                        
                    # История сообщений
                    ScrollView:
                        id: chat_scroll
                        BoxLayout:
                            id: chat_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            padding: dp(10)
                            spacing: dp(10)
                            
                    # Поле ввода
                    BoxLayout:
                        size_hint_y: None
                        height: dp(60)
                        padding: dp(10)
                        spacing: dp(10)
                        
                        TextInput:
                            id: chat_input
                            hint_text: 'Написать сообщение...'
                            multiline: False
                            font_size: '16sp'
                            padding: dp(15), dp(15)
                            on_text_validate: root.send_chat_message()
                            
                        Button:
                            text: '➤'
                            size_hint_x: None
                            width: dp(60)
                            font_size: '20sp'
                            background_normal: ''
                            background_color: 0.15, 0.45, 0.85, 1
                            on_release: root.send_chat_message()

            # === ЭКРАН ЗАГРУЗКИ ===
            Screen:
                name: 'new'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(20)
                    spacing: dp(20)
                    
                    Label:
                        text: 'Загрузка конспекта'
                        size_hint_y: None
                        height: dp(40)
                        font_size: '22sp'
                        bold: True
                        
                    TextInput:
                        id: photo_path
                        hint_text: 'Путь к фото (напр. /storage/emulated/0/Download/photo.jpg)'
                        size_hint_y: None
                        height: dp(50)
                        multiline: False
                        
                    Button:
                        text: 'Распознать фото'
                        size_hint_y: None
                        height: dp(60)
                        background_normal: ''
                        background_color: 0.55, 0.3, 0.8, 1
                        on_release: root.process_photo_by_path()
                        
                    Label:
                        id: photo_status
                        text: 'Или введите текст ниже'
                        size_hint_y: None
                        height: dp(30)
                        color: 0.5, 0.5, 0.5, 1
                        
                    TextInput:
                        id: manual_text
                        hint_text: 'Введите конспект вручную...'
                        multiline: True
                        size_hint_y: 1
                        
                    Button:
                        text: 'Сохранить текст'
                        size_hint_y: None
                        height: dp(50)
                        background_normal: ''
                        background_color: 0.2, 0.6, 0.4, 1
                        on_release: root.save_manual_text()

            # === ЭКРАН ОБУЧЕНИЯ ===
            Screen:
                name: 'learn'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(10)
                    spacing: dp(10)
                    
                    Label:
                        text: 'ИИ-Учитель'
                        size_hint_y: None
                        height: dp(40)
                        font_size: '22sp'
                        bold: True
                        color: 0.55, 0.3, 0.8, 1
                        
                    Button:
                        text: 'Загрузить материал для плана'
                        size_hint_y: None
                        height: dp(55)
                        background_normal: ''
                        background_color: 0.2, 0.6, 0.4, 1
                        on_release: root.process_learn_material()
                        
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
                        height: dp(60)
                        spacing: dp(10)
                        
                        TextInput:
                            id: learn_input
                            hint_text: 'Ваш ответ учителю...'
                            multiline: False
                            on_text_validate: root.send_learn_message()
                            
                        Button:
                            text: '➤'
                            size_hint_x: None
                            width: dp(60)
                            background_normal: ''
                            background_color: 0.55, 0.3, 0.8, 1
                            on_release: root.send_learn_message()

        # === НИЖНЯЯ ПАНЕЛЬ НАВИГАЦИИ (Как в Telegram) ===
        BoxLayout:
            size_hint_y: None
            height: dp(60)
            padding: dp(5), dp(5)
            spacing: dp(5)
            canvas.before:
                Color:
                    rgba: 1, 1, 1, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
                    
            Button:
                text: '💬\\nЧат'
                font_size: '10sp'
                background_normal: ''
                background_color: 0.15, 0.45, 0.85, 1 if root.ids.content_manager.current == 'chat' else 0.8, 0.8, 0.8, 1
                on_release: root.ids.content_manager.current = 'chat'
            Button:
                text: '➕\\nЗагрузка'
                font_size: '10sp'
                background_normal: ''
                background_color: 0.15, 0.45, 0.85, 1 if root.ids.content_manager.current == 'new' else 0.8, 0.8, 0.8, 1
                on_release: root.ids.content_manager.current = 'new'
            Button:
                text: '📚\\nОбучение'
                font_size: '10sp'
                background_normal: ''
                background_color: 0.15, 0.45, 0.85, 1 if root.ids.content_manager.current == 'learn' else 0.8, 0.8, 0.8, 1
                on_release: root.ids.content_manager.current = 'learn'
"""

# ============================================================
# ЛОГИКА
# ============================================================
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_history = []
        self.learn_history = []
        Clock.schedule_once(self.setup_app, 0.5)

    def setup_app(self, dt):
        init_storage()

    # --- ЧАТ ---
    def send_chat_message(self):
        text = self.ids.chat_input.text.strip()
        if not text: return
        self.ids.chat_input.text = ''
        self.add_bubble(self.ids.chat_container, text, is_user=True)
        self.chat_history.append({'role': 'user', 'content': text})
        
        loading = Label(text='Думаю...', size_hint_y=None, height=dp(40), italic=True, color=(0.5, 0.5, 0.5, 1))
        self.ids.chat_container.add_widget(loading)
        
        def worker():
            try:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENROUTER_API_KEY}"}
                payload = json.dumps({"model": "meta-llama/llama-3-8b-instruct", "messages": self.chat_history})
                response = safe_url_request(url, payload, headers)
                
                if response.startswith("Ошибка"):
                    self.update_answer(self.ids.chat_container, response, loading, is_learn=False)
                    return
                    
                result = json.loads(response)
                answer = result["choices"][0]["message"]["content"].strip()
                self.chat_history.append({'role': 'assistant', 'content': answer})
                self.update_answer(self.ids.chat_container, answer, loading, is_learn=False)
            except Exception as e:
                self.update_answer(self.ids.chat_container, f"Ошибка: {e}", loading, is_learn=False)
                
        threading.Thread(target=worker, daemon=True).start()

    # --- ОБУЧЕНИЕ ---
    def process_learn_material(self):
        self.add_bubble(self.ids.learn_container, "Материал загружен! Составляю план...", is_user=False)
        
        def worker():
            try:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENROUTER_API_KEY}"}
                payload = json.dumps({
                    "model": "meta-llama/llama-3-8b-instruct",
                    "messages": [{"role": "user", "content": "Составь план обучения по программированию. Задай первый вопрос."}]
                })
                response = safe_url_request(url, payload, headers)
                
                if response.startswith("Ошибка"):
                    self.update_answer(self.ids.learn_container, response, None, is_learn=True)
                    return
                    
                result = json.loads(response)
                answer = result["choices"][0]["message"]["content"].strip()
                self.update_answer(self.ids.learn_container, answer, None, is_learn=True)
            except Exception as e:
                self.update_answer(self.ids.learn_container, f"Ошибка: {e}", None, is_learn=True)
                
        threading.Thread(target=worker, daemon=True).start()

    def send_learn_message(self):
        text = self.ids.learn_input.text.strip()
        if not text: return
        self.ids.learn_input.text = ''
        self.add_bubble(self.ids.learn_container, text, is_user=True)
        
        def worker():
            try:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENROUTER_API_KEY}"}
                payload = json.dumps({
                    "model": "meta-llama/llama-3-8b-instruct",
                    "messages": [{"role": "user", "content": f"Мой ответ: {text}. Оцени и задай следующий вопрос."}]
                })
                response = safe_url_request(url, payload, headers)
                
                if response.startswith("Ошибка"):
                    self.update_answer(self.ids.learn_container, response, None, is_learn=True)
                    return
                    
                result = json.loads(response)
                answer = result["choices"][0]["message"]["content"].strip()
                self.update_answer(self.ids.learn_container, answer, None, is_learn=True)
            except Exception as e:
                self.update_answer(self.ids.learn_container, f"Ошибка: {e}", None, is_learn=True)
                
        threading.Thread(target=worker, daemon=True).start()

    # --- ОБЩИЕ МЕТОДЫ ---
    @mainthread
    def update_answer(self, container, answer, loading_label, is_learn):
        if loading_label and loading_label.parent:
            container.remove_widget(loading_label)
        self.add_bubble(container, answer, is_user=False)

    def add_bubble(self, container, text, is_user):
        bubble = BoxLayout(orientation='horizontal', size_hint_y=None, spacing=dp(5))
        
        if is_user:
            bubble.add_widget(Label(size_hint_x=0.2)) # Отступ слева
            
        # Сам пузырь
        bubble_content = BoxLayout(orientation='vertical', size_hint_x=0.8, padding=dp(10), spacing=dp(5))
        
        # Рисуем фон пузыря
        with bubble_content.canvas.before:
            Color(*(0.9, 0.95, 1, 1) if is_user else (1, 1, 1, 1))
            rect = RoundedRectangle(pos=bubble_content.pos, size=bubble_content.size, radius=[dp(15)])
        bubble_content.bind(pos=lambda *x: setattr(rect, 'pos', bubble_content.pos))
        bubble_content.bind(size=lambda *x: setattr(rect, 'size', bubble_content.size))
        
        lbl = Label(text=text, size_hint_y=None, text_size=(dp(280), None), halign='left', valign='top', color=(0,0,0,1))
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        bubble_content.add_widget(lbl)
        
        bubble.add_widget(bubble_content)
        
        if not is_user:
            bubble.add_widget(Label(size_hint_x=0.2)) # Отступ справа
            
        bubble.height = lbl.height + dp(20)
        container.add_widget(bubble)
        
        # Анимация
        bubble.opacity = 0
        Animation(opacity=1, d=0.3).start(bubble)

def save_note(text):
    try:
        note_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        data = {"id": note_id, "title": text[:20], "text": text}
        with open(os.path.join(NOTES_FOLDER, f"{note_id}.json"), 'w', encoding='utf-8') as f: 
            json.dump(data, f, ensure_ascii=False)
    except Exception as e: print(e)

class NotesApp(App):
    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    NotesApp().run()
