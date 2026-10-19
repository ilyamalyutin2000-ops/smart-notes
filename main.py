# -*- coding: utf-8 -*-
import os
import json
import threading
import base64
import ssl
import urllib.request
from datetime import datetime

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.toolbar import MDTopAppBar

from kivy.clock import Clock, mainthread
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.lang import Builder

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
        base = MDApp.get_running_app().user_data_dir
        NOTES_FOLDER = os.path.join(base, "notes")
        os.makedirs(NOTES_FOLDER, exist_ok=True)
    except: NOTES_FOLDER = "."

# ============================================================
# ЗАПРОСЫ
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
# KV РАЗМЕТКА (Дизайн)
# ============================================================
KV = """
<MainScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            title: "Умный конспект"
            elevation: 4
            right_action_items: [["history", lambda x: root.switch_tab('history')], ["book-open-variant", lambda x: root.switch_tab('learn')]]
            
        MDBoxLayout:
            id: content_manager
            # Тут будет меняться контент
            
        MDBottomNavigation:
            panel_color: 1, 1, 1, 1
            
            MDBottomNavigationItem:
                name: 'chat'
                text: 'Чат'
                icon: 'chat'
                on_tab_press: root.switch_tab('chat')
                
                MDBoxLayout:
                    orientation: 'vertical'
                    padding: dp(10)
                    
                    MDScrollView:
                        id: chat_scroll
                        MDBoxLayout:
                            id: chat_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(10)
                    
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(60)
                        spacing: dp(10)
                        
                        MDTextField:
                            id: chat_input
                            hint_text: 'Введите сообщение...'
                            mode: "rectangle"
                            on_text_validate: root.send_chat_message()
                            
                        MDIconButton:
                            icon: 'send'
                            theme_icon_color: "Custom"
                            icon_color: 0.15, 0.45, 0.85, 1
                            on_release: root.send_chat_message()

            MDBottomNavigationItem:
                name: 'new'
                text: 'Загрузка'
                icon: 'plus-circle'
                on_tab_press: root.switch_tab('new')
                
                MDBoxLayout:
                    orientation: 'vertical'
                    padding: dp(15)
                    spacing: dp(15)
                    
                    MDLabel:
                        text: "Загрузите фото конспекта или введите текст"
                        halign: "center"
                        theme_text_color: "Secondary"
                        
                    MDRaisedButton:
                        text: "Открыть проводник"
                        pos_hint: {"center_x": .5}
                        on_release: root.open_system_file_picker()
                        
                    MDTextField:
                        id: photo_path
                        hint_text: 'Путь к файлу'
                        mode: "rectangle"
                        
                    MDTextField:
                        id: manual_text
                        hint_text: 'Введите текст вручную...'
                        mode: "rectangle"
                        multiline: True
                        
                    MDRaisedButton:
                        text: "Сохранить"
                        pos_hint: {"center_x": .5}
                        on_release: root.save_manual_text()

            MDBottomNavigationItem:
                name: 'history'
                text: 'История'
                icon: 'history'
                on_tab_press: root.switch_tab('history')
                
                MDScrollView:
                    MDList:
                        id: history_list

            MDBottomNavigationItem:
                name: 'learn'
                text: 'Обучение'
                icon: 'book-open-variant'
                on_tab_press: root.switch_tab('learn')
                
                MDBoxLayout:
                    orientation: 'vertical'
                    padding: dp(15)
                    spacing: dp(15)
                    
                    MDLabel:
                        text: "ИИ-Учитель"
                        font_style: "H4"
                        halign: "center"
                        
                    MDRaisedButton:
                        text: "Загрузить материал для плана"
                        pos_hint: {"center_x": .5}
                        on_release: root.process_learn_material()
                        
                    MDScrollView:
                        id: learn_scroll
                        MDBoxLayout:
                            id: learn_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(10)
                            
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(60)
                        spacing: dp(10)
                        
                        MDTextField:
                            id: learn_input
                            hint_text: 'Ваш ответ учителю...'
                            mode: "rectangle"
                            on_text_validate: root.send_learn_message()
                            
                        MDIconButton:
                            icon: 'send'
                            on_release: root.send_learn_message()
"""

