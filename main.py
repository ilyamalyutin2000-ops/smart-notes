# -*- coding: utf-8 -*-
"""SmartNotes: Kivy application for saving notes and asking questions about them."""

import os
import json
import ssl
import base64
import threading
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from uuid import uuid4

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.animation import Animation
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
Window.clearcolor = get_color_from_hex("#F3F6FA")

# Не публикуй действующие API-ключи в открытом репозитории.
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
OCR_API_KEY = os.environ.get("OCR_API_KEY", "").strip()
OPENROUTER_MODEL = os.environ.get(
    "OPENROUTER_MODEL", "meta-llama/llama-3-8b-instruct"
)

NOTES_FOLDER = ""
APP_DATA_FOLDER = ""
CHAT_FILE = ""
API_CONFIG_FILE = ""

STORAGE_LOCK = threading.RLock()
CHAT_LOCK = threading.RLock()

REQUEST_TIMEOUT = 25
MAX_CHAT_MESSAGES = 30
MAX_NOTE_CONTEXT_CHARS = 24000
MAX_MESSAGE_CHARS = 12000


def init_storage():
    """Создание приватной папки данных приложения."""
    global NOTES_FOLDER, APP_DATA_FOLDER, CHAT_FILE, API_CONFIG_FILE

    app = App.get_running_app()
    base = app.user_data_dir if app else os.path.abspath(".")

    APP_DATA_FOLDER = os.path.join(base, "smartnotes")
    NOTES_FOLDER = os.path.join(APP_DATA_FOLDER, "notes")
    CHAT_FILE = os.path.join(APP_DATA_FOLDER, "chat_history.json")
    API_CONFIG_FILE = os.path.join(APP_DATA_FOLDER, "api_config.json")

    os.makedirs(NOTES_FOLDER, exist_ok=True)
    load_api_config()


def load_api_config():
    """Загрузка API-ключей из приватной папки приложения."""
    global OPENROUTER_API_KEY, OCR_API_KEY

    if not API_CONFIG_FILE or not os.path.isfile(API_CONFIG_FILE):
        return

    try:
        with open(API_CONFIG_FILE, "r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)

        if isinstance(data, dict):
            OPENROUTER_API_KEY = str(
                data.get("openrouter", OPENROUTER_API_KEY) or ""
            ).strip()
            OCR_API_KEY = str(
                data.get("ocr", OCR_API_KEY) or ""
            ).strip()

    except (OSError, ValueError, TypeError):
        pass


def ensure_storage():
    if not NOTES_FOLDER or not APP_DATA_FOLDER:
        init_storage()


def safe_url_request(url, payload=None, headers=None, timeout=REQUEST_TIMEOUT):
    """HTTPS-запрос с проверкой SSL-сертификата."""
    data = None
    request_headers = dict(headers or {})

    if payload is not None:
        data = payload if isinstance(payload, bytes) else payload.encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers=request_headers,
        method="POST" if data is not None else "GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=ssl.create_default_context(),
        ) as response:
            return response.read().decode("utf-8", errors="replace")

    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = ""

        return "API_ERROR:{}:{}".format(exc.code, detail[:700])

    except urllib.error.URLError as exc:
        return "NETWORK_ERROR:{}".format(getattr(exc, "reason", exc))

    except Exception as exc:
        return "REQUEST_ERROR:{}".format(exc)


def write_json_atomic(path, data):
    """Сохранение JSON через временный файл для защиты от повреждения."""
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    temp_path = path + ".tmp"

    with open(temp_path, "w", encoding="utf-8") as file_obj:
        json.dump(data, file_obj, ensure_ascii=False, indent=2)
        file_obj.flush()
        os.fsync(file_obj.fileno())

    os.replace(temp_path, path)


def save_note(text, title=None):
    text = (text or "").strip()

    if not text:
        raise ValueError("Нельзя сохранить пустой конспект.")

    ensure_storage()

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    note_id = "{}_{}".format(
        datetime.now().strftime("%Y%m%d_%H%M%S"),
        uuid4().hex[:8],
    )

    clean_title = (
        title or " ".join(text.split())[:48] or "Без названия"
    ).strip()

    note = {
        "id": note_id,
        "title": clean_title,
        "text": text,
        "created_at": now,
    }

    path = os.path.join(NOTES_FOLDER, note_id + ".json")

    with STORAGE_LOCK:
        write_json_atomic(path, note)

    return note


