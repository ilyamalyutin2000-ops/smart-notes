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
from kivy.uix.filechooser import FileChooserListView
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window

# ============================================================
# НАСТРОЙКА ОКНА
# ============================================================
Window.clearcolor = get_color_from_hex('#F4F6F9')

# ИГНОРИРУЕМ ОШИБКИ SSL (Чтобы Android не блокировал HTTPS)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# ============================================================
# НАСТРОЙКИ
# ============================================================
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
# СЕТЕВОЙ ЗАПРОС (С защитой от вылетов)
# ============================================================
def safe_url_request(url, json_data=None, headers=None):
    try:
        data = json_data.encode('utf-8') if json_data else None
        req = urllib.request.Request(url, data=data, headers=headers or {}, method='POST' if data else 'GET')
        
        with urllib.request.urlopen(req, context=ssl_context, timeout=20) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return f"Ошибка API ({e.code}): {error_body[:150]}"
    except Exception as e:
        return f"Ошибка сети: {str(e)}"

# ============================================================
# ИНТЕРФЕЙС
# ============================================================
KV = """
<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(15)
        spacing: dp(15)
        
        Label:
            size_hint_y: None
            height: dp(40)
            text: 'Умный конспект'
            font_size: '24sp'
            bold: True
            color: 0.1, 0.15, 0.2, 1
            
        BoxLayout:
            size_hint_y: None
            height: dp(55)
            spacing: dp(10)
            
            Button:
                id: btn_tab_new
                text: 'Загрузка'
                font_size: '16sp'
                background_normal: ''
                background_color: 0.15, 0.45, 0.85, 1
                on_release: root.switch_tab('new')
            Button:
                id: btn_tab_chat
                text: 'Чат'
                font_size: '16sp'
                background_normal: ''
                background_color: 0.4, 0.4, 0.45, 1
                on_release: root.switch_tab('chat')
                
        ScreenManager:
            id: content_manager
            transition: SlideTransition(direction='left', duration=0.3)
            
            Screen:
                name: 'new'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(15)
                    
                    Button:
                        text: 'Загрузить фото/файл'
                        size_hint_y: None
                        height: dp(60)
                        font_size: '18sp'
                        background_normal: ''
                        background_color: 0.55, 0.3, 0.8, 1
                        on_release: root.open_file_chooser()
                        
                    Label:
                        id: photo_status
                        text: 'Текст сохранится автоматически'
                        color: 0.4, 0.4, 0.45, 1
                        size_hint_y: None
                        height: dp(30)
                        
                    ScrollView:
                        Label:
                            id: photo_output
                            text: 'Здесь появится текст...'
                            size_hint_y: None
                            height: self.texture_size[1]
                            text_size: self.width, None
                            color: 0.1, 0.15, 0.2, 1
                            
            Screen:
                name: 'chat'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(15)
                    
                    ScrollView:
                        BoxLayout:
                            id: chat_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(10)
                            
                    BoxLayout:
                        size_hint_y: None
                        height: dp(60)
                        spacing: dp(10)
                        
                        TextInput:
                            id: chat_input
                            hint_text: 'Введите вопрос...'
                            multiline: False
                            background_color: 1, 1, 1, 1
                            foreground_color: 0.1, 0.15, 0.2, 1
                            padding: dp(15), dp(15)
                            on_text_validate: root.send_chat_message()
                            
                        Button:
                            text: 'Ввод'
                            size_hint_x: None
                            width: dp(90)
                            font_size: '16sp'
                            background_normal: ''
                            background_color: 0.15, 0.45, 0.85, 1
                            on_release: root.send_chat_message()
"""

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_history = []
        Clock.schedule_once(self.setup_app, 0.5)

    def setup_app(self, dt):
        init_storage()

    def switch_tab(self, name):
        self.ids.content_manager.current = name
        if name == 'new':
            self.ids.btn_tab_new.background_color = (0.15, 0.45, 0.85, 1)
            self.ids.btn_tab_chat.background_color = (0.4, 0.4, 0.45, 1)
        else:
            self.ids.btn_tab_new.background_color = (0.4, 0.4, 0.45, 1)
            self.ids.btn_tab_chat.background_color = (0.15, 0.45, 0.85, 1)

    def open_file_chooser(self):
        content = BoxLayout(orientation='vertical', padding=dp(10))
        filechooser = FileChooserListView(path="/storage/emulated/0/Download", filters=['*.png', '*.jpg', '*.jpeg'])
        content.add_widget(filechooser)
        
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        btn_cancel = Button(text='Отмена', background_normal='', background_color=(0.7, 0.7, 0.7, 1))
        btn_open = Button(text='Открыть', background_normal='', background_color=(0.2, 0.6, 0.4, 1))
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_open)
        content.add_widget(btn_box)
        
        popup = Popup(title='Выберите файл', content=content, size_hint=(0.95, 0.95))
        
        def process_file(selection):
            popup.dismiss()
            if selection:
                self.ids.photo_status.text = 'Обработка...'
                threading.Thread(target=self.process_photo, args=(selection[0],), daemon=True).start()
                
        btn_cancel.bind(on_release=lambda x: popup.dismiss())
        btn_open.bind(on_release=lambda x: process_file(filechooser.selection))
        popup.open()

    def process_photo(self, path):
        try:
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
            if result.get('IsErroredOnProcessing'):
                raise Exception(result.get('ErrorMessage'))
            text = result.get('ParsedResults', [{}])[0].get('ParsedText', '')
            
            self.update_photo_result(text, 'Готово! Сохранено.')
            save_note(text)
        except Exception as e:
            self.update_photo_result(f'Ошибка: {e}', 'Ошибка разбора')

    @mainthread
    def update_photo_result(self, text, status):
        self.ids.photo_output.text = text
        self.ids.photo_status.text = status

    def send_chat_message(self):
        text = self.ids.chat_input.text.strip()
        if not text: return
        self.ids.chat_input.text = ''
        self.add_chat_bubble(text, is_user=True)
        self.chat_history.append({'role': 'user', 'content': text})
        
        loading = Label(text='Думаю...', size_hint_y=None, height=dp(40), italic=True, color=(0.5, 0.5, 0.5, 1))
        self.ids.chat_container.add_widget(loading)
        
        def worker():
            try:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json", 
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}"
                }
                payload = json.dumps({
                    "model": "meta-llama/llama-3-8b-instruct",
                    "messages": self.chat_history
                })
                response = safe_url_request(url, payload, headers)
                
                if response.startswith("Ошибка"):
                    self.update_chat_answer(response, loading)
                    return
                    
                result = json.loads(response)
                answer = result["choices"][0]["message"]["content"].strip()
                self.update_chat_answer(answer, loading)
            except Exception as e:
                self.update_chat_answer(f"Ошибка разбора: {e}", loading)
                
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_chat_answer(self, answer, loading_label):
        if loading_label and loading_label.parent:
            self.ids.chat_container.remove_widget(loading_label)
        self.add_chat_bubble(answer, is_user=False)

    def add_chat_bubble(self, text, is_user):
        msg_layout = BoxLayout(orientation='horizontal', size_hint_y=None, spacing=dp(5))
        lbl = Label(text=text, size_hint_y=None, text_size=(dp(300), None), 
                    halign='right' if is_user else 'left', valign='top', 
                    color=(0, 0, 0, 1) if is_user else (0, 0, 0.5, 1), markup=True)
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        
        if is_user:
            msg_layout.add_widget(Label(size_hint_x=0.2))
            msg_layout.add_widget(lbl)
        else:
            msg_layout.add_widget(lbl)
            msg_layout.add_widget(Label(size_hint_x=0.2))

        msg_layout.height = lbl.height + dp(10)
        self.ids.chat_container.add_widget(msg_layout)
        Clock.schedule_once(lambda dt: setattr(self.ids.chat_container, 'height', self.ids.chat_container.minimum_height), 0.1)

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
