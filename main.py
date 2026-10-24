# -*- coding: utf-8 -*-
import os
import json
import threading
import urllib.request
import ssl
import re
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
from kivy.uix.slider import Slider
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.clipboard import Clipboard

# ============================================================
# ГЛОБАЛЬНЫЕ НАСТРОЙКИ ЦВЕТОВ
# ============================================================
COLORS = {
    "bg_app": (0.07, 0.07, 0.07, 1),      # Фон приложения
    "btn": (0.15, 0.45, 0.85, 1),         # Цвет кнопок
    "text": (1, 1, 1, 1),                 # Цвет текста
    "chat_user": (0.1, 0.3, 0.6, 1),      # Твой пузырь
    "chat_bot": (0.15, 0.15, 0.15, 1),    # Пузырь бота
}

Window.clearcolor = COLORS["bg_app"]
Window.softinput_mode = 'below_target'

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

API_KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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",
    "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"
]
MODEL_NAME = "openrouter/free"

BASE_DIR, NOTES_FOLDER = "", ""

def init_storage():
    global BASE_DIR, NOTES_FOLDER
    try:
        BASE_DIR = App.get_running_app().user_data_dir
        NOTES_FOLDER = os.path.join(BASE_DIR, "notes")
        os.makedirs(NOTES_FOLDER, exist_ok=True)
    except: 
        BASE_DIR, NOTES_FOLDER = ".", "."

# ============================================================
# ЗАПРОСЫ
# ============================================================
def safe_openrouter_request(messages, max_tokens=2500):
    if not API_KEYS: return "Ошибка: Нет ключей."
    for key in API_KEYS:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
            sys_instruction = {
                "role": "system", 
                "content": "Отвечай на русском. Код оборачивай в ```. Не используй markdown-таблицы."
            }
            payload = {"model": MODEL_NAME, "messages": [sys_instruction] + messages, "max_tokens": max_tokens}
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req, context=ssl_context, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result["choices"][0]["message"].get("content")
                if content and content.strip(): return content.strip()
        except: continue
    return "Лимит ключей исчерпан (429). Попробуйте позже."

# ============================================================
# КНОПКА С ВОЗМОЖНОСТЬЮ СМЕНЫ ЦВЕТА
# ============================================================
class ColorButton(Button):
    def __init__(self, **kwargs):
        self.bg_color = kwargs.pop('bg_color', COLORS["btn"])
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        
        with self.canvas.before:
            self.color_inst = Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def set_color(self, new_color):
        self.bg_color = new_color
        self.color_inst.rgba = new_color

