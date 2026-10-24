# -*- coding: utf-8 -*-
import os
import json
import threading
import base64
import ssl
import urllib.request
import shutil
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
Window.softinput_mode = 'below_target'

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

OCR_API_KEY = "K86772432188957"

def get_key():
    p1 = "sk-or-v1-71d88394a7c915b6"
    p2 = "382385eb96fde7e8e5892b42bb5e08f41f6432ea72e57196"
    return p1 + p2

OPENROUTER_API_KEY = get_key()
MODEL_NAME = "openrouter/free"

NOTES_FOLDER = ""
COURSES_FOLDER = ""
CACHE_FILE = ""

def init_storage():
    global NOTES_FOLDER, COURSES_FOLDER, CACHE_FILE
    try:
        base = App.get_running_app().user_data_dir
        NOTES_FOLDER = os.path.join(base, "notes")
        COURSES_FOLDER = os.path.join(base, "courses")
        os.makedirs(NOTES_FOLDER, exist_ok=True)
        os.makedirs(COURSES_FOLDER, exist_ok=True)
        CACHE_FILE = os.path.join(base, "chat_cache.json")
        
        # Копируем файлы из GitHub (если они есть) при первом запуске
        copy_github_files()
    except: 
        NOTES_FOLDER = "."
        COURSES_FOLDER = "."
        CACHE_FILE = "chat_cache.json"

def copy_github_files():
    # Если в папке проекта есть папки default_notes или default_courses, копируем их
    try:
        if os.path.exists("default_notes"):
            for f in os.listdir("default_notes"):
                shutil.copy(os.path.join("default_notes", f), NOTES_FOLDER)
        if os.path.exists("default_courses"):
            for f in os.listdir("default_courses"):
                shutil.copy(os.path.join("default_courses", f), COURSES_FOLDER)
    except: pass

# ============================================================
# РАБОТА С ФАЙЛАМИ
# ============================================================
def load_cache():
    if not os.path.exists(CACHE_FILE): return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_to_cache(question, answer):
    cache = load_cache()
    cache[question.strip().lower()] = answer
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f: json.dump(cache, f, ensure_ascii=False)
    except: pass

def get_from_cache(question):
    return load_cache().get(question.strip().lower(), None)

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
        if score > 0: scored_notes.append((score, note))
    scored_notes.sort(key=lambda x: -x[0])
    top_notes = [n[1] for n in scored_notes[:3]]
    if not top_notes: return ""
    return "\n\n---\n\n".join([f"Конспект: {n.get('title', '')}\n{n.get('text', '')}" for n in top_notes])[:4000]

