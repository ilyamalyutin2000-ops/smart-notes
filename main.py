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
from kivy.utils import platform, get_color_from_hex
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
import requests

# ============================================================
# ИСПРАВЛЕНИЕ КЛАВИАТУРЫ
# ============================================================
Window.softinput_mode = 'below_target'
Window.clearcolor = get_color_from_hex('#F4F6F9')

# ============================================================
# НАСТРОЙКИ (Ключи)
# ============================================================
OCR_API_KEY = "K86772432188957"
GROQ_API_KEY = "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"

# ============================================================
# ПУТИ ДЛЯ ANDROID
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

# ============================================================
# КАСТОМНЫЙ КЛАСС ДЛЯ КНОПОК С ЗАКРУГЛЕННЫМИ КРАЯМИ
# ============================================================
class RoundedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0) # Прозрачный фон
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(15)])

# ============================================================
# ИНТЕРФЕЙС (KV-разметка)
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
            color: 0.1, 0.15, 0.2, 1

        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(8)
            
            RoundedButton:
                text: 'Новый'
                bg_color: 0.15, 0.45, 0.85, 1
                on_release: root.switch_tab('new')
            RoundedButton:
                text: 'История'
                bg_color: 0.4, 0.4, 0.45, 1
                on_release: root.switch_tab('history')
            RoundedButton:
                text: 'Чат'
                bg_color: 0.4, 0.4, 0.45, 1
                on_release: root.switch_tab('chat')

        ScreenManager:
            id: content_manager
            
            Screen:
                name: 'new'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    
                    BoxLayout:
                        size_hint_y: None
                        height: dp(45)
                        spacing: dp(8)
                        RoundedButton:
                            text: 'Файл'
                            bg_color: 0.15, 0.45, 0.85, 1
                            on_release: root.switch_subtab('photo')
                        RoundedButton:
                            text: 'Текст'
                            bg_color: 0.4, 0.4, 0.45, 1
                            on_release: root.switch_subtab('text')
                            
                    ScreenManager:
                        id: subtab_manager
                        
                        Screen:
                            name: 'photo'
                            BoxLayout:
                                orientation: 'vertical'
                                spacing: dp(10)
                                RoundedButton:
                                    text: 'Загрузить фото/файл'
                                    size_hint_y: None
                                    height: dp(60)
                                    bg_color: 0.55, 0.3, 0.8, 1
                                    on_release: root.open_file_chooser()
                                Label:
                                    id: photo_status
                                    text: 'Выберите файл'
                                    size_hint_y: None
                                    height: dp(30)
                                    color: 0.4, 0.4, 0.45, 1
                                ScrollView:
                                    Label:
                                        id: photo_output
                                        text: 'Здесь появится текст...'
                                        size_hint_y: None
                                        height: self.texture_size[1]
                                        text_size: self.width, None
                                        color: 0.1, 0.15, 0.2, 1
                                BoxLayout:
                                    size_hint_y: None
                                    height: dp(50)
                                    spacing: dp(8)
                                    RoundedButton:
                                        text: 'Копировать'
                                        bg_color: 0.2, 0.6, 0.4, 1
                                        on_release: root.copy_photo_text()
                                    RoundedButton:
                                        text: 'Сохранить'
                                        bg_color: 0.2, 0.5, 0.8, 1
                                        on_release: root.save_photo_text()
                        Screen:
                            name: 'text'
                            BoxLayout:
                                orientation: 'vertical'
                                spacing: dp(10)
                                TextInput:
                                    id: manual_input
                                    hint_text: 'Введите текст...'
                                    multiline: True
                                    background_color: 1, 1, 1, 1
                                    foreground_color: 0.1, 0.15, 0.2, 1
                                Label:
                                    id: manual_status
                                    text: 'Введите текст'
                                    size_hint_y: None
                                    height: dp(30)
                                    color: 0.4, 0.4, 0.45, 1
                                RoundedButton:
                                    text: 'Сохранить'
                                    size_hint_y: None
                                    height: dp(55)
                                    bg_color: 0.55, 0.3, 0.8, 1
                                    on_release: root.process_manual_text()

            Screen:
                name: 'history'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    RoundedButton:
                        text: 'Обновить'
                        size_hint_y: None
                        height: dp(45)
                        bg_color: 0.15, 0.45, 0.85, 1
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
                    spacing: dp(10)
                    ScrollView:
                        id: chat_scroll
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
                            background_color: 1, 1, 1, 1
                            foreground_color: 0.1, 0.15, 0.2, 1
                            on_text_validate: root.send_chat_message()
                        RoundedButton:
                            text: 'Отправить'
                            size_hint_x: None
                            width: dp(110)
                            bg_color: 0.15, 0.45, 0.85, 1
                            on_release: root.send_chat_message()
                    RoundedButton:
                        text: 'Очистить диалог'
                        size_hint_y: None
                        height: dp(45)
                        bg_color: 0.85, 0.25, 0.25, 1
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
        if name == 'history': self.load_history()

    def switch_subtab(self, name):
        self.ids.subtab_manager.current = name

    def open_file_chooser(self):
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView(path="/storage/emulated/0/Download")
        content.add_widget(filechooser)
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
        btn_cancel = Button(text='Отмена', background_color=(0.7, 0.7, 0.7, 1))
        btn_open = Button(text='Открыть', background_color=(0.2, 0.6, 0.4, 1))
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_open)
        content.add_widget(btn_box)
        popup = Popup(title='Выберите файл', content=content, size_hint=(0.95, 0.95))
        def cancel(*_): popup.dismiss()
        def open_file(*_):
            if filechooser.selection:
                popup.dismiss()
                self.process_photo(filechooser.selection[0])
        btn_cancel.bind(on_release=cancel)
        btn_open.bind(on_release=open_file)
        popup.open()

    def process_photo(self, path):
        self.ids.photo_status.text = 'Обработка...'
        self.ids.photo_output.text = 'Подождите...'
        def worker():
            try:
                raw = recognize_photo(path)
                ready = clean_text(raw)
                self.update_photo_result(ready, 'Готово!')
            except Exception as e:
                self.update_photo_result(f'Ошибка: {e}', 'Ошибка')
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
        if self.current_photo_text:
            save_note(self.current_photo_text)
            self.ids.photo_status.text = 'Сохранено!'

    def process_manual_text(self):
        text = self.ids.manual_input.text.strip()
        if not text: return
        save_note(clean_manual_text(text))
        self.ids.manual_input.text = ''
        self.ids.manual_status.text = 'Сохранено!'

    def load_history(self):
        container = self.ids.history_container
        container.clear_widgets()
        notes = get_all_notes()
        if not notes:
            container.add_widget(Label(text='Пусто...', color=(0.6, 0.6, 0.6, 1)))
            return
        for note in notes:
            btn = RoundedButton(text=f"{note['title']}\n{note['date']}", size_hint_y=None, height=dp(70), bg_color=(1, 1, 1, 1), color=(0.1, 0.1, 0.1, 1))
            btn.bind(on_release=lambda b, n=note: self.open_note(n))
            container.add_widget(btn)

    def open_note(self, note):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        scroll = ScrollView()
        lbl = Label(text=note['text'], size_hint_y=None, text_size=(None, None), color=(0.1, 0.1, 0.1, 1))
        lbl.bind(width=lambda *x: setattr(lbl, 'text_size', (lbl.width, None)))
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        scroll.add_widget(lbl)
        content.add_widget(scroll)
        popup = Popup(title=note['title'], content=content, size_hint=(0.95, 0.9))
        popup.open()

    def send_chat_message(self):
        text = self.ids.chat_input.text.strip()
        if not text: return
        self.ids.chat_input.text = ''
        self.add_chat_bubble(text, is_user=True)
        self.chat_history.append({'role': 'user', 'content': text})
        
        loading = Label(text='Думаю...', size_hint_y=None, height=dp(40), color=(0.5, 0.5, 0.5, 1), italic=True)
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
        # Контейнер для одного сообщения
        msg_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        
        # Настройка стилей
        if is_user:
            bg_color = (0.95, 0.95, 0.95, 1)
            text_color = (0, 0, 0, 1)
            halign = 'right'
            font_style = 'italic' # Курсив для юзера
        else:
            bg_color = (0.9, 0.95, 1, 1)
            text_color = (0.1, 0.1, 0.1, 1)
            halign = 'left'
            font_style = 'normal'

        # Текст сообщения
        lbl = Label(
            text=text, size_hint_y=None, text_size=(dp(320), None),
            halign=halign, valign='top', color=text_color,
            italic=(font_style == 'italic'), markup=True
        )
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        
        # Фон сообщения (закругленный)
        with lbl.canvas.before:
            Color(*bg_color)
            rect = RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[dp(12)])
        lbl.bind(pos=lambda *x: setattr(rect, 'pos', lbl.pos))
        lbl.bind(size=lambda *x: setattr(rect, 'size', lbl.size))
        
        msg_box.add_widget(lbl)

        # Кнопка копирования для бота
        if not is_user:
            copy_btn = RoundedButton(text='📋 Копировать', size_hint_y=None, height=dp(30), bg_color=(0.8, 0.85, 0.9, 1), color=(0.2, 0.2, 0.2, 1), font_size='12sp')
            copy_btn.bind(on_release=lambda b: self.copy_text_to_clipboard(text))
            msg_box.add_widget(copy_btn)

        msg_box.height = lbl.height + (dp(30) if not is_user else 0)
        self.ids.chat_container.add_widget(msg_box)
        Clock.schedule_once(lambda dt: setattr(self.ids.chat_scroll, 'scroll_y', 0), 0.1)

    def copy_text_to_clipboard(self, text):
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(text)

    def clear_chat(self):
        self.chat_history = []
        self.ids.chat_container.clear_widgets()


