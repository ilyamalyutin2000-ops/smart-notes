# -*- coding: utf-8 -*-
import os
import json
import threading
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
from kivy.core.window import Window
import requests

# ============================================================
# ИСПРАВЛЕНИЕ КЛАВИАТУРЫ (Окно сдвигается вверх при вводе)
# ============================================================
Window.softinput_mode = 'below_target'

# ============================================================
# НАСТРОЙКИ (Ключи)
# ============================================================
OCR_API_KEY = "K86772432188957"
GROQ_API_KEY = "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"

# ============================================================
# ПУТИ ДЛЯ ANDROID И ЗАПРОС ПРАВ
# ============================================================
def get_data_path(folder_name):
    if platform == 'android':
        from android.storage import app_storage_path
        base = app_storage_path()
    else:
        base = os.getcwd()
    path = os.path.join(base, folder_name)
    os.makedirs(path, exist_ok=True)
    return path

NOTES_FOLDER = get_data_path("notes")
UPLOADS_FOLDER = get_data_path("uploads")

# ============================================================
# ИНТЕРФЕЙС (KV-разметка)
# ============================================================
KV = """
<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: 0.94, 0.95, 0.97, 1
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            size_hint_y: None
            height: dp(50)
            text: 'Умный конспект'
            font_size: '20sp'
            bold: True
            color: 0.1, 0.13, 0.18, 1

        BoxLayout:
            size_hint_y: None
            height: dp(50)
            padding: dp(5)
            spacing: dp(5)
            Button:
                text: 'Новый'
                background_color: 0.22, 0.5, 0.79, 1
                on_release: root.switch_tab('new')
            Button:
                text: 'История'
                background_color: 0.8, 0.8, 0.8, 1
                on_release: root.switch_tab('history')
            Button:
                text: 'Чат'
                background_color: 0.8, 0.8, 0.8, 1
                on_release: root.switch_tab('chat')

        ScreenManager:
            id: content_manager
            size_hint_y: 1
            
            Screen:
                name: 'new'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(10)
                    spacing: dp(10)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(45)
                        spacing: dp(5)
                        Button:
                            text: 'Файл'
                            background_color: 0.22, 0.5, 0.79, 1
                            on_release: root.switch_subtab('photo')
                        Button:
                            text: 'Текст'
                            background_color: 0.8, 0.8, 0.8, 1
                            on_release: root.switch_subtab('text')
                    
                    ScreenManager:
                        id: subtab_manager
                        size_hint_y: 1
                        
                        Screen:
                            name: 'photo'
                            BoxLayout:
                                orientation: 'vertical'
                                spacing: dp(10)
                                Button:
                                    text: 'Загрузить фото/файл'
                                    size_hint_y: None
                                    height: dp(60)
                                    background_color: 0.49, 0.35, 0.83, 1
                                    on_release: root.open_file_chooser()
                                Label:
                                    id: photo_status
                                    text: 'Выберите файл для обработки'
                                    size_hint_y: None
                                    height: dp(30)
                                    color: 0.44, 0.5, 0.58, 1
                                ScrollView:
                                    Label:
                                        id: photo_output
                                        text: 'Здесь появится распознанный текст.'
                                        size_hint_y: None
                                        height: self.texture_size[1]
                                        text_size: self.width, None
                                        padding: dp(10), dp(10)
                                        halign: 'left'
                                        valign: 'top'
                                        color: 0.1, 0.13, 0.18, 1
                                BoxLayout:
                                    size_hint_y: None
                                    height: dp(50)
                                    spacing: dp(5)
                                    Button:
                                        text: 'Скопировать'
                                        background_color: 0.22, 0.63, 0.41, 1
                                        on_release: root.copy_photo_text()
                                    Button:
                                        text: 'Сохранить'
                                        background_color: 0.19, 0.51, 0.81, 1
                                        on_release: root.save_photo_text()
                        Screen:
                            name: 'text'
                            BoxLayout:
                                orientation: 'vertical'
                                spacing: dp(10)
                                TextInput:
                                    id: manual_input
                                    hint_text: 'Вставьте или напишите текст конспекта здесь...'
                                    multiline: True
                                    font_size: '15sp'
                                    background_color: 1, 1, 1, 1
                                    foreground_color: 0.1, 0.13, 0.18, 1
                                Label:
                                    id: manual_status
                                    text: 'Вставьте текст и нажмите кнопку'
                                    size_hint_y: None
                                    height: dp(30)
                                    color: 0.44, 0.5, 0.58, 1
                                Button:
                                    text: 'Обработать и сохранить'
                                    size_hint_y: None
                                    height: dp(55)
                                    background_color: 0.49, 0.35, 0.83, 1
                                    on_release: root.process_manual_text()
            
            Screen:
                name: 'history'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(10)
                    Button:
                        text: 'Обновить'
                        size_hint_y: None
                        height: dp(45)
                        background_color: 0.22, 0.5, 0.79, 1
                        on_release: root.load_history()
                    ScrollView:
                        BoxLayout:
                            id: history_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(8)
            
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
                            spacing: dp(8)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(55)
                        spacing: dp(5)
                        TextInput:
                            id: chat_input
                            hint_text: 'Введите вопрос...'
                            multiline: False
                            font_size: '15sp'
                            on_text_validate: root.send_chat_message()
                        Button:
                            text: 'Отправить'
                            size_hint_x: None
                            width: dp(110)
                            background_color: 0.19, 0.51, 0.81, 1
                            on_release: root.send_chat_message()
                    Button:
                        text: 'Очистить диалог'
                        size_hint_y: None
                        height: dp(45)
                        background_color: 0.9, 0.24, 0.24, 1
                        on_release: root.clear_chat()
"""

