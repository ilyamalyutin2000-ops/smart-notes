# -*- coding: utf-8 -*-
import os
import json
import threading
import base64
import urllib.request
import urllib.parse
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
from kivy.graphics import Color, RoundedRectangle
from kivy.animation import Animation

# ============================================================
# НАСТРОЙКИ
# ============================================================
OCR_API_KEY = "K86772432188957"
OPENROUTER_API_KEY = "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"

# ============================================================
# БЕЗОПАСНЫЕ ПУТИ
# ============================================================
NOTES_FOLDER = ""
def init_storage():
    global NOTES_FOLDER
    try:
        base = App.get_running_app().user_data_dir
        NOTES_FOLDER = os.path.join(base, "notes")
        os.makedirs(NOTES_FOLDER, exist_ok=True)
    except:
        NOTES_FOLDER = "."

# ============================================================
# КАСТОМНЫЕ КНОПКИ
# ============================================================
class TabButton(Button):
    def __init__(self, bg_color_normal=(0.4, 0.4, 0.45, 1), bg_color_active=(0.15, 0.45, 0.85, 1), **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.bg_color_normal = bg_color_normal
        self.bg_color_active = bg_color_active
        self.current_color = bg_color_normal
        self.color_normal = (0.9, 0.9, 0.9, 1)
        self.color_active = (1, 1, 1, 1)
        self.color = self.color_normal
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.current_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])

    def set_active(self, is_active):
        target_bg = self.bg_color_active if is_active else self.bg_color_normal
        target_text = self.color_active if is_active else self.color_normal
        Animation(current_color=target_bg, color=target_text, d=0.2, t='out_quad').start(self)

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
            text: 'Умный конспект'
            font_size: '22sp'
            bold: True
            color: 0.1, 0.15, 0.2, 1

        BoxLayout:
            size_hint_y: None
            height: dp(45)
            spacing: dp(5)
            TabButton:
                id: btn_tab_new
                text: 'Загрузка'
                on_release: root.switch_tab('new')
            TabButton:
                id: btn_tab_history
                text: 'История'
                on_release: root.switch_tab('history')
            TabButton:
                id: btn_tab_learn
                text: 'Обучение'
                on_release: root.switch_tab('learn')
            TabButton:
                id: btn_tab_chat
                text: 'Чат'
                on_release: root.switch_tab('chat')

        ScreenManager:
            id: content_manager
            transition: SlideTransition(direction='left', duration=0.3)
            
            Screen:
                name: 'new'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    TabButton:
                        text: 'Загрузить фото/файл'
                        size_hint_y: None
                        height: dp(60)
                        bg_color_normal: (0.55, 0.3, 0.8, 1)
                        bg_color_active: (0.55, 0.3, 0.8, 1)
                        on_release: root.open_file_chooser('photo')
                    Label:
                        id: photo_status
                        text: 'Текст сохранится автоматически'
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
                    TabButton:
                        text: 'Копировать'
                        size_hint_y: None
                        height: dp(50)
                        bg_color_normal: (0.2, 0.6, 0.4, 1)
                        bg_color_active: (0.2, 0.6, 0.4, 1)
                        on_release: root.copy_photo_text()

            Screen:
                name: 'history'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    TextInput:
                        id: search_input
                        hint_text: 'Поиск...'
                        size_hint_y: None
                        height: dp(45)
                        multiline: False
                        background_color: 1, 1, 1, 1
                        foreground_color: 0.1, 0.15, 0.2, 1
                        on_text: root.filter_history(self.text)
                    ScrollView:
                        BoxLayout:
                            id: history_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(8)

            Screen:
                name: 'learn'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    TabButton:
                        text: 'Загрузить материал для обучения'
                        size_hint_y: None
                        height: dp(55)
                        bg_color_normal: (0.2, 0.6, 0.4, 1)
                        bg_color_active: (0.2, 0.6, 0.4, 1)
                        on_release: root.open_file_chooser('learn')
                    Label:
                        id: learn_status
                        text: 'Загрузите конспект'
                        size_hint_y: None
                        height: dp(30)
                        color: 0.4, 0.4, 0.45, 1
                    ScrollView:
                        id: learn_scroll
                        BoxLayout:
                            id: learn_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(12)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(55)
                        spacing: dp(8)
                        TextInput:
                            id: learn_input
                            hint_text: 'Ваш ответ...'
                            multiline: False
                            background_color: 1, 1, 1, 1
                            foreground_color: 0.1, 0.15, 0.2, 1
                            on_text_validate: root.send_learn_message()
                        TabButton:
                            text: 'Ответ'
                            size_hint_x: None
                            width: dp(90)
                            bg_color_normal: (0.15, 0.45, 0.85, 1)
                            bg_color_active: (0.15, 0.45, 0.85, 1)
                            on_release: root.send_learn_message()

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
                        TabButton:
                            text: 'Ввод'
                            size_hint_x: None
                            width: dp(90)
                            bg_color_normal: (0.15, 0.45, 0.85, 1)
                            bg_color_active: (0.15, 0.45, 0.85, 1)
                            on_release: root.send_chat_message()