# ============================================================
# ЛОГИКА
# ============================================================
class MainScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_history = []
        self.learn_history = []
        Clock.schedule_once(self.setup_app, 0.5)

    def setup_app(self, dt):
        init_storage()

    def switch_tab(self, name):
        # Безопасное переключение экранов через нижнее меню
        pass # MDBottomNavigation делает это автоматически

    # --- ЗАГРУЗКА ФАЙЛОВ ---
    def open_system_file_picker(self):
        # Безопасный путь: используем стандартный Android Intent (но без вылетов)
        try:
            from android import mActivity
            from jnius import autoclass, cast
            Intent = autoclass('android.content.Intent')
            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.setType('*/*')
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            
            # В KivyMD это не всегда работает напрямую, поэтому даем путь по умолчанию
            self.ids.photo_path.text = "/storage/emulated/0/Download/"
            self.show_dialog("Выберите файл вручную", "Вставьте полный путь к файлу в поле 'Путь к файлу' и нажмите Сохранить.")
        except:
            self.show_dialog("Ошибка", "Системный выбор файлов недоступен. Введите путь вручную.")

    def show_dialog(self, title, text):
        dialog = MDDialog(
            title=title,
            text=text,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())]
        )
        dialog.open()

    def save_manual_text(self):
        text = self.ids.manual_text.text.strip()
        if text:
            save_note(text)
            self.ids.manual_text.text = ''
            self.show_dialog("Успех", "Текст сохранен в Историю!")

    def load_history(self):
        # Заглушка для истории (можно расширить)
        pass

    # --- ЧАТ ---
    def send_chat_message(self):
        text = self.ids.chat_input.text.strip()
        if not text: return
        self.ids.chat_input.text = ''
        self.add_chat_bubble(text, is_user=True)
        self.chat_history.append({'role': 'user', 'content': text})
        
        loading = MDLabel(text='Думаю...', size_hint_y=None, height=dp(40), italic=True)
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
        # Пузырь в стиле Telegram
        card = MDCard(
            orientation='vertical',
            padding=dp(10),
            size_hint=(None, None),
            size=(dp(280), dp(60)),
            pos_hint={"right": 1} if is_user else {"left": 1},
            md_bg_color=(0.9, 0.95, 1, 1) if is_user else (1, 1, 1, 1),
            radius=[15, 15, 0, 15] if is_user else [15, 15, 15, 0],
            elevation=2
        )
        
        lbl = MDLabel(text=text, theme_text_color="Custom", text_color=(0,0,0,1), size_hint_y=None)
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        lbl.bind(texture_size=lambda *x: setattr(card, 'height', lbl.height + dp(20)))
        card.add_widget(lbl)
        
        self.ids.chat_container.add_widget(card)
        
        # Анимация
        card.opacity = 0
        Animation(opacity=1, d=0.3).start(card)

    # --- ОБУЧЕНИЕ ---
    def process_learn_material(self):
        # Здесь логика загрузки файла и отправки нейросети
        self.show_dialog("Обучение", "Функция обучения находится в разработке.")

    def send_learn_message(self):
        text = self.ids.learn_input.text.strip()
        if not text: return
        self.ids.learn_input.text = ''
        # Логика чата с ИИ-учителем

def save_note(text):
    try:
        note_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        data = {"id": note_id, "title": text[:20], "text": text}
        with open(os.path.join(NOTES_FOLDER, f"{note_id}.json"), 'w', encoding='utf-8') as f: 
            json.dump(data, f, ensure_ascii=False)
    except Exception as e: print(e)

class NotesApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        Builder.load_string(KV)
        sm = MDScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    NotesApp().run()