# ============================================================
# API И ХРАНЕНИЕ
# ============================================================
def clean_text(raw_text):
    if not raw_text: return ""
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GROQ_API_KEY}"}
        payload = {"model": "openai/gpt-oss-120b", "messages": [{"role": "system", "content": "Убери все символы разметки. Только чистый текст."}, {"role": "user", "content": raw_text}]}
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code == 200: return resp.json()["choices"][0]["message"]["content"].strip()
    except: pass
    return raw_text.replace('*', '').replace('#', '').strip()

def clean_manual_text(raw_text):
    return raw_text.strip()

def recognize_photo(filepath):
    url = "https://api.ocr.space/parse/image"
    payload = {'apikey': OCR_API_KEY, 'language': 'rus', 'scale': 'true'}
    with open(filepath, 'rb') as f:
        resp = requests.post(url, data=payload, files={'file': f}, timeout=90)
    result = resp.json()
    if result.get('IsErroredOnProcessing'): raise Exception(result.get('ErrorMessage'))
    return result.get('ParsedResults', [{}])[0].get('ParsedText', '')

def save_note(text):
    note_id = datetime.now().strftime("%Y%m%d_%H%M%S%f")
    title = text.strip().split('\n')[0][:40]
    data = {"id": note_id, "title": title, "date": datetime.now().strftime("%d.%m.%Y"), "text": text}
    with open(os.path.join(NOTES_FOLDER, f"{note_id}.json"), 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False)

