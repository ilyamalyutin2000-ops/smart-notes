# -*- coding: utf-8 -*-
import os
import json
import threading
import base64
from datetime import datetime
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.metrics import dp
from kivy.utils import platform

# ============================================================
# ИМПОРТЫ ANDROID (Для безопасного интернета)
# ============================================================
if platform == 'android':
    from jnius import autoclass, cast
    from android import mActivity
    URL = autoclass('java.net.URL')
    InputStreamReader = autoclass('java.io.InputStreamReader')
    BufferedReader = autoclass('java.io.BufferedReader')
    StringBuilder = autoclass('java.lang.StringBuilder')

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
# БЕЗОПАСНЫЙ СЕТЕВОЙ ЗАПРОС ЧЕРЕЗ JAVA
# ============================================================
def safe_url_request(url, json_data=None, headers=None):
    if platform != 'android':
        return "Ошибка: Этот код работает только на Android."
    
    try:
        url_obj = URL(url)
        conn = url_obj.openConnection()
        conn.setRequestMethod("POST" if json_data else "GET")
        conn.setDoOutput(True)
        
        if headers:
            for key, val in headers.items():
                conn.setRequestProperty(key, val)
                
        if json_data:
            output_stream = conn.getOutputStream()
            output_stream.write(json_data.encode('utf-8'))
            output_stream.flush()
            output_stream.close()
            
        response_code = conn.getResponseCode()
        
        # Читаем ответ сервера, даже если это ошибка (403, 502 и т.д.)
        if response_code != 200:
            error_stream = conn.getErrorStream()
            if error_stream is not None:
                reader = BufferedReader(InputStreamReader(error_stream))
                error_response = StringBuilder()
                line = reader.readLine()
                while line is not None:
                    error_response.append(line)
                    line = reader.readLine()
                reader.close()
                return f"Ошибка API ({response_code}): {error_response.toString()[:200]}"
            return f"Ошибка API: {response_code}"
            
        input_stream = InputStreamReader(conn.getInputStream())
        reader = BufferedReader(input_stream)
        response = StringBuilder()
        line = reader.readLine()
        while line is not None:
            response.append(line)
            line = reader.readLine()
        reader.close()
        
        res_str = str(response.toString())
        if not res_str.strip():
            return "Ошибка: Сервер вернул пустой ответ."
            
        return res_str
    except Exception as e:
        print(f"Сетевая ошибка: {e}")
        return f"Ошибка сети: {e}"

# ============================================================
# ИНТЕРФЕЙС
# ============================================================
KV = """
<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(10)
        spacing: dp(10)
        Label:
            size_hint_y: None
            height: dp(40)
            text: 'Умный конспект'
            font_size: '22sp'
            bold: True
        BoxLayout:
            size_hint_y: None
            height: dp(45)
            spacing: dp(5)
            Button:
                id: btn_tab_new
                text: 'Загрузка'
                background_color: 0.15, 0.45, 0.85, 1
                on_release: root.switch_tab('new')
            Button:
                id: btn_tab_chat
                text: 'Чат'
                background_color: 0.4, 0.4, 0.45, 1
                on_release: root.switch_tab('chat')
        ScreenManager:
            id: content_manager
            Screen:
                name: 'new'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    Button:
                        text: 'Загрузить фото/файл'
                        size_hint_y: None
                        height: dp(60)
                        on_release: root.open_file_chooser()
                    Label:
                        id: photo_status
                        text: 'Текст сохранится автоматически'
                    ScrollView:
                        Label:
                            id: photo_output
                            text: 'Здесь появится текст...'
                            size_hint_y: None
                            height: self.texture_size[1]
                            text_size: self.width, None
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
                            spacing: dp(12)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(55)
                        spacing: dp(8)
                        TextInput:
                            id: chat_input
                            hint_text: 'Введите вопрос...'
                            multiline: False
                            on_text_validate: root.send_chat_message()
                        Button:
                            text: 'Ввод'
                            size_hint_x: None
                            width: dp(90)
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
        self.ids.btn_tab_new.background_color = (0.15, 0.45, 0.85, 1) if name == 'new' else (0.4, 0.4, 0.45, 1)
        self.ids.btn_tab_chat.background_color = (0.15, 0.45, 0.85, 1) if name == 'chat' else (0.4, 0.4, 0.45, 1)

    def open_file_chooser(self):
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView(path="/storage/emulated/0/Download", filters=['*.png', '*.jpg', '*.jpeg'])
        content.add_widget(filechooser)
        btn_box = BoxLayout(size_hint_y=None, height=dp(50))
        btn_cancel = Button(text='Отмена', on_release=lambda x: popup.dismiss())
        btn_open = Button(text='Открыть', on_release=lambda x: process_file(filechooser.selection))
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_open)
        content.add_widget(btn_box)
        popup = Popup(title='Выберите файл', content=content, size_hint=(0.95, 0.95))
        
        def process_file(selection):
            popup.dismiss()
            if selection:
                self.ids.photo_status.text = 'Обработка (может занять время)...'
                threading.Thread(target=self.process_photo, args=(selection[0],), daemon=True).start()
        popup.open()

    def process_photo(self, path):
        try:
            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            
            url = "https://api.ocr.space/parse/image"
            payload = f"apikey={OCR_API_KEY}&language=rus&base64Image=data:image/jpeg;base64,{encoded}"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            response = safe_url_request(url, payload, headers)
            
            # Защита от не-JSON ответа
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
        loading = Label(text='Думаю...', size_hint_y=None, height=dp(40))
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
                
                # Защита от не-JSON ответа
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
        lbl = Label(text=text, size_hint_y=None, text_size=(dp(320), None), 
                    halign='right' if is_user else 'left', valign='top', 
                    color=(0,0,0,1) if is_user else (0,0,0.5,1))
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        self.ids.chat_container.add_widget(lbl)

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
