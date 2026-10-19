# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime
from kivy.app import App
from kivy.clock import Clock
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
# ПУТИ (Личная папка)
# ============================================================
NOTES_FOLDER = ""
def init_storage():
    global NOTES_FOLDER
    try:
        base = App.get_running_app().user_data_dir
        NOTES_FOLDER = os.path.join(base, "notes")
        os.makedirs(NOTES_FOLDER, exist_ok=True)
    except: NOTES_FOLDER = "."

KV = """
<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(10)
        spacing: dp(10)

        Label:
            size_hint_y: None
            height: dp(40)
            text: 'ТЕСТ БЕЗ СЕТИ'
            font_size: '22sp'
            bold: True

        BoxLayout:
            size_hint_y: None
            height: dp(45)
            spacing: dp(5)
            Button:
                text: 'Загрузка'
                on_release: root.switch_tab('new')
            Button:
                text: 'История'
                on_release: root.switch_tab('history')

        ScreenManager:
            id: content_manager
            
            Screen:
                name: 'new'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    Button:
                        text: 'Создать конспект'
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
"""

class MainScreen(Screen):
    def switch_tab(self, name):
        self.ids.content_manager.current = name
        if name == 'history': self.load_history()

    def create_test_note(self):
        text = f"Тестовый конспект создан {datetime.now().strftime('%H:%M:%S')}."
        save_note(text)
        print("Сохранено!")

    def load_history(self):
        container = self.ids.history_container
        container.clear_widgets()
        notes = get_all_notes()
        if not notes:
            container.add_widget(Label(text='Пусто', size_hint_y=None, height=dp(50)))
            return
        for note in notes:
            btn = Button(text=note.get('title', ''), size_hint_y=None, height=dp(60))
            container.add_widget(btn)

def save_note(text):
    try:
        note_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        data = {"id": note_id, "title": text[:20], "text": text}
        with open(os.path.join(NOTES_FOLDER, f"{note_id}.json"), 'w', encoding='utf-8') as f: 
            json.dump(data, f, ensure_ascii=False)
    except Exception as e: print(f"Ошибка: {e}")

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
    def on_start(self):
        init_storage()
    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    NotesApp().run()