def get_all_notes():
    ensure_storage()
    notes = []

    with STORAGE_LOCK:
        try:
            names = sorted(os.listdir(NOTES_FOLDER), reverse=True)
        except OSError:
            return []

        for filename in names:
            if not filename.endswith(".json"):
                continue

            path = os.path.join(NOTES_FOLDER, filename)

            try:
                with open(path, "r", encoding="utf-8") as file_obj:
                    note = json.load(file_obj)

                if isinstance(note, dict) and isinstance(note.get("text"), str):
                    note.setdefault("id", filename[:-5])
                    note.setdefault("title", "Без названия")
                    note.setdefault("created_at", "")
                    notes.append(note)

            except (OSError, ValueError, TypeError):
                # Повреждённая заметка не должна ломать всю историю.
                continue

    notes.sort(
        key=lambda item: item.get("created_at", item.get("id", "")),
        reverse=True,
    )
    return notes


def load_chat_history():
    ensure_storage()

    with CHAT_LOCK:
        try:
            with open(CHAT_FILE, "r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)

            if isinstance(data, list):
                return [
                    item
                    for item in data
                    if isinstance(item, dict)
                    and item.get("role") in ("user", "assistant")
                    and isinstance(item.get("content"), str)
                ][-MAX_CHAT_MESSAGES:]

        except (OSError, ValueError, TypeError):
            pass

    return []


def save_chat_history(messages):
    ensure_storage()

    safe_messages = [
        {
            "role": item["role"],
            "content": item["content"],
        }
        for item in messages[-MAX_CHAT_MESSAGES:]
        if item.get("role") in ("user", "assistant")
        and isinstance(item.get("content"), str)
    ]

    with CHAT_LOCK:
        write_json_atomic(CHAT_FILE, safe_messages)


def build_notes_context(notes):
    """Формирование ограниченного контекста из сохранённых конспектов."""
    parts = []
    remaining = MAX_NOTE_CONTEXT_CHARS

    for note in notes:
        title = str(note.get("title") or "Без названия")
        body = str(note.get("text") or "").strip()

        if not body or remaining <= 0:
            continue

        chunk = "\n### {}\n{}".format(title, body)
        chunk = chunk[:remaining]

        parts.append(chunk)
        remaining -= len(chunk)

    return "\n".join(parts)


def friendly_api_error(response):
    if response.startswith("API_ERROR:"):
        bits = response.split(":", 2)
        code = bits[1] if len(bits) > 1 else "?"
        detail = bits[2] if len(bits) > 2 else ""

        if code == "401":
            return "Ошибка авторизации OpenRouter. Проверь API-ключ."
        if code == "402":
            return "Недостаточно средств или лимита в OpenRouter."
        if code == "429":
            return "Слишком много запросов. Подожди немного и попробуй снова."

        return "Ошибка API {}. {}".format(code, detail[:220])

    if response.startswith("NETWORK_ERROR:"):
        return (
            "Нет соединения с интернетом или сервер недоступен. "
            "Проверь подключение."
        )

    if response.startswith("REQUEST_ERROR:"):
        return "Не удалось выполнить запрос: {}".format(
            response.split(":", 1)[1][:220]
        )

    return response
    KV = r"""
#:import dp kivy.metrics.dp
#:import SlideTransition kivy.uix.screenmanager.SlideTransition

<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(12)
        spacing: dp(10)

        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(7)

            Button:
                id: btn_tab_new
                text: 'Загрузка'
                background_normal: ''
                background_color: (0.16, 0.43, 0.78, 1)
                on_release: root.switch_tab('new')

            Button:
                id: btn_tab_history
                text: 'Конспекты'
                background_normal: ''
                background_color: (0.32, 0.38, 0.47, 1)
                on_release: root.switch_tab('history')

            Button:
                id: btn_tab_chat
                text: 'Чат'
                background_normal: ''
                background_color: (0.32, 0.38, 0.47, 1)
                on_release: root.switch_tab('chat')

        ScreenManager:
            id: content_manager
            transition: SlideTransition(direction='left', duration=0.18)

            Screen:
                name: 'new'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)

                    Label:
                        text: 'Добавить конспект'
                        size_hint_y: None
                        height: dp(34)
                        color: (0.10, 0.16, 0.24, 1)
                        bold: True
                        font_size: '20sp'

                    TextInput:
                        id: path_input
                        hint_text: 'Путь к фото на устройстве'
                        multiline: False
                        size_hint_y: None
                        height: dp(48)
                        padding: dp(12), dp(12)

                    Button:
                        text: 'Распознать фото'
                        size_hint_y: None
                        height: dp(48)
                        background_normal: ''
                        background_color: (0.48, 0.31, 0.75, 1)
                        on_release: root.process_photo_by_path()

                    Label:
                        id: photo_status
                        text: 'Можно загрузить фото или вставить текст ниже'
                        color: (0.36, 0.41, 0.48, 1)
                        size_hint_y: None
                        height: dp(34)
                        font_size: '12sp'

                    ScrollView:
                        size_hint_y: 0.8
                        do_scroll_x: False
                        Label:
                            id: photo_output
                            text: 'Распознанный текст появится здесь.'
                            size_hint_y: None
                            height: max(self.texture_size[1] + dp(16), dp(70))
                            text_size: self.width - dp(16), None
                            halign: 'left'
                            valign: 'top'
                            color: (0.12, 0.17, 0.23, 1)
                            padding: dp(8), dp(8)

                    Label:
                        text: 'Или введи конспект вручную'
                        size_hint_y: None
                        height: dp(28)
                        color: (0.36, 0.41, 0.48, 1)

                    TextInput:
                        id: manual_text_input
                        hint_text: 'Вставь сюда конспект...'
                        multiline: True
                        size_hint_y: 0.9
                        padding: dp(12), dp(12)

                    Button:
                        text: 'Сохранить конспект'
                        size_hint_y: None
                        height: dp(50)
                        background_normal: ''
                        background_color: (0.12, 0.62, 0.42, 1)
                        on_release: root.save_manual_text()

            Screen:
                name: 'history'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(8)

                    Label:
                        text: 'Сохранённые конспекты'
                        size_hint_y: None
                        height: dp(34)
                        color: (0.10, 0.16, 0.24, 1)
                        bold: True
                        font_size: '19sp'

                    Button:
                        text: 'Обновить список'
                        size_hint_y: None
                        height: dp(42)
                        background_normal: ''
                        background_color: (0.16, 0.43, 0.78, 1)
                        on_release: root.load_history()

                    ScrollView:
                        do_scroll_x: False
                        BoxLayout:
                            id: history_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(8)
                            padding: 0, dp(4)

            Screen:
                name: 'chat'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(8)

                    BoxLayout:
                        size_hint_y: None
                        height: dp(42)

                        Label:
                            text: 'SmartNotes'
                            color: (0.10, 0.20, 0.32, 1)
                            bold: True
                            font_size: '19sp'
                            halign: 'left'

                        Button:
                            text: 'API'
                            size_hint_x: None
                            width: dp(54)
                            background_normal: ''
                            background_color: (0.82, 0.86, 0.91, 1)
                            color: (0.18, 0.23, 0.30, 1)
                            font_size: '12sp'
                            on_release: root.show_api_settings()

                        Button:
                            text: 'Очистить'
                            size_hint_x: None
                            width: dp(82)
                            background_normal: ''
                            background_color: (0.82, 0.86, 0.91, 1)
                            color: (0.18, 0.23, 0.30, 1)
                            font_size: '12sp'
                            on_release: root.clear_chat()

                    ScrollView:
                        id: chat_scroll
                        do_scroll_x: False
                        bar_width: dp(4)
                        scroll_type: ['bars', 'content']

                        BoxLayout:
                            id: chat_container
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(10)
                            padding: dp(4), dp(8)

                    BoxLayout:
                        size_hint_y: None
                        height: dp(56)
                        spacing: dp(7)

                        TextInput:
                            id: chat_input
                            hint_text: 'Спроси по своим конспектам...'
                            multiline: False
                            padding: dp(12), dp(12)
                            on_text_validate: root.send_chat_message()

                        Button:
                            text: '➤'
                            size_hint_x: None
                            width: dp(54)
                            font_size: '22sp'
                            background_normal: ''
                            background_color: (0.16, 0.43, 0.78, 1)
                            on_release: root.send_chat_message()
"""


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_history = []
        self.request_in_progress = False
        self.loading_widget = None
        Clock.schedule_once(self.setup_app, 0)

    def setup_app(self, _dt):
        try:
            init_storage()
            self.chat_history = load_chat_history()
            self.render_chat_history()
            self.load_history()
        except Exception as exc:
            self.show_status("Не удалось открыть данные: {}".format(exc))

    def show_status(self, message):
        if "photo_status" in self.ids:
            self.ids.photo_status.text = str(message)[:500]

    def switch_tab(self, name):
        self.ids.content_manager.current = name

        for key in ("new", "history", "chat"):
            self.ids["btn_tab_" + key].background_color = (
                (0.16, 0.43, 0.78, 1)
                if key == name else (0.32, 0.38, 0.47, 1)
            )

        if name == "history":
            self.load_history()
        elif name == "chat":
            Clock.schedule_once(self.scroll_chat_to_bottom, 0.12)

    def load_history(self):
        container = self.ids.history_container
        container.clear_widgets()
        notes = get_all_notes()

        if not notes:
            container.add_widget(Label(
                text="Пока нет конспектов. Добавь первый на вкладке «Загрузка».",
                size_hint_y=None,
                height=dp(64),
                color=(0.38, 0.43, 0.50, 1),
                halign="center",
            ))
            return

        for note in notes:
            title = str(note.get("title") or "Без названия")
            body = str(note.get("text") or "")
            preview = " ".join(body.split())[:90]

            button = Button(
                text="{}\n{}".format(title, preview),
                size_hint_y=None,
                height=dp(76),
                halign="left",
                valign="middle",
                text_size=(Window.width - dp(60), None),
                padding=(dp(12), dp(8)),
                background_normal="",
                background_color=(1, 1, 1, 1),
                color=(0.12, 0.17, 0.24, 1),
            )
            button.bind(
                on_release=lambda _btn, item=note: self.show_note(item)
            )
            container.add_widget(button)

    def show_note(self, note):
        content = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=dp(12),
        )

        text = Label(
            text=str(note.get("text", "")),
            size_hint_y=None,
            halign="left",
            valign="top",
            color=(0.12, 0.17, 0.24, 1),
            text_size=(Window.width - dp(60), None),
        )
        text.bind(
            texture_size=lambda widget, size:
                setattr(widget, "height", size[1] + dp(12))
        )

        from kivy.uix.scrollview import ScrollView
        scroll = ScrollView()
        scroll.add_widget(text)
        content.add_widget(scroll)

        actions = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(8),
        )
        ask_btn = Button(text="Спросить по конспектам")
        close_btn = Button(text="Закрыть")
        actions.add_widget(ask_btn)
        actions.add_widget(close_btn)
        content.add_widget(actions)

        popup = Popup(
            title=str(note.get("title", "Конспект")),
            content=content,
            size_hint=(0.94, 0.84),
            auto_dismiss=False,
        )

        ask_btn.bind(
            on_release=lambda *_: (
                popup.dismiss(),
                self.switch_tab("chat"),
                self.prefill_note_question(note),
            )
        )
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

    def prefill_note_question(self, note):
        self.ids.chat_input.text = (
            "Объясни понятнее конспект «{}»".format(
                str(note.get("title", "Без названия"))[:100]
            )
        )
        self.ids.chat_input.focus = True

    def save_manual_text(self):
        text = self.ids.manual_text_input.text.strip()

        if not text:
            self.show_status("Сначала введи текст конспекта.")
            return

        try:
            note = save_note(text)
            self.ids.manual_text_input.text = ""
            self.ids.photo_output.text = text
            self.show_status(
                "Конспект «{}» сохранён.".format(note["title"])
            )
            self.load_history()
        except Exception as exc:
            self.show_status("Не удалось сохранить конспект: {}".format(exc))

    def process_photo_by_path(self):
        path = self.ids.path_input.text.strip()

        if not path:
            self.show_status("Введи путь к фотографии.")
            return

        if not os.path.isfile(path):
            self.show_status(
                "Файл не найден. Проверь путь и разрешение на доступ к файлу."
            )
            return

        if not OCR_API_KEY:
            self.show_status(
                "Не настроен OCR API. Нажми API в чате и укажи ключ OCR.space."
            )
            return

        self.show_status("Распознаю фото…")
        threading.Thread(
            target=self.process_photo,
            args=(path,),
            daemon=True,
        ).start()

    def process_photo(self, path):
        try:
            with open(path, "rb") as file_obj:
                encoded = base64.b64encode(file_obj.read()).decode("ascii")

            payload = urllib.parse.urlencode({
                "apikey": OCR_API_KEY,
                "language": "rus",
                "base64Image": "data:image/jpeg;base64," + encoded,
            }).encode("utf-8")

            request = urllib.request.Request(
                "https://api.ocr.space/parse/image",
                data=payload,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                method="POST",
            )

            with urllib.request.urlopen(
                request,
                context=ssl.create_default_context(),
                timeout=45,
            ) as response:
                result = json.loads(
                    response.read().decode("utf-8", errors="replace")
                )

            if result.get("IsErroredOnProcessing"):
                raise RuntimeError(str(
                    result.get("ErrorMessage", "OCR не смог распознать изображение")
                ))

            parsed = result.get("ParsedResults") or []
            text = "\n".join(
                str(item.get("ParsedText", "")).strip()
                for item in parsed
                if isinstance(item, dict)
            ).strip()

            if not text:
                raise RuntimeError("На фото не удалось распознать текст.")

            note = save_note(text)
            self.update_photo_result(
                text,
                "Распознано и сохранено: {}".format(note["title"]),
            )
            Clock.schedule_once(lambda _dt: self.load_history(), 0)

        except Exception as exc:
            self.update_photo_result(
                "",
                "Ошибка распознавания: {}".format(exc),
            )

    @mainthread
    def update_photo_result(self, text, status):
        self.ids.photo_output.text = text or "Текст не распознан."
        self.show_status(status)
            def send_chat_message(self):
        if self.request_in_progress:
            self.show_status("Подожди, предыдущий запрос ещё выполняется.")
            return

        question = self.ids.chat_input.text.strip()
        if not question:
            return

        if not OPENROUTER_API_KEY:
            self.add_chat_bubble(
                "Не настроен ключ OpenRouter. Нажми кнопку API "
                "в верхней части чата и введи свой ключ.",
                is_user=False,
            )
            return

        self.ids.chat_input.text = ""
        self.add_chat_bubble(question, is_user=True)

        self.chat_history.append({
            "role": "user",
            "content": question,
        })

        self.request_in_progress = True

        self.loading_widget = self.add_chat_bubble(
            "Думаю…",
            is_user=False,
            temporary=True,
        )

        notes_snapshot = get_all_notes()
        history_snapshot = list(self.chat_history[-MAX_CHAT_MESSAGES:])

        threading.Thread(
            target=self.chat_worker,
            args=(
                question,
                notes_snapshot,
                history_snapshot,
                self.loading_widget,
            ),
            daemon=True,
        ).start()

    def chat_worker(self, question, notes, history, loading_widget):
        try:
            context = build_notes_context(notes)

            if context:
                system_prompt = (
                    "Ты — SmartNotes, помощник по учебным конспектам. "
                    "Сначала отвечай на основе переданных конспектов. "
                    "Объясняй простым языком, структурируй ответ и при "
                    "необходимости приводи короткий пример. Если дополняешь "
                    "материал знаниями вне конспектов, явно пометь раздел "
                    "«Дополнение». Не выдумывай, будто факт есть в конспекте, "
                    "если его там нет. Если конспекты не содержат ответа, "
                    "честно скажи об этом и затем можешь дать отдельное "
                    "общее объяснение.\n\n"
                    "Сохранённые конспекты пользователя:\n" + context
                )
            else:
                system_prompt = (
                    "Ты — SmartNotes, учебный помощник. Конспектов пока нет. "
                    "Отвечай понятно, а дополнительные знания явно помечай "
                    "как «Дополнение»."
                )

            messages = [
                {"role": "system", "content": system_prompt}
            ]
            messages.extend(history[-MAX_CHAT_MESSAGES:])

            payload = json.dumps({
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": 1200,
            }, ensure_ascii=False)

            response = safe_url_request(
                "https://openrouter.ai/api/v1/chat/completions",
                payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + OPENROUTER_API_KEY,
                    "HTTP-Referer": "https://github.com/",
                    "X-Title": "SmartNotes",
                },
            )

            if response.startswith((
                "API_ERROR:",
                "NETWORK_ERROR:",
                "REQUEST_ERROR:",
            )):
                answer = friendly_api_error(response)
            else:
                result = json.loads(response)
                choices = result.get("choices") or []

                if choices:
                    answer = str(
                        choices[0]["message"]["content"]
                    ).strip()
                else:
                    answer = ""

                if not answer:
                    answer = (
                        "Нейросеть вернула пустой ответ. "
                        "Попробуй задать вопрос иначе."
                    )

        except Exception as exc:
            answer = (
                "Не удалось получить ответ: {}. "
                "Проверь интернет и настройки API."
            ).format(exc)

        self.finish_chat_answer(answer, loading_widget)

    @mainthread
    def finish_chat_answer(self, answer, loading_widget):
        if (
            loading_widget is not None
            and loading_widget.parent is not None
        ):
            self.ids.chat_container.remove_widget(loading_widget)

        self.chat_history.append({
            "role": "assistant",
            "content": answer,
        })

        self.chat_history = self.chat_history[-MAX_CHAT_MESSAGES:]

        try:
            save_chat_history(self.chat_history)
        except Exception as exc:
            self.show_status(
                "Ответ получен, но история не сохранена: {}".format(exc)
            )

        self.request_in_progress = False
        self.loading_widget = None

        self.add_chat_bubble(answer, is_user=False)

    def render_chat_history(self):
        container = self.ids.chat_container
        container.clear_widgets()

        if not self.chat_history:
            self.add_chat_bubble(
                "Привет! Я SmartNotes. Сохрани конспект во вкладке "
                "«Загрузка», а затем задай вопрос — я буду использовать "
                "твои материалы в ответах.",
                is_user=False,
            )
            return

        for item in self.chat_history:
            self.add_chat_bubble(
                item.get("content", ""),
                is_user=item.get("role") == "user",
            )

        Clock.schedule_once(self.scroll_chat_to_bottom, 0.15)

    def add_chat_bubble(self, text, is_user, temporary=False):
        outer = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(10),
            padding=(dp(2), 0),
        )

        bubble = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            padding=(dp(12), dp(9)),
            spacing=dp(5),
        )

        # Оформление сообщений в стиле Telegram.
        bubble_color = (
            (0.80, 0.93, 0.86, 1)
            if is_user
            else (1, 1, 1, 1)
        )

        with bubble.canvas.before:
            Color(*bubble_color)
            bubble_bg = RoundedRectangle(
                pos=bubble.pos,
                size=bubble.size,
                radius=[dp(14)],
            )

        bubble.bind(
            pos=lambda widget, value: setattr(bubble_bg, "pos", value)
        )
        bubble.bind(
            size=lambda widget, value: setattr(bubble_bg, "size", value)
        )

        label = Label(
            text=str(text),
            size_hint=(1, None),
            halign="left",
            valign="top",
            color=(
                (0.08, 0.16, 0.13, 1)
                if is_user
                else (0.12, 0.17, 0.23, 1)
            ),
            font_size="15sp",
            text_size=(Window.width * 0.68, None),
            markup=False,
        )

        label.bind(
            texture_size=lambda widget, size:
                setattr(widget, "height", size[1])
        )

        bubble.add_widget(label)

        if not is_user and not temporary:
            copy_btn = Button(
                text="Копировать",
                size_hint=(None, None),
                size=(dp(100), dp(28)),
                background_normal="",
                background_color=(0.90, 0.93, 0.96, 1),
                color=(0.20, 0.30, 0.40, 1),
                font_size="11sp",
            )

            copy_btn.bind(
                on_release=lambda _btn, value=str(text):
                    self.copy_text(value)
            )

            bubble.add_widget(copy_btn)

        bubble.bind(minimum_height=bubble.setter("height"))

        bubble.width = min(Window.width * 0.82, dp(520))
        bubble.size_hint_x = None

        bubble.height = (
            label.texture_size[1]
            + dp(26)
            + (
                dp(33)
                if not is_user and not temporary
                else 0
            )
        )

        if is_user:
            outer.add_widget(BoxLayout())
            outer.add_widget(bubble)
        else:
            outer.add_widget(bubble)
            outer.add_widget(BoxLayout())

        outer.height = bubble.height
        self.ids.chat_container.add_widget(outer)

        Clock.schedule_once(self.scroll_chat_to_bottom, 0.08)

        return outer

    def scroll_chat_to_bottom(self, _dt):
        try:
            self.ids.chat_scroll.scroll_y = 0
        except Exception:
            pass

    def copy_text(self, text):
        try:
            Clipboard.copy(text)
            self.show_status("Ответ скопирован.")
        except Exception:
            self.show_status(
                "Не удалось скопировать ответ на этом устройстве."
            )

    def show_api_settings(self):
        content = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=dp(12),
        )

        content.add_widget(Label(
            text=(
                "Ключи сохраняются в приватной папке приложения "
                "на этом устройстве. Не публикуй их в открытом GitHub."
            ),
            size_hint_y=None,
            height=dp(62),
            color=(0.20, 0.25, 0.32, 1),
            halign="left",
            valign="middle",
        ))

        openrouter_input = TextInput(
            text=OPENROUTER_API_KEY,
            hint_text="OpenRouter API key",
            multiline=False,
            password=True,
            size_hint_y=None,
            height=dp(46),
        )

        ocr_input = TextInput(
            text=OCR_API_KEY,
            hint_text="OCR.space API key (необязательно)",
            multiline=False,
            password=True,
            size_hint_y=None,
            height=dp(46),
        )

        content.add_widget(openrouter_input)
        content.add_widget(ocr_input)

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(8),
        )

        save_btn = Button(text="Сохранить")
        cancel_btn = Button(text="Отмена")

        buttons.add_widget(save_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        popup = Popup(
            title="Настройки API",
            content=content,
            size_hint=(0.94, None),
            height=dp(310),
            auto_dismiss=False,
        )

        def save_keys(*_args):
            global OPENROUTER_API_KEY, OCR_API_KEY

            openrouter_key = openrouter_input.text.strip()
            ocr_key = ocr_input.text.strip()

            if not openrouter_key:
                self.show_status("Для чата нужен ключ OpenRouter.")
                return

            try:
                ensure_storage()

                write_json_atomic(
                    API_CONFIG_FILE,
                    {
                        "openrouter": openrouter_key,
                        "ocr": ocr_key,
                    },
                )

                OPENROUTER_API_KEY = openrouter_key
                OCR_API_KEY = ocr_key

                self.show_status(
                    "Настройки API сохранены на устройстве."
                )
                popup.dismiss()

            except Exception as exc:
                self.show_status(
                    "Не удалось сохранить ключи: {}".format(exc)
                )

        save_btn.bind(on_release=save_keys)
        cancel_btn.bind(on_release=popup.dismiss)

        popup.open()

    def clear_chat(self):
        self.chat_history = []

        try:
            save_chat_history([])
        except Exception as exc:
            self.show_status(
                "Не удалось очистить историю: {}".format(exc)
            )
            return

        self.render_chat_history()


class NotesApp(App):
    def build(self):
        Builder.load_string(KV)

        manager = ScreenManager()
        manager.add_widget(MainScreen(name="main"))

        return manager


if __name__ == "__main__":
    NotesApp().run()
