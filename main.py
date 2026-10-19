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
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
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
        with urllib.request.urlopen(req, context=ssl_context, timeout=20) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return f"Ошибка API ({e.code})"
    except Exception as e:
        return f"Ошибка сети: {str(e)}"

# ============================================================
# ИНТЕРФЕЙС
# ============================================================
KV = """
#:import SlideTransition kivy.uix.screenmanager.SlideTransition

<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(15)
        spacing: dp(15)
        
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(10)
            
            Button:
                id: btn_tab_new
                text: 'Загрузка'
                background_normal: ''
                background_color: 0.15, 0.45, 0.85, 1
                on_release: root.switch_tab('new')
            Button:
                id: btn_tab_history
                text: 'История'
                background_normal: ''
                background_color: 0.4, 0.4, 0.45, 1
                on_release: root.switch_tab('history')
            Button:
                id: btn_tab_chat
                text: 'Чат'
                background_normal: ''
                background_color: 0.4, 0.4, 0.45, 1
                on_release: root.switch_tab('chat')

        ScreenManager:
            id: content_manager
            transition: SlideTransition(direction='left', duration=0.3)
            
            # === ЭКРАН ЗАГРУЗКИ ===
            Screen:
                name: 'new'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(15)
                    
                    # Блок с фото
                    TextInput:
                        id: path_input
                        hint_text: 'Путь к фото (напр. /storage/emulated/0/Download/photo.jpg)'
                        multiline: False
                        size_hint_y: None
                        height: dp(50)
                        padding: dp(15), dp(15)
                    
                    Button:
                        text: 'Распознать фото'
                        size_hint_y: None
                        height: dp(60)
                        background_normal: ''
                        background_color: 0.55, 0.3, 0.8, 1
                        on_release: root.process_photo_by_path()
                        
                    Label:
                        id: photo_status
                        text: 'Путь к файлу'
                        color: 0.4, 0.4, 0.45, 1
                        size_hint_y: None
                        height: dp(30)
                        
                    ScrollView:
                        Label:
                            id: photo_output
                            text: 'Здесь появится распознанный текст...'
                            size_hint_y: None
                            height: self.texture_size[1]
                            text_size: self.width, None
                            color: 0.1, 0.15, 0.2, 1

                    # Блок с ручным вводом текста
                    Label:
                        text: 'Или введите текст вручную:'
                        size_hint_y: None
                        height: dp(30)
                        color: 0.4, 0.4, 0.45, 1
                        
                    TextInput:
                        id: manual_text_input
                        hint_text: 'Напишите свой конспект здесь...'
                        multiline: True
                        size_hint_y: 0.3
                        padding: dp(15), dp(15)
                        
                    Button:
                        text: 'Сохранить текст'
                        size_hint_y: None
                        height: dp(50)
                        background_normal: ''
                        background_color: 0.2, 0.6, 0.4, 1
                        on_release: root.save_manual_text()

            # === ЭКРАН ИСТОРИИ ===
            Screen:
                name: 'history'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    Button:
                        text: 'Обновить'
                        size_hint_y: None
                        height: dp(45)
                        background_normal: ''
                        background_color: 0.15, 0.45, 0.85, 1
                        on_release: root.load_history()
                    ScrollView:
                        BoxLayout:
                            id: history_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(10)

            # === ЭКРАН ЧАТА ===
            Screen:
                name: 'chat'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    
                    ScrollView:
                        BoxLayout:
                            id: chat_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(15)
                            
                    BoxLayout:
                        size_hint_y: None
                        height: dp(60)
                        spacing: dp(10)
                        
                        TextInput:
                            id: chat_input
                            hint_text: 'Введите вопрос...'
                            multiline: False
                            padding: dp(15), dp(15)
                            on_text_validate: root.send_chat_message()
                            
                        Button:
                            text: 'Ввод'
                            size_hint_x: None
                            width: dp(90)
                            background_normal: ''
                            background_color: 0.15, 0.45, 0.85, 1
                            on_release: root.send_chat_message()
"""