def get_all_notes():
    notes = []
    if not os.path.exists(NOTES_FOLDER): return notes
    for fname in sorted(os.listdir(NOTES_FOLDER), reverse=True):
        if fname.endswith('.json'):
            with open(os.path.join(NOTES_FOLDER, fname), 'r', encoding='utf-8') as f: notes.append(json.load(f))
    return notes

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
        return "В конспектах нет информации по этой теме."
        
    # ЖЕСТКИЙ ПРОМПТ ДЛЯ ИИ
    system_prompt = (
        "Ты ассистент. Отвечай на вопрос, используя ТОЛЬКО текст из конспекта ниже.\n"
        "ВАЖНО: Если в конспекте НЕТ информации по вопросу, напиши: 'В конспекте этой информации нет.', "
        "а затем добавь блок 'Дополнительная информация:' и напиши то, что знаешь сам.\n"
        "ВАЖНО: Не используй символы Markdown (никаких *, #, |, _, `). "
        "Пиши обычным текстом, используй отступы для абзацев.\n\n"
        f"КОНСПЕКТ:\n{context}"
    )
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GROQ_API_KEY}"}
    payload = {
        "model": "openai/gpt-oss-120b", 
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "temperature": 0.5
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=90)
        if resp.status_code != 200: return f"Ошибка API: {resp.status_code}"
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e: 
        return f"Ошибка: {str(e)}"

# ============================================================
# ЗАПУСК
# ============================================================
class NotesApp(App):
    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    NotesApp().run()