# ============================================================
# ЗАПРОС К OPENROUTER
# ============================================================
def safe_openrouter_request(messages):
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENROUTER_API_KEY}"}
        payload = {"model": MODEL_NAME, "messages": messages, "temperature": 0.5, "max_tokens": 1500}
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, context=ssl_context, timeout=60) as response:
            return json.loads(response.read().decode('utf-8'))["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e: return f"Ошибка API ({e.code})"
    except Exception as e: return f"Ошибка: {str(e)}"

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
                            spacing: dp(10)
                            
                    BoxLayout:
                        size_hint_y: None
                        height: dp(55)
                        spacing: dp(8)
                        
                        TextInput:
                            id: chat_input
                            hint_text: 'Вопрос по конспектам...'
                            multiline: False
                            input_type: 'text'
                            padding: dp(15), dp(15)
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
                        input_type: 'text'
                        
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
                        input_type: 'text'
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
                    
                    TextInput:
                        id: learn_text_input
                        hint_text: 'Вставьте конспект для обучения...'
                        multiline: True
                        input_type: 'text'
                        size_hint_y: 0.3
                        
                    BoxLayout:
                        size_hint_y: None
                        height: dp(55)
                        spacing: dp(10)
                        
                        Button:
                            text: 'Составить план'
                            background_normal: ''
                            background_color: 0.2, 0.6, 0.4, 1
                            on_release: root.start_learning()
                            
                        Button:
                            text: 'Загрузить старый'
                            background_normal: ''
                            background_color: 0.8, 0.5, 0.2, 1
                            on_release: root.load_saved_course()
                        
                    ScrollView:
                        id: lessons_scroll
                        BoxLayout:
                            id: lessons_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(8)
                            
                    Button:
                        text: 'Задать вопрос по уроку'
                        size_hint_y: None
                        height: dp(40)
                        background_normal: ''
                        background_color: 0.55, 0.3, 0.8, 1
                        on_release: root.ask_extra_question()
                            
                    ScrollView:
                        id: learn_scroll
                        BoxLayout:
                            id: learn_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(10)
                            
                    BoxLayout:
                        size_hint_y: None
                        height: dp(55)
                        spacing: dp(8)
                        
                        TextInput:
                            id: learn_input
                            hint_text: 'Ваш ответ или вопрос...'
                            multiline: False
                            input_type: 'text'
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
        self.learn_history = []
        self.learning_context = ""
        self.course_cache = {} # Кэш уроков (в оперативной памяти)
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
            if not os.path.exists(path): raise Exception("Файл не найден.")
            with open(path, "rb") as f: encoded = base64.b64encode(f.read()).decode('utf-8')
            url = "https://api.ocr.space/parse/image"
            payload = f"apikey={OCR_API_KEY}&language=rus&base64Image=data:image/jpeg;base64,{encoded}"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            req = urllib.request.Request(url, data=payload.encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
            text = result.get('ParsedResults', [{}])[0].get('ParsedText', '')
            self.update_photo_result(text, 'Готово! Сохранено.')
            save_note(text)
        except Exception as e: self.update_photo_result(f'Ошибка: {e}', 'Ошибка')

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
        self.add_bubble(self.ids.chat_container, text, is_user=True)
        self.chat_history.append({'role': 'user', 'content': text})
        loading = Label(text='...', size_hint_y=None, height=dp(30), color=(0.5, 0.5, 0.5, 1))
        self.ids.chat_container.add_widget(loading)
        
        def worker():
            try:
                cached = get_from_cache(text)
                if cached:
                    self.update_chat(f"📁 [Из памяти]\n\n{cached}", loading)
                    return
                if not check_internet():
                    self.update_chat("Нет интернета. Подключите сеть или найдите ответ в конспектах (вкладка Загрузка).", loading)
                    return
                context = find_relevant_notes(text)
                sys_p = "Отвечай на русском. Используй ТОЛЬКО текст из конспекта:\n" + context if context else "Нет конспектов."
                ans = safe_openrouter_request([{"role": "system", "content": sys_p}] + self.chat_history)
                if ans and not ans.startswith("Ошибка"):
                    save_to_cache(text, ans)
                    self.chat_history.append({'role': 'assistant', 'content': ans})
                self.update_chat(ans, loading)
            except Exception as e: self.update_chat(f"Ошибка: {e}", loading)
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_chat(self, answer, loading):
        if loading and loading.parent: self.ids.chat_container.remove_widget(loading)
        self.add_bubble(self.ids.chat_container, answer, is_user=False)

    # --- ОБУЧЕНИЕ ---
    def start_learning(self):
        text = self.ids.learn_text_input.text.strip()
        if not text:
            self.add_bubble(self.ids.learn_container, "Вставьте текст.", is_user=False)
            return
        self.learning_context = text
        self.ids.learn_container.clear_widgets()
        self.ids.lessons_container.clear_widgets()
        self.add_bubble(self.ids.learn_container, "Составляю план уроков...", is_user=False)
        
        def worker():
            try:
                # ЖЕСТКИЙ ПРОМПТ ДЛЯ ИЗБЕЖАНИЯ ТАБЛИЦ
                prompt = (
                    "Ты ИИ-учитель. Разбей текст на 3-4 урока. "
                    "ВАЖНО: Пиши ТОЛЬКО названия уроков цифрами. Никаких таблиц и символов. "
                    f"Текст:\n{self.learning_context[:2500]}"
                )
                ans = safe_openrouter_request([{"role": "user", "content": prompt}])
                self.show_lessons(ans, self.learning_context)
            except Exception as e: self.update_learn(f"Ошибка: {e}", None)
        threading.Thread(target=worker, daemon=True).start()

    def load_saved_course(self):
        try:
            files = [f for f in os.listdir(COURSES_FOLDER) if f.endswith('.json')]
            if not files: raise Exception("Нет сохраненных курсов")
            with open(os.path.join(COURSES_FOLDER, files[0]), 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.learning_context = data['context']
            self.ids.learn_container.clear_widgets()
            self.ids.lessons_container.clear_widgets()
            self.add_bubble(self.ids.learn_container, "Загружен сохраненный курс.", is_user=False)
            self.show_lessons(data['plan'], data['context'])
        except Exception as e:
            self.add_bubble(self.ids.learn_container, f"Ошибка загрузки: {e}", is_user=False)

    @mainthread
    def show_lessons(self, raw_plan, context):
        self.ids.learn_container.clear_widgets()
        self.add_bubble(self.ids.learn_container, "План готов. Выбери урок:", is_user=False)
        
        # Сохраняем курс в файл
        try:
            course_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(os.path.join(COURSES_FOLDER, f"course_{course_id}.json"), 'w', encoding='utf-8') as f:
                json.dump({"plan": raw_plan, "context": context}, f, ensure_ascii=False)
        except: pass

        lines = [line.strip() for line in raw_plan.split('\n') if line.strip()]
        for line in lines:
            if line[0].isdigit() or line.startswith('-'):
                btn = Button(text=line, size_hint_y=None, height=dp(50), background_normal='', background_color=(0.15, 0.45, 0.85, 1))
                btn.bind(on_release=lambda b, l=line: self.start_lesson(l))
                self.ids.lessons_container.add_widget(btn)

    def start_lesson(self, lesson_title):
        self.ids.learn_container.clear_widgets()
        self.add_bubble(self.ids.learn_container, f"Урок: {lesson_title}", is_user=False)
        
        # ПРОВЕРКА КЭША УРОКОВ (Чтобы не пропадал при переключении)
        if lesson_title in self.course_cache:
            self.add_bubble(self.ids.learn_container, self.course_cache[lesson_title], is_user=False)
            self.learn_history = [{'role': 'assistant', 'content': self.course_cache[lesson_title]}]
            return

        if not check_internet():
            self.add_bubble(self.ids.learn_container, "Нет интернета для генерации урока. Читайте конспект.", is_user=False)
            return

        def worker():
            try:
                # ЖЕСТКИЙ ПРОМПТ ДЛЯ ИСКЛЮЧЕНИЯ ТАБЛИЦ И СИМВОЛОВ
                prompt = (
                    f"Ты ИИ-учитель. Объясни тему '{lesson_title}' простым текстом. "
                    "ЗАПРЕЩЕНО использовать markdown-таблицы, звездочки, решетки и сложные математические символы (пиши словами: 'в степени', 'корень из'). "
                    f"Текст конспекта:\n{self.learning_context[:2500]}\n"
                    "В конце задай 1 вопрос ученику."
                )
                ans = safe_openrouter_request([{"role": "user", "content": prompt}])
                if ans and not ans.startswith("Ошибка"):
                    self.course_cache[lesson_title] = ans # Сохраняем в оперативку
                    self.learn_history = [{'role': 'assistant', 'content': ans}]
                self.update_learn(ans, None)
            except Exception as e: self.update_learn(f"Ошибка: {e}", None)
        threading.Thread(target=worker, daemon=True).start()

    def ask_extra_question(self):
        self.ids.learn_input.focus = True

    def send_learn_message(self):
        text = self.ids.learn_input.text.strip()
        if not text: return
        self.ids.learn_input.text = ''
        self.add_bubble(self.ids.learn_container, text, is_user=True)
        self.learn_history.append({'role': 'user', 'content': text})
        loading = Label(text='Думаю...', size_hint_y=None, height=dp(30), color=(0.5, 0.5, 0.5, 1))
        self.ids.learn_container.add_widget(loading)
        
        def worker():
            try:
                if not check_internet():
                    self.update_learn("Нет интернета.", loading)
                    return
                ans = safe_openrouter_request(self.learn_history)
                self.learn_history.append({'role': 'assistant', 'content': ans})
                self.update_learn(ans, loading)
            except Exception as e: self.update_learn(f"Ошибка: {e}", loading)
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_learn(self, answer, loading):
        if loading and loading.parent: self.ids.learn_container.remove_widget(loading)
        self.add_bubble(self.ids.learn_container, answer, is_user=False)

    # --- ДИЗАЙН ПУЗЫРЕЙ ---
    def add_bubble(self, container, text, is_user):
        layout = BoxLayout(orientation='horizontal', size_hint_y=None, spacing=dp(5))
        
        # Красивый фон (светло-синий для юзера, белый для бота)
        bg_color = (0.85, 0.92, 1, 1) if is_user else (1, 1, 1, 1)
        
        lbl = Label(
            text=text, size_hint_y=None, text_size=(dp(280), None), 
            halign='right' if is_user else 'left', valign='top',
            color=(0, 0, 0, 1), markup=False # ОТКЛЮЧАЕМ MARKUP, ЧТОБЫ НЕ БЫЛО КРАКОЗЯБР
        )
        
        # Красивый фон пузыря (без радиусов, чтобы не вылетало, просто цветная плашка)
        with lbl.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*bg_color)
            rect = Rectangle(pos=lbl.pos, size=lbl.size)
        lbl.bind(pos=lambda *x: setattr(rect, 'pos', lbl.pos))
        lbl.bind(size=lambda *x: setattr(rect, 'size', lbl.size))
        
        # Отступы внутри пузыря
        lbl.padding = (dp(10), dp(10))
        
        def update_height(instance, texture_size):
            instance.height = texture_size[1] + dp(20) # +20 на отступы
            layout.height = instance.height
            container.height = container.minimum_height
        lbl.bind(texture_size=update_height)
        
        if is_user:
            layout.add_widget(Label(size_hint_x=0.1))
            layout.add_widget(lbl)
        else:
            layout.add_widget(lbl)
            layout.add_widget(Label(size_hint_x=0.1))
            
        container.add_widget(layout)
        layout.opacity = 0
        Animation(opacity=1, d=0.2).start(layout)
        Clock.schedule_once(lambda dt: setattr(container, 'height', container.minimum_height), 0.1)

def save_note(text):
    try:
        note_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(os.path.join(NOTES_FOLDER, f"{note_id}.json"), 'w', encoding='utf-8') as f: 
            json.dump({"id": note_id, "title": text[:20], "text": text}, f, ensure_ascii=False)
    except: pass

class NotesApp(App):
    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    NotesApp().run()