# ============================================================
# ИНТЕРФЕЙС
# ============================================================
KV = """
#:import SlideTransition kivy.uix.screenmanager.SlideTransition
#:import ColorButton __main__.ColorButton

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
                            background_color: 0.15, 0.15, 0.15, 1
                            foreground_color: 1, 1, 1, 1
                            on_text_validate: root.send_chat()
                        ColorButton:
                            text: '▶'
                            size_hint_x: None
                            width: dp(55)
                            on_release: root.send_chat()

            Screen:
                name: 'learn'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(15)
                    spacing: dp(10)
                    
                    BoxLayout:
                        size_hint_y: None
                        height: dp(40)
                        Label:
                            text: "Кол-во частей:"
                            color: 1, 1, 1, 1
                        TextInput:
                            id: parts_input
                            text: "0"
                            input_filter: 'int'
                            size_hint_x: 0.3
                            background_color: 0.15, 0.15, 0.15, 1
                            foreground_color: 1, 1, 1, 1
                        Label:
                            text: "(0=Авто)"
                            color: 0.5, 0.5, 0.5, 1

                    TextInput:
                        id: learn_text
                        hint_text: 'Вставьте конспект...'
                        multiline: True
                        size_hint_y: 0.3
                        background_color: 0.15, 0.15, 0.15, 1
                        foreground_color: 1, 1, 1, 1
                        
                    ColorButton:
                        text: 'Составить план'
                        size_hint_y: None
                        height: dp(55)
                        on_release: root.start_learning()
                        
                    ScrollView:
                        id: lessons_scroll
                        BoxLayout:
                            id: lessons_box
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(8)
                            
                    ScrollView:
                        id: learn_scroll
                        BoxLayout:
                            id: learn_box
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            
                    BoxLayout:
                        size_hint_y: None
                        height: dp(55)
                        spacing: dp(8)
                        TextInput:
                            id: learn_input
                            hint_text: 'Ответ...'
                            background_color: 0.15, 0.15, 0.15, 1
                            foreground_color: 1, 1, 1, 1
                            on_text_validate: root.send_learn()
                        ColorButton:
                            text: '▶'
                            size_hint_x: None
                            width: dp(55)
                            on_release: root.send_learn()

            Screen:
                name: 'settings'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(15)
                    spacing: dp(15)
                    
                    Label:
                        text: "Цвета (нажми, чтобы применить):"
                        color: 1, 1, 1, 1
                        
                    BoxLayout:
                        size_hint_y: None
                        height: dp(50)
                        spacing: dp(10)
                        ColorButton:
                            text: "Синий"
                            bg_color: (0.15, 0.45, 0.85, 1)
                            on_release: root.apply_theme((0.15, 0.45, 0.85, 1), (0.07, 0.07, 0.07, 1))
                        ColorButton:
                            text: "Зеленый"
                            bg_color: (0.2, 0.6, 0.4, 1)
                            on_release: root.apply_theme((0.2, 0.6, 0.4, 1), (0.1, 0.1, 0.1, 1))
                        ColorButton:
                            text: "Красный"
                            bg_color: (0.7, 0.2, 0.2, 1)
                            on_release: root.apply_theme((0.7, 0.2, 0.2, 1), (0.05, 0.05, 0.05, 1))

                    Label:
                        text: "Фон приложения:"
                        color: 1, 1, 1, 1
                        
                    BoxLayout:
                        size_hint_y: None
                        height: dp(50)
                        spacing: dp(10)
                        ColorButton:
                            text: "Темный"
                            bg_color: (0.2, 0.2, 0.2, 1)
                            on_release: root.set_bg((0.07, 0.07, 0.07, 1))
                        ColorButton:
                            text: "Серый"
                            bg_color: (0.4, 0.4, 0.4, 1)
                            on_release: root.set_bg((0.2, 0.2, 0.2, 1))
                        ColorButton:
                            text: "Светлый"
                            bg_color: (0.8, 0.8, 0.8, 1)
                            color: (0,0,0,1)
                            on_release: root.set_bg((0.9, 0.9, 0.9, 1))

        BoxLayout:
            size_hint_y: None
            height: dp(60)
            spacing: dp(8)
            padding: dp(5), dp(5)
            canvas.before:
                Color:
                    rgba: 0.1, 0.1, 0.1, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            ColorButton:
                id: nav_chat
                text: 'Чат'
                on_release: root.switch('chat')
            ColorButton:
                id: nav_learn
                text: 'Обучение'
                on_release: root.switch('learn')
            ColorButton:
                id: nav_set
                text: '⚙'
                size_hint_x: None
                width: dp(60)
                on_release: root.switch('settings')
"""

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_history = []
        self.learn_context = ""
        Clock.schedule_once(self.setup, 0.5)

    def setup(self, dt):
        init_storage()
        self.switch('chat')

    # Смена вкладки
    def switch(self, name):
        self.ids.content_manager.current = name
        # Подсветка активной кнопки
        self.ids.nav_chat.set_color(COLORS["btn"] if name == 'chat' else (0.2, 0.2, 0.2, 1))
        self.ids.nav_learn.set_color(COLORS["btn"] if name == 'learn' else (0.2, 0.2, 0.2, 1))

    # === НАСТРОЙКИ ===
    def apply_theme(self, btn_color, bg_color):
        COLORS["btn"] = btn_color
        COLORS["bg_app"] = bg_color
        Window.clearcolor = bg_color
        
        # Перекрашиваем все кнопки на экране
        for widget in self.walk():
            if isinstance(widget, ColorButton):
                # Не трогаем кнопки выбора цвета в настройках
                if widget.parent and "settings" in str(widget.parent):
                    continue
                # Если это навигация
                if widget.id == 'nav_chat':
                    widget.set_color(btn_color if self.ids.content_manager.current == 'chat' else (0.2, 0.2, 0.2, 1))
                elif widget.id == 'nav_learn':
                    widget.set_color(btn_color if self.ids.content_manager.current == 'learn' else (0.2, 0.2, 0.2, 1))
                else:
                    widget.set_color(btn_color)

    def set_bg(self, color):
        COLORS["bg_app"] = color
        Window.clearcolor = color
        if color[0] > 0.5:
            COLORS["text"] = (0, 0, 0, 1)
        else:
            COLORS["text"] = (1, 1, 1, 1)

    # === ЧАТ ===
    def send_chat(self):
        text = self.ids.chat_input.text.strip()
        if not text: return
        self.ids.chat_input.text = ''
        self.add_bubble(self.ids.chat_container, text, True)
        self.chat_history.append({'role': 'user', 'content': text})
        
        loading = Label(text='...', color=(0.5, 0.5, 0.5, 1))
        self.ids.chat_container.add_widget(loading)
        
        def worker():
            ans = safe_openrouter_request(self.chat_history)
            if ans and not ans.startswith("Лимит"):
                self.chat_history.append({'role': 'assistant', 'content': ans})
            self.update_chat(ans, loading)
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_chat(self, ans, loading):
        if loading.parent: self.ids.chat_container.remove_widget(loading)
        self.add_bubble(self.ids.chat_container, ans, False)

    # === ОБУЧЕНИЕ ===
    def start_learning(self):
        text = self.ids.learn_text.text.strip()
        if not text: return
        self.learn_context = text
        self.ids.lessons_box.clear_widgets()
        self.ids.learn_box.clear_widgets()
        
        try:
            parts = int(self.ids.parts_input.text)
        except:
            parts = 0
            
        prompt = f"Разбей текст на {parts} частей." if parts > 0 else "Разбей текст на логические части (3-7)."
        self.add_bubble(self.ids.learn_box, "Составляю план...", False)
        
        def worker():
            ans = safe_openrouter_request([{"role": "user", "content": f"{prompt} ТОЛЬКО цифры. Текст:\n{text[:2500]}"}], 3000)
            self.show_lessons(ans, text)
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def show_lessons(self, plan, text):
        self.ids.learn_box.clear_widgets()
        if not plan or plan.startswith("Лимит"):
            self.add_bubble(self.ids.learn_box, f"Ошибка: {plan}", False)
            return
            
        self.add_bubble(self.ids.learn_box, "План готов:", False)
        for line in plan.split('\n'):
            if line.strip() and line[0].isdigit():
                btn = ColorButton(text=line, size_hint_y=None, height=dp(50), bg_color=COLORS["btn"])
                btn.bind(on_release=lambda b, l=line: self.open_lesson(l, text))
                self.ids.lessons_box.add_widget(btn)

    def open_lesson(self, title, context):
        popup = Popup(title=title, size_hint=(1, 1), auto_dismiss=False)
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        lbl = Label(text="Генерирую урок...", color=(1,1,1,1))
        content.add_widget(lbl)
        popup.content = content
        popup.open()
        
        def worker():
            ans = safe_openrouter_request([{"role": "user", "content": f"Объясни '{title}' простым текстом. Текст:\n{context[:2000]}"}], 3000)
            self.show_full_lesson(popup, ans)
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def show_full_lesson(self, popup, text):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        scroll = ScrollView()
        lbl = Label(text=text, size_hint_y=None, text_size=(Window.width - dp(40), None), halign='left', valign='top', color=(1,1,1,1))
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        scroll.add_widget(lbl)
        content.add_widget(scroll)
        
        btn = ColorButton(text="Закрыть", size_hint_y=None, height=dp(50), bg_color=(0.7, 0.2, 0.2, 1))
        btn.bind(on_release=lambda x: popup.dismiss())
        content.add_widget(btn)
        popup.content = content

    def send_learn(self):
        text = self.ids.learn_input.text.strip()
        if not text: return
        self.ids.learn_input.text = ''
        self.add_bubble(self.ids.learn_box, text, True)
        def worker():
            ans = safe_openrouter_request([{"role": "user", "content": text}])
            self.update_learn(ans)
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_learn(self, ans):
        self.add_bubble(self.ids.learn_box, ans, False)

    # === ПУЗЫРИ (Без вылетов) ===
    def add_bubble(self, container, text, is_user):
        box = BoxLayout(orientation='horizontal', size_hint_y=None, spacing=dp(5))
        bubble = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        
        lbl = Label(text=text, size_hint_y=None, text_size=(dp(250), None), 
                    halign='right' if is_user else 'left', valign='top',
                    color=COLORS["text"])
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        
        with bubble.canvas.before:
            Color(*(COLORS["chat_user"]) if is_user else COLORS["chat_bot"])
            rect = Rectangle(pos=bubble.pos, size=bubble.size)
        bubble.bind(pos=lambda *x: setattr(rect, 'pos', bubble.pos))
        bubble.bind(size=lambda *x: setattr(rect, 'size', bubble.size))
        
        lbl.padding = (dp(10), dp(10))
        bubble.add_widget(lbl)
        
        if is_user:
            box.add_widget(Label(size_hint_x=0.05))
            box.add_widget(bubble)
        else:
            box.add_widget(bubble)
            box.add_widget(Label(size_hint_x=0.05))
            
        box.height = lbl.height + dp(20)
        container.add_widget(box)
        Clock.schedule_once(lambda dt: setattr(container, 'height', container.minimum_height), 0.1)

class NotesApp(App):
    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    NotesApp().run()