"""

# ============================================================
# ЛОГИКА
# ============================================================
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_photo_text = ""
        self.chat_history = []
        self.learn_history = []
        self.learn_context = ""
        self.all_notes = []
        self.file_picker_target = 'photo'
        Clock.schedule_once(self.setup_app, 0.5)

    def setup_app(self, dt):
        init_storage()
        self.switch_tab('new')

    def switch_tab(self, name):
        self.ids.content_manager.current = name
        self.ids.btn_tab_new.set_active(name == 'new')
        self.ids.btn_tab_history.set_active(name == 'history')
        self.ids.btn_tab_learn.set_active(name == 'learn')
        self.ids.btn_tab_chat.set_active(name == 'chat')
        if name == 'history': self.load_history()

    def open_file_chooser(self, target='photo'):
        self.file_picker_target = target
        content = BoxLayout(orientation='vertical')
        start_path = "/storage/emulated/0/Download"
        if not os.path.exists(start_path):
            start_path = os.path.expanduser("~")
            
        try:
            filechooser = FileChooserListView(path=start_path, filters=['*.png', '*.jpg', '*.jpeg', '*.txt'])
        except:
            filechooser = FileChooserListView(path=".")
            
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
                path = filechooser.selection[0]
                if self.file_picker_target == 'learn':
                    self.process_learn_material(path)
                else:
                    self.process_photo(path)
                    
        btn_cancel.bind(on_release=cancel)
        btn_open.bind(on_release=open_file)
        popup.open()

    def process_photo(self, path):
        self.ids.photo_status.text = 'Обработка (может занять время)...'
        self.ids.photo_output.text = 'Подождите...'
        def worker():
            try:
                raw = recognize_photo(path)
                ready = clean_text(raw)
                save_note(ready)
                self.update_photo_result(ready, 'Готово! Сохранено.')
            except Exception as e:
                self.update_photo_result(f'Ошибка: {e}', 'Ошибка сети/файла')
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_photo_result(self, text, status):
        self.current_photo_text = text
        self.ids.photo_output.text = text
        self.ids.photo_status.text = status

    def copy_photo_text(self):
        if self.current_photo_text:
            try:
                from kivy.core.clipboard import Clipboard
                Clipboard.copy(self.current_photo_text)
                self.ids.photo_status.text = 'Скопировано!'
            except: pass

    def load_history(self):
        self.all_notes = get_all_notes()
        self.render_history(self.all_notes)

    def filter_history(self, query):
        if not query:
            self.render_history(self.all_notes)
            return
        filtered = [n for n in self.all_notes if query.lower() in n.get('text', '').lower() or query.lower() in n.get('title', '').lower()]
        self.render_history(filtered)

    def render_history(self, notes):
        container = self.ids.history_container
        container.clear_widgets()
        if not notes:
            container.add_widget(Label(text='Ничего не найдено', color=(0.6,0.6,0.6,1)))
            return
        for note in notes:
            title = note.get('title', 'Без названия')
            date = note.get('date', '')
            btn = TabButton(text=f"{title}\n{date}", size_hint_y=None, height=dp(70), bg_color_normal=(1, 1, 1, 1), bg_color_active=(0.9, 0.9, 0.9, 1), color=(0.1, 0.1, 0.1, 1))
            btn.bind(on_release=lambda b, n=note: self.open_note(n))
            container.add_widget(btn)

    def open_note(self, note):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        text_input = TextInput(text=note.get('text', ''), multiline=True, background_color=(1,1,1,1), foreground_color=(0.1,0.1,0.1,1))
        content.add_widget(text_input)
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
        btn_save = Button(text='Обновить', background_color=(0.2, 0.6, 0.4, 1))
        btn_delete = Button(text='Удалить', background_color=(0.85, 0.25, 0.25, 1))
        btn_box.add_widget(btn_save)
        btn_box.add_widget(btn_delete)
        content.add_widget(btn_box)
        popup = Popup(title=note.get('title', ''), content=content, size_hint=(0.95, 0.9))
        
        def save_edit(*_):
            update_note(note.get('id'), text_input.text)
            popup.dismiss()
            self.load_history()
        def delete_note_action(*_):
            delete_note(note.get('id'))
            popup.dismiss()
            self.load_history()
            
        btn_save.bind(on_release=save_edit)
        btn_delete.bind(on_release=delete_note_action)
        popup.open()

    # ========================================================
    # ОБУЧЕНИЕ
    # ========================================================
    def process_learn_material(self, path):
        self.ids.learn_status.text = 'Чтение файла...'
        def worker():
            try:
                raw = recognize_photo(path)
                self.learn_context = clean_text(raw)
                self.learn_history = []
                self.ids.learn_container.clear_widgets()
                self.add_learn_bubble("Материал загружен! Составляю план...", is_user=False)
                prompt = f"Вот мой конспект:\n{self.learn_context}\n\nСоставь краткий пошаговый план обучения по этой теме и задай мне первый вопрос (задание)."
                answer = call_openrouter([{"role": "user", "content": prompt}])
                self.learn_history.append({'role': 'assistant', 'content': answer})
                self.update_learn_answer(answer)
            except Exception as e:
                self.ids.learn_status.text = f'Ошибка: {e}'
        threading.Thread(target=worker, daemon=True).start()

    def send_learn_message(self):
        text = self.ids.learn_input.text.strip()
        if not text: return
        self.ids.learn_input.text = ''
        self.add_learn_bubble(text, is_user=True)
        self.learn_history.append({'role': 'user', 'content': text})
        loading = Label(text='Учитель думает...', size_hint_y=None, height=dp(40), color=(0.5, 0.5, 0.5, 1), italic=True)
        self.ids.learn_container.add_widget(loading)
        def worker():
            try:
                prompt = f"Мой ответ: {text}\nОцени ответ и задай следующий вопрос."
                messages = [{"role": "system", "content": "Ты ИИ-учитель."}] + self.learn_history + [{"role": "user", "content": prompt}]
                answer = call_openrouter(messages)
                self.learn_history.append({'role': 'assistant', 'content': answer})
                self.update_learn_answer(answer, loading)
            except Exception as e:
                self.update_learn_answer(f"Ошибка сети: {e}", loading)
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_learn_answer(self, answer, loading_label=None):
        if loading_label and loading_label.parent:
            self.ids.learn_container.remove_widget(loading_label)
        self.add_learn_bubble(answer, is_user=False)

    def add_learn_bubble(self, text, is_user):
        msg_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        bg = (0.95, 0.95, 0.95, 1) if is_user else (0.9, 0.95, 1, 1)
        lbl = Label(text=text, size_hint_y=None, text_size=(dp(320), None), halign='right' if is_user else 'left', valign='top', color=(0,0,0,1) if is_user else (0.1,0.1,0.1,1), markup=True)
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        with lbl.canvas.before:
            Color(*bg)
            rect = RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[dp(12)])
        lbl.bind(pos=lambda *x: setattr(rect, 'pos', lbl.pos))
        lbl.bind(size=lambda *x: setattr(rect, 'size', lbl.size))
        msg_box.add_widget(lbl)
        msg_box.height = lbl.height + dp(10)
        self.ids.learn_container.add_widget(msg_box)
        Clock.schedule_once(lambda dt: setattr(self.ids.learn_scroll, 'scroll_y', 0), 0.1)

    # ========================================================
    # ЧАТ
    # ========================================================
    def send_chat_message(self):
        text = self.ids.chat_input.text.strip()
        if not text: return
        self.ids.chat_input.text = ''
        self.add_chat_bubble(text, is_user=True)
        self.chat_history.append({'role': 'user', 'content': text})
        loading = Label(text='Думаю...', size_hint_y=None, height=dp(40), color=(0.5, 0.5, 0.5, 1), italic=True)
        self.ids.chat_container.add_widget(loading)
        def worker():
            try:
                answer = answer_question(self.chat_history)
                self.chat_history.append({'role': 'assistant', 'content': answer})
                self.update_chat_answer(answer, loading)
            except Exception as e:
                self.update_chat_answer(f"Ошибка сети: {e}", loading)
        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def update_chat_answer(self, answer, loading_label):
        if loading_label and loading_label.parent:
            self.ids.chat_container.remove_widget(loading_label)
        self.add_chat_bubble(answer, is_user=False)

    def add_chat_bubble(self, text, is_user):
        msg_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        bg = (0.95, 0.95, 0.95, 1) if is_user else (0.9, 0.95, 1, 1)
        lbl = Label(text=text, size_hint_y=None, text_size=(dp(320), None), halign='right' if is_user else 'left', valign='top', color=(0,0,0,1) if is_user else (0.1,0.1,0.1,1), italic=is_user, markup=True)
        lbl.bind(texture_size=lambda *x: setattr(lbl, 'height', lbl.texture_size[1]))
        with lbl.canvas.before:
            Color(*bg)
            rect = RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[dp(12)])
        lbl.bind(pos=lambda *x: setattr(rect, 'pos', lbl.pos))
        lbl.bind(size=lambda *x: setattr(rect, 'size', lbl.size))
        msg_box.add_widget(lbl)
        if not is_user:
            copy_btn = TabButton(text='📋 Копировать', size_hint_y=None, height=dp(30), bg_color_normal=(0.8, 0.85, 0.9, 1), bg_color_active=(0.7, 0.75, 0.8, 1), color=(0.2, 0.2, 0.2, 1), font_size='12sp')
            copy_btn.bind(on_release=lambda b: self.copy_text_to_clipboard(text))
            msg_box.add_widget(copy_btn)
        msg_box.height = lbl.height + (dp(35) if not is_user else dp(5))
        self.ids.chat_container.add_widget(msg_box)
        Clock.schedule_once(lambda dt: setattr(self.ids.chat_scroll, 'scroll_y', 0), 0.1)

    def copy_text_to_clipboard(self, text):
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(text)
        except: pass

# ============================================================
# API С ИСПОЛЬЗОВАНИЕМ URLLIB И OPENROUTER
# ============================================================
def clean_text(raw_text):
    if not raw_text: return ""
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {OPENROUTER_API_KEY}"
        }
        payload = {
            "model": "meta-llama/llama-3-8b-instruct",
            "messages": [{"role": "system", "content": "Убери символы разметки. Только чистый текст."}, {"role": "user", "content": raw_text}]
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Ошибка нейросети при чистке: {e}")
    return raw_text.replace('*', '').replace('#', '').strip()

def recognize_photo(filepath):
    if not os.path.exists(filepath):
        raise Exception("Файл не найден.")
    try:
        url = "https://api.ocr.space/parse/image"
        with open(filepath, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode('utf-8')
            
        payload = {
            'apikey': OCR_API_KEY, 
            'language': 'rus', 
            'scale': 'true',
            'base64Image': f"data:image/jpeg;base64,{encoded_image}"
        }
        data = urllib.parse.urlencode(payload).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        if result.get('IsErroredOnProcessing'): 
            raise Exception(result.get('ErrorMessage'))
        return result.get('ParsedResults', [{}])[0].get('ParsedText', '')
    except Exception as e:
        raise Exception(f"Ошибка OCR: {e}")

def save_note(text):
    try:
        note_id = datetime.now().strftime("%Y%m%d_%H%M%S%f")
        title = text.strip().split('\n')[0][:40]
        data = {"id": note_id, "title": title, "date": datetime.now().strftime("%d.%m.%Y"), "text": text}
        with open(os.path.join(NOTES_FOLDER, f"{note_id}.json"), 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка записи: {e}")

def update_note(note_id, new_text):
    try:
        path = os.path.join(NOTES_FOLDER, f"{note_id}.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
            data['text'] = new_text
            data['title'] = new_text.strip().split('\n')[0][:40]
            with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False)
    except: pass

def delete_note(note_id):
    try:
        path = os.path.join(NOTES_FOLDER, f"{note_id}.json")
        if os.path.exists(path): os.remove(path)
    except: pass

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
    try:
        notes = get_all_notes()
        if not notes: return ""
        words = [w.lower() for w in question.split() if len(w) > 3]
        scored = [(sum(n.get("text", "").lower().count(w) for w in words), n) for n in notes]
        scored = [s for s in scored if s[0] > 0]
        scored.sort(key=lambda x: -x[0])
        return "\n\n".join(n.get("text", "") for _, n in scored[:3])[:6000]
    except: return ""

def call_openrouter(messages):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
    }
    payload = {
        "model": "meta-llama/llama-3-8b-instruct", 
        "messages": messages, 
        "temperature": 0.5
    }
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e: 
        return f"Ошибка сети: {str(e)}"

def answer_question(messages):
    last_q = messages[-1]["content"]
    context = find_relevant_notes(last_q)
    if not context: 
        return "В конспектах нет информации."
    system_prompt = (
        "Ты ассистент. Отвечай на вопрос, используя ТОЛЬКО текст из конспекта ниже.\n"
        "Если нет, напиши 'В конспекте этой информации нет.', а затем 'Дополнительная информация:'.\n"
        f"КОНСПЕКТ:\n{context}"
    )
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    return call_openrouter(full_messages)

# ============================================================
# ЗАПУСК
# ============================================================
class NotesApp(App):
    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    NotesApp().run()