# ============================================================
# ЛОГИКА
# ============================================================
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_history = []
        Clock.schedule_once(self.setup_app, 0.5)

    def setup_app(self, dt):
        init_storage()

    def switch_tab(self, name):
        self.ids.content_manager.current = name
        # Сброс цветов
        self.ids.btn_tab_new.background_color = (0.4, 0.4, 0.45, 1)
        self.ids.btn_tab_history.background_color = (0.4, 0.4, 0.45, 1)
        self.ids.btn_tab_chat.background_color = (0.4, 0.4, 0.45, 1)
        
        # Подсветка
        if name == 'new': self.ids.btn_tab_new.background_color = (0.15, 0.45, 0.85, 1)
        elif name == 'history': 
            self.ids.btn_tab_history.background_color = (0.15, 0.45, 0.85, 1)
            self.load_history()
        elif name == 'chat': self.ids.btn_tab_chat.background_color = (0.15, 0.45, 0.85, 1)

    # --- РАБОТА С ТЕКСТОМ И ФОТО ---
    def load_history(self):
        container = self.ids.history_container
        container.clear_widgets()
        notes = get_all_notes()
        if not notes:
            container.add_widget(Label(text="История пуста", size_hint_y=None, height=dp(40)))
            return
        for note in notes:
            btn = Button(text=note.get('title', 'Без названия'), size_hint_y=None, height=dp(50))
            container.add_widget(btn)

    def process_photo_by_path(self):
        path = self.ids.path_input.text.strip()
        if not path:
            self.ids.photo_status.text = "Введите путь к файлу!"
            return
        self.ids.photo_status.text = 'Обработка...'
        threading.Thread(target=self.process_photo, args=(path,), daemon=True).start()

    def process_photo(self, path):
        try:
            if not os.path.exists(path):
                raise Exception("Файл не найден.")
            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            
            url = "https://api.ocr.space/parse/image"
            payload = f"apikey={OCR_API_KEY}&language=rus&base64Image=data:image/jpeg;base64,{encoded}"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            response = safe_url_request(url, payload, headers)
            if response.startswith("Ошибка"):
                self.update_photo_result(response, 'Ошибка сервера')
                return
                
            result = json.loads(response)
            text = result.get('ParsedResults', [{}])[0].get('ParsedText', '')
            self.update_photo_result(text, 'Готово!')
            save_note(text)
        except Exception as e:
            self.update_photo_result(f'Ошибка: {e}', 'Ошибка')

    @mainthread
    def update_photo_result(self, text, status):
        self.ids.photo_output.text = text
        self.ids.photo_status.text = status

    def save_manual_text(self):
        text = self.ids.manual_text_input.text.strip()
        if text:
            save_note(text)
            self.ids.manual_text_input.text = ''
            self.ids.photo_status.text = 'Текст сохранен в Историю!'

    # --- ЧАТ ---
    def send_chat_message(self):
        text = self.ids.chat_input.text.strip()
        if not text: return
        self.ids.chat_input.text = ''
        self.add_chat_bubble(text, is_user=True)
        self.chat_history.append({'role': 'user', 'content': text})
        
        loading = Label(text='Думаю...', size_hint_y=None, height=dp(40), italic=True)
        self.ids.chat_container.add_widget(loading)
        
        def worker():
            try:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENROUTER_API_KEY}"}
                payload = json.dumps({"model": "meta-llama/llama-3-8b-instruct", "messages": self.chat_history})
                response = safe_url_request(url, payload, headers)
                
                if response.startswith("Ошибка"):
                    self.update_chat_answer(response, loading)
                    return
                    
                result = json.loads(response)
                answer = result["choices"][0]["message"]["content"].strip()
                self.update_chat_answer(answer, loading)
            except Exception as e:
                self.update_chat_answer(f"Ошибка: {e}", loading)
                
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_chat_answer(self, answer, loading_label):
        if loading_label and loading_label.parent:
            self.ids.chat_container.remove_widget(loading_label)
        self.add_chat_bubble(answer, is_user=False)

    def add_chat_bubble(self, text, is_user):
        # Создаем контейнер для пузыря
        bubble_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        
        # Текст
        lbl = Label(text=text, size_hint_y=None, text_size=(dp(300), None), 
                    halign='right' if is_user else 'left', valign='top', 
                    color=(0, 0, 0, 1) if is_user else (0, 0, 0.5, 1))
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        bubble_box.add_widget(lbl)

        # Кнопка копирования для ответа бота
        if not is_user:
            copy_btn = Button(text='Копировать ответ', size_hint_y=None, height=dp(35), 
                              background_normal='', background_color=(0.8, 0.85, 0.9, 1), color=(0.1, 0.1, 0.1, 1), font_size='12sp')
            copy_btn.bind(on_release=lambda x: self.copy_text(text))
            bubble_box.add_widget(copy_btn)

        bubble_box.height = lbl.height + (dp(40) if not is_user else dp(5))
        self.ids.chat_container.add_widget(bubble_box)
        
        # Анимация плавного появления
        bubble_box.opacity = 0
        Animation(opacity=1, d=0.3).start(bubble_box)
        Clock.schedule_once(lambda dt: setattr(self.ids.chat_container, 'height', self.ids.chat_container.minimum_height), 0.1)

    def copy_text(self, text):
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(text)
        # Можно добавить всплывающее уведомление, но пока просто копируем

def save_note(text):
    try:
        note_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        data = {"id": note_id, "title": text[:20], "text": text}
        with open(os.path.join(NOTES_FOLDER, f"{note_id}.json"), 'w', encoding='utf-8') as f: 
            json.dump(data, f, ensure_ascii=False)
    except Exception as e: print(e)

def get_all_notes():
    notes = []
    if not os.path.exists(NOTES_FOLDER): return notes
    for fname in sorted(os.listdir(NOTES_FOLDER), reverse=True):
        if fname.endswith('.json'):
            try:
                with open(os.path.join(NOTES_FOLDER, fname), 'r', encoding='utf-8') as f: 
                    notes.append(json.load(f))
            except: pass
    return notes

class NotesApp(App):
    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    NotesApp().run()