# ============================================================
# ЛОГИКА ПРИЛОЖЕНИЯ
# ============================================================
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_photo_text = ""
        self.chat_history = []

    def switch_tab(self, name):
        self.ids.content_manager.current = name
        if name == 'history':
            self.load_history()

    def switch_subtab(self, name):
        self.ids.subtab_manager.current = name

    def open_file_chooser(self):
        content = BoxLayout(orientation='vertical')
        # Убрали фильтры, теперь можно выбрать любой файл
        filechooser = FileChooserListView(path="/storage/emulated/0/Download")
        content.add_widget(filechooser)
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
        btn_cancel = Button(text='Отмена')
        btn_open = Button(text='Открыть', background_color=(0.22, 0.63, 0.41, 1))
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_open)
        content.add_widget(btn_box)
        popup = Popup(title='Выберите файл', content=content, size_hint=(0.95, 0.95))
        def cancel(*_): popup.dismiss()
        def open_file(*_):
            if filechooser.selection:
                path = filechooser.selection[0]
                popup.dismiss()
                self.process_photo(path)
        btn_cancel.bind(on_release=cancel)
        btn_open.bind(on_release=open_file)
        popup.open()

    def process_photo(self, path):
        self.ids.photo_status.text = 'Обработка файла...'
        self.ids.photo_output.text = 'Пожалуйста, подождите...'
        def worker():
            try:
                raw = recognize_photo(path)
                ready = clean_text(raw)
                self.update_photo_result(ready, 'Готово!')
            except Exception as e:
                self.update_photo_result(f'Ошибка: {e}', 'Ошибка при обработке')
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_photo_result(self, text, status):
        self.current_photo_text = text
        self.ids.photo_output.text = text
        self.ids.photo_status.text = status

    def copy_photo_text(self):
        if self.current_photo_text:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(self.current_photo_text)
            self.ids.photo_status.text = 'Скопировано!'

    def save_photo_text(self):
        if not self.current_photo_text: return
        save_note(self.current_photo_text)
        self.ids.photo_status.text = 'Конспект сохранён!'

    def process_manual_text(self):
        text = self.ids.manual_input.text.strip()
        if not text:
            self.ids.manual_status.text = 'Введите текст конспекта'
            return
        cleaned = clean_manual_text(text)
        save_note(cleaned)
        self.ids.manual_input.text = ''
        self.ids.manual_status.text = 'Конспект сохранён!'

    def load_history(self):
        container = self.ids.history_container
        container.clear_widgets()
        notes = get_all_notes()
        if not notes:
            container.add_widget(Label(text='Пока нет сохранённых конспектов', size_hint_y=None, height=dp(80), color=(0.63, 0.68, 0.75, 1)))
            return
        for note in notes:
            btn = Button(text=f"{note['title']}\n{note['date']}", size_hint_y=None, height=dp(70), background_color=(0.97, 0.98, 0.99, 1), color=(0.1, 0.13, 0.18, 1))
            btn.bind(on_release=lambda b, n=note: self.open_note(n))
            container.add_widget(btn)

    def open_note(self, note):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        scroll = ScrollView()
        lbl = Label(text=note['text'], size_hint_y=None, text_size=(None, None), halign='left', valign='top', color=(0.1, 0.13, 0.18, 1))
        lbl.bind(width=lambda *x: setattr(lbl, 'text_size', (lbl.width, None)))
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        scroll.add_widget(lbl)
        content.add_widget(scroll)
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
        btn_copy = Button(text='Скопировать', background_color=(0.22, 0.63, 0.41, 1))
        btn_delete = Button(text='Удалить', background_color=(0.9, 0.24, 0.24, 1))
        btn_box.add_widget(btn_copy)
        btn_box.add_widget(btn_delete)
        content.add_widget(btn_box)
        popup = Popup(title=note['title'], content=content, size_hint=(0.95, 0.9))
        def copy_text(*_):
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(note['text'])
        def delete_note_action(*_):
            delete_note(note['id'])
            popup.dismiss()
            self.load_history()
        btn_copy.bind(on_release=copy_text)
        btn_delete.bind(on_release=delete_note_action)
        popup.open()

    def send_chat_message(self):
        text = self.ids.chat_input.text.strip()
        if not text: return
        self.ids.chat_input.text = ''
        self.add_chat_bubble(text, is_user=True)
        self.chat_history.append({'role': 'user', 'content': text})
        loading = Label(text='Думаю...', size_hint_y=None, height=dp(40), color=(0.44, 0.5, 0.58, 1))
        self.ids.chat_container.add_widget(loading)
        def worker():
            answer = answer_question(self.chat_history)
            self.chat_history.append({'role': 'assistant', 'content': answer})
            self.update_chat_answer(answer, loading)
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_chat_answer(self, answer, loading_label):
        self.ids.chat_container.remove_widget(loading_label)
        self.add_chat_bubble(answer, is_user=False)

    def add_chat_bubble(self, text, is_user):
        lbl = Label(text=text, size_hint_y=None, text_size=(dp(300), None), halign='right' if is_user else 'left', valign='top', padding=(dp(10), dp(10)), color=(1, 1, 1, 1) if is_user else (0.1, 0.13, 0.18, 1))
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1] + dp(20)))
        self.ids.chat_container.add_widget(lbl)
        Clock.schedule_once(lambda dt: setattr(self.ids.chat_scroll, 'scroll_y', 0), 0.1)

    def clear_chat(self):
        self.chat_history = []
        self.ids.chat_container.clear_widgets()

