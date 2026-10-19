# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.metrics import dp

# ============================================================
# БЕЗОПАСНЫЕ ПУТИ (Личная папка приложения)
# ============================================================
NOTES_FOLDER = ""

def init_storage():
    global NOTES_FOLDER
    try:
        base = App.get_running_app().user_data_dir
        NOTES_FOLDER = os.path.join(base, "notes")
        os.makedirs(NOTES_FOLDER, exist_ok=True)
        print(f"Папка сохранений: {NOTES_FOLDER}")
    except Exception as e:
        print(f"Ошибка папки: {e}")
        NOTES_FOLDER = "."

# ============================================================
# ИНТЕРФЕЙС (KV)
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
            text: 'Офлайн Конспект'
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
                id: btn_tab_history
                text: 'История'
                background_color: 0.4, 0.4, 0.45, 1
                on_release: root.switch_tab('history')
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
                        text: 'Создать тестовый конспект'
                        size_hint_y: None
                        height: dp(60)
                        background_color: 0.55, 0.3, 0.8, 1
                        on_release: root.create_test_note()

            Screen:
                name: 'history'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    Button:
                        text: 'Обновить список'
                        size_hint_y: None
                        height: dp(45)
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
                            hint_text: 'Напишите что-нибудь...'
                            multiline: False
                            on_text_validate: root.send_fake_chat()
                        Button:
                            text: 'Ввод'
                            size_hint_x: None
                            width: dp(90)
                            background_color: 0.15, 0.45, 0.85, 1
                            on_release: root.send_fake_chat()
"""

# ============================================================
# ЛОГИКА
# ============================================================
class MainScreen(Screen):
    def switch_tab(self, name):
        self.ids.content_manager.current = name
        self.ids.btn_tab_new.background_color = (0.15, 0.45, 0.85, 1) if name == 'new' else (0.4, 0.4, 0.45, 1)
        self.ids.btn_tab_history.background_color = (0.15, 0.45, 0.85, 1) if name == 'history' else (0.4, 0.4, 0.45, 1)
        self.ids.btn_tab_chat.background_color = (0.15, 0.45, 0.85, 1) if name == 'chat' else (0.4, 0.4, 0.45, 1)
        
        if name == 'history':
            self.load_history()

    def create_test_note(self):
        text = f"Это тестовый конспект, созданный {datetime.now().strftime('%H:%M:%S')}."
        save_note(text)
        self.ids.btn_tab_new.text = "Сохранено!"
        Clock.schedule_once(lambda dt: setattr(self.ids.btn_tab_new, 'text', 'Создать тестовый конспект'), 2)

    def load_history(self):
        container = self.ids.history_container
        container.clear_widgets()
        notes = get_all_notes()
        if not notes:
            container.add_widget(Label(text='Пока нет конспектов', size_hint_y=None, height=dp(50)))
            return
        for note in notes:
            btn = Button(text=note.get('title', 'Без названия'), size_hint_y=None, height=dp(60))
            btn.bind(on_release=lambda b, n=note: self.open_note(n))
            container.add_widget(btn)

    def open_note(self, note):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(text=note.get('text', '')))
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
        btn_close = Button(text='Закрыть', on_release=lambda x: popup.dismiss())
        btn_delete = Button(text='Удалить', background_color=(0.85, 0.25, 0.25, 1))
        btn_box.add_widget(btn_close)
        btn_box.add_widget(btn_delete)
        content.add_widget(btn_box)
        
        popup = Popup(title=note.get('title', ''), content=content, size_hint=(0.9, 0.8))
        
        def delete(*_):
            delete_note(note['id'])
            popup.dismiss()
            self.load_history()
            
        btn_delete.bind(on_release=delete)
        popup.open()

    def send_fake_chat(self):
        text = self.ids.chat_input.text.strip()
        if not text: return
        self.ids.chat_input.text = ''
        
        # Выводим сообщение пользователя
        self.ids.chat_container.add_widget(Label(text=f"Вы: {text}", size_hint_y=None, height=dp(40), color=(0,0,0,1)))
        
        # Имитация ответа
        fake_answer = "Это офлайн-режим. Нейросеть отключена для проверки стабильности."
        self.ids.chat_container.add_widget(Label(text=f"Бот: {fake_answer}", size_hint_y=None, height=dp(60), color=(0,0,0.5,1)))

# ============================================================
# ХРАНЕНИЕ
# ============================================================
def save_note(text):
    try:
        note_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        title = text[:20]
        data = {"id": note_id, "title": title, "text": text}
        with open(os.path.join(NOTES_FOLDER, f"{note_id}.json"), 'w', encoding='utf-8') as f: 
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

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

def delete_note(note_id):
    try:
        path = os.path.join(NOTES_FOLDER, f"{note_id}.json")
        if os.path.exists(path): os.remove(path)
    except: pass

# ============================================================
# ЗАПУСК
# ============================================================
class NotesApp(App):
    def on_start(self):
        # Инициализируем папку при старте
        init_storage()

    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    NotesApp().run()
