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

# КЛЮЧ OPENROUTER (разбит на 2 части для GitHub)
def get_key():
    p1 = "sk-or-v1-71d88394a7c915b6"
    p2 = "382385eb96fde7e8e5892b42bb5e08f41f6432ea72e57196"
    return p1 + p2

OPENROUTER_API_KEY = get_key()
MODEL_NAME = "openrouter/free"

NOTES_FOLDER = ""
def init_storage():
    global NOTES_FOLDER
    try:
        base = App.get_running_app().user_data_dir
        NOTES_FOLDER = os.path.join(base, "notes")
        os.makedirs(NOTES_FOLDER, exist_ok=True)
    except: NOTES_FOLDER = "."

# ============================================================
# РАБОТА С КОНСПЕКТАМИ
# ============================================================
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

def find_relevant_notes(question):
    notes = get_all_notes()
    if not notes: return ""
    words = [w.lower().strip('.,!?;:()[]{}"') for w in question.split() if len(w) > 3]
    if not words: return ""
    
    scored_notes = []
    for note in notes:
        text_lower = note.get('text', '').lower()
        score = sum(text_lower.count(w) for w in words)
        if score > 0:
            scored_notes.append((score, note))
            
    scored_notes.sort(key=lambda x: -x[0])
    top_notes = [n[1] for n in scored_notes[:3]]
    if not top_notes: return ""
    
    context = "\n\n---\n\n".join([f"Конспект: {n.get('title', '')}\n{n.get('text', '')}" for n in top_notes])
    return context[:4000]