# ============================================================
# API И ХРАНЕНИЕ
# ============================================================
def clean_text(raw_text):
    if not raw_text or not raw_text.strip(): return "Не удалось распознать текст."
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GROQ_API_KEY}"}
        payload = {"model": "openai/gpt-oss-120b", "messages": [{"role": "system", "content": "Убери символы (*, #, `, _), исправь ошибки. Только чистый текст на русском."}, {"role": "user", "content": raw_text}], "temperature": 0.3}
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code == 200: return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e: print("Groq clean error:", e)
    return raw_text.replace('*', '').replace('#', '').replace('`', '').replace('_', '').strip()

def clean_manual_text(raw_text):
    if not raw_text or not raw_text.strip(): return ""
    return raw_text.replace('*', '').replace('#', '').replace('`', '').replace('_', '').strip()

def recognize_photo(filepath):
    url = "https://api.ocr.space/parse/image"
    payload = {'apikey': OCR_API_KEY, 'language': 'rus', 'scale': 'true', 'isOverlayRequired': 'false'}
    with open(filepath, 'rb') as f:
        files = {'file': (os.path.basename(filepath), f, 'image/jpeg')}
        resp = requests.post(url, data=payload, files=files, timeout=90)
    result = resp.json()
    if result.get('IsErroredOnProcessing'): raise Exception(result.get('ErrorMessage', 'Ошибка OCR'))
    return result.get('ParsedResults', [{}])[0].get('ParsedText', '')

def save_note(text):
    note_id = datetime.now().strftime("%Y%m%d_%H%M%S%f")
    title = text.strip().split('\n')[0][:50] if text.strip() else "Без названия"
    date = datetime.now().strftime("%d.%m.%Y %H:%M")
    data = {"id": note_id, "title": title, "date": date, "text": text}
    with open(os.path.join(NOTES_FOLDER, f"{note_id}.json"), 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False)

def get_all_notes():
    notes = []
    if not os.path.exists(NOTES_FOLDER): return notes
    for fname in sorted(os.listdir(NOTES_FOLDER), reverse=True):
        if fname.endswith('.json'):
            try:
                with open(os.path.join(NOTES_FOLDER, fname), 'r', encoding='utf-8') as f: notes.append(json.load(f))
            except: pass
    return notes

def delete_note(note_id):
    path = os.path.join(NOTES_FOLDER, f"{note_id}.json")
    if os.path.exists(path): os.remove(path)

def find_relevant_notes(question):
    notes = get_all_notes()
    if not notes: return ""
    words = [w.lower() for w in question.split() if len(w) > 3]
    scored = [(sum(n["text"].lower().count(w) for w in words), n) for n in notes]
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda x: -x[0])
    return "\n\n".join(n["text"] for _, n in scored[:3])[:6000]

def answer_question(messages):
    last_q = messages[-1]["content"]
    context = find_relevant_notes(last_q)
    if not context: 
        return "В конспектах нет информации по этой теме. Сначала сохраните конспект."
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GROQ_API_KEY}"}
    payload = {"model": "openai/gpt-oss-120b", "messages": [{"role": "system", "content": f"Отвечай только по конспектам:\n{context}"}] + messages}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=90)
        if resp.status_code != 200:
            return f"Ошибка API (Код {resp.status_code}). Возможно, заблокирован доступ или закончился лимит."
        result = resp.json()
        if "choices" not in result:
            return "Нейросеть вернула странный ответ. Попробуйте переформулировать вопрос."
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e: 
        return f"Ошибка соединения: {str(e)}"

# ============================================================
# ЗАПУСК
# ============================================================
class NotesApp(App):
    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

    def build(self):
        self.title = "Умный конспект"
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    NotesApp().run()