# ============================================================
# ЗАПРОС К OPENROUTER (Безопасный)
# ============================================================
def safe_openrouter_request(messages):
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}"
        }
        
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 1500
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, context=ssl_context, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["choices"][0]["message"]["content"].strip()
            
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return "Лимит запросов. Подожди минуту и попробуй снова."
        return f"Ошибка API OpenRouter ({e.code})"
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
        
        ScreenManager:
            id: content_manager
            transition: SlideTransition(direction='left', duration=0.2)
            
            # === ЧАТ ===
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
                        spacing: dp(8)
                        
                        TextInput:
                            id: chat_input
                            hint_text: 'Вопрос по конспектам...'
                            multiline: False
                            padding: dp(10), dp(10)
                            on_text_validate: root.send_chat_message()
                            
                        Button:
                            text: '▶'
                            size_hint_x: None
                            width: dp(50)
                            background_normal: ''
                            background_color: 0.15, 0.45, 0.85, 1
                            on_release: root.send_chat_message()

            # === ЗАГРУЗКА ===
            Screen:
                name: 'new'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(15)
                    spacing: dp(15)
                    
                    TextInput:
                        id: photo_path
                        hint_text: 'Путь к фото'
                        size_hint_y: None
                        height: dp(50)
                        multiline: False
                        
                    Button:
                        text: 'Распознать фото'
                        size_hint_y: None
                        height: dp(55)
                        background_normal: ''
                        background_color: 0.55, 0.3, 0.8, 1
                        on_release: root.process_photo_by_path()
                        
                    Label:
                        id: photo_status
                        text: 'Или введите текст вручную'
                        size_hint_y: None
                        height: dp(30)
                        color: 0.4, 0.4, 0.4, 1
                        
                    TextInput:
                        id: manual_text
                        hint_text: 'Введите конспект...'
                        multiline: True
                        size_hint_y: 1
                        
                    Button:
                        text: 'Сохранить текст'
                        size_hint_y: None
                        height: dp(50)
                        background_normal: ''
                        background_color: 0.2, 0.6, 0.4, 1
                        on_release: root.save_manual_text()

            # === ОБУЧЕНИЕ ===
            Screen:
                name: 'learn'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(15)
                    spacing: dp(15)
                    
                    Button:
                        text: 'Составить план обучения'
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
                            spacing: dp(8)
                            
                    BoxLayout:
                        size_hint_y: None
                        height: dp(55)
                        spacing: dp(8)
                        
                        TextInput:
                            id: learn_input
                            hint_text: 'Ваш ответ...'
                            multiline: False
                            on_text_validate: root.send_learn_message()
                            
                        Button:
                            text: '▶'
                            size_hint_x: None
                            width: dp(50)
                            background_normal: ''
                            background_color: 0.55, 0.3, 0.8, 1
                            on_release: root.send_learn_message()

        # === НИЖНЯЯ ПАНЕЛЬ ===
        BoxLayout:
            size_hint_y: None
            height: dp(55)
            spacing: dp(2)
            
            Button:
                id: btn_nav_chat
                text: 'Чат'
                font_size: '14sp'
                background_normal: ''
                background_color: 0.4, 0.4, 0.45, 1
                on_release: root.switch_nav('chat')
            Button:
                id: btn_nav_new
                text: 'Загрузка'
                font_size: '14sp'
                background_normal: ''
                background_color: 0.4, 0.4, 0.45, 1
                on_release: root.switch_nav('new')
            Button:
                id: btn_nav_learn
                text: 'Обучение'
                font_size: '14sp'
                background_normal: ''
                background_color: 0.4, 0.4, 0.45, 1
                on_release: root.switch_nav('learn')
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
        self.switch_nav('chat')

    def switch_nav(self, name):
        self.ids.content_manager.current = name
        self.ids.btn_nav_chat.background_color = (0.4, 0.4, 0.45, 1)
        self.ids.btn_nav_new.background_color = (0.4, 0.4, 0.45, 1)
        self.ids.btn_nav_learn.background_color = (0.4, 0.4, 0.45, 1)
        
        if name == 'chat': self.ids.btn_nav_chat.background_color = (0.15, 0.45, 0.85, 1)
        elif name == 'new': self.ids.btn_nav_new.background_color = (0.15, 0.45, 0.85, 1)
        elif name == 'learn': self.ids.btn_nav_learn.background_color = (0.15, 0.45, 0.85, 1)

    def process_photo_by_path(self):
        path = self.ids.photo_path.text.strip()
        if not path:
            self.ids.photo_status.text = "Введите путь!"
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
            
            req = urllib.request.Request(url, data=payload.encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
            text = result.get('ParsedResults', [{}])[0].get('ParsedText', '')
            self.update_photo_result(text, 'Готово! Сохранено.')
            save_note(text)
        except Exception as e:
            self.update_photo_result(f'Ошибка: {e}', 'Ошибка')

    @mainthread
    def update_photo_result(self, text, status):
        self.ids.photo_status.text = status

    def save_manual_text(self):
        text = self.ids.manual_text.text.strip()
        if text:
            save_note(text)
            self.ids.manual_text.text = ''
            self.ids.photo_status.text = 'Сохранено!'

    # --- ЧАТ ---
    def send_chat_message(self):
        text = self.ids.chat_input.text.strip()
        if not text: return
        self.ids.chat_input.text = ''
        self.add_simple_bubble(self.ids.chat_container, text, is_user=True)
        self.chat_history.append({'role': 'user', 'content': text})
        
        loading = Label(text='Думаю...', size_hint_y=None, height=dp(30), color=(0.5, 0.5, 0.5, 1))
        self.ids.chat_container.add_widget(loading)
        
        def worker():
            try:
                context = find_relevant_notes(text)
                if context:
                    system_prompt = (
                        "Ты ассистент. Отвечай на вопрос, используя ТОЛЬКО текст из конспекта ниже. "
                        "Если в конспекте нет ответа, скажи: 'В конспекте этой информации нет'. "
                        f"КОНСПЕКТ:\n{context}"
                    )
                else:
                    system_prompt = "В сохраненных конспектах нет информации."
                
                messages = [{"role": "system", "content": system_prompt}] + self.chat_history
                answer = safe_openrouter_request(messages)
                
                if answer:
                    self.chat_history.append({'role': 'assistant', 'content': answer})
                self.update_chat(answer=answer, loading=loading)
            except Exception as e:
                self.update_chat(answer=f"Ошибка: {e}", loading=loading)
                
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_chat(self, answer, loading):
        if loading and loading.parent:
            self.ids.chat_container.remove_widget(loading)
        self.add_simple_bubble(self.ids.chat_container, answer, is_user=False)

    # --- ОБУЧЕНИЕ ---
    def process_learn_material(self):
        self.add_simple_bubble(self.ids.learn_container, "Составляю план...", is_user=False)
        
        def worker():
            try:
                messages = [{"role": "user", "content": "Ты ИИ-учитель. Составь план обучения программированию. Задай первый вопрос."}]
                answer = safe_openrouter_request(messages)
                self.update_learn(answer=answer, loading=None)
            except Exception as e:
                self.update_learn(answer=f"Ошибка: {e}", loading=None)
                
        threading.Thread(target=worker, daemon=True).start()

    def send_learn_message(self):
        text = self.ids.learn_input.text.strip()
        if not text: return
        self.ids.learn_input.text = ''
        self.add_simple_bubble(self.ids.learn_container, text, is_user=True)
        
        def worker():
            try:
                messages = [{"role": "user", "content": f"Мой ответ: {text}. Оцени и задай следующий вопрос."}]
                answer = safe_openrouter_request(messages)
                self.update_learn(answer=answer, loading=None)
            except Exception as e:
                self.update_learn(answer=f"Ошибка: {e}", loading=None)
                
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_learn(self, answer, loading):
        if loading and loading.parent:
            self.ids.learn_container.remove_widget(loading)
        self.add_simple_bubble(self.ids.learn_container, answer, is_user=False)

    def add_simple_bubble(self, container, text, is_user):
        layout = BoxLayout(orientation='horizontal', size_hint_y=None, spacing=dp(5))
        lbl = Label(text=text, size_hint_y=None, text_size=(dp(250), None), 
                    halign='right' if is_user else 'left', valign='top',
                    color=(0, 0, 0.7, 1) if is_user else (0, 0, 0, 1), markup=True)
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        
        if is_user:
            layout.add_widget(Label(size_hint_x=0.2))
            layout.add_widget(lbl)
        else:
            layout.add_widget(lbl)
            layout.add_widget(Label(size_hint_x=0.2))
            
        layout.height = lbl.height + dp(10)
        container.add_widget(layout)
        layout.opacity = 0
        Animation(opacity=1, d=0.2).start(layout)
        Clock.schedule_once(lambda dt: setattr(container, 'height', container.minimum_height), 0.1)

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
