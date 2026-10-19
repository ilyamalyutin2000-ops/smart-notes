# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime
from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
from kivy.animation import Animation

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
                        text: 'Тест кнопки загрузки'
                        size_hint_y: None
                        height: dp(60)
                        bg_color_normal: (0.55, 0.3, 0.8, 1)
                        bg_color_active: (0.55, 0.3, 0.8, 1)
                        on_release: root.test_click()

            Screen:
                name: 'history'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    Label:
                        text: 'Здесь будут конспекты'
                        color: (0.5, 0.5, 0.5, 1)

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
                            hint_text: 'Введите вопрос...'
                            multiline: False
                        TabButton:
                            text: 'Ввод'
                            size_hint_x: None
                            width: dp(90)
                            bg_color_normal: (0.15, 0.45, 0.85, 1)
                            bg_color_active: (0.15, 0.45, 0.85, 1)
                            on_release: root.test_click()
"""

class MainScreen(Screen):
    def switch_tab(self, name):
        self.ids.content_manager.current = name
        self.ids.btn_tab_new.set_active(name == 'new')
        self.ids.btn_tab_history.set_active(name == 'history')
        self.ids.btn_tab_chat.set_active(name == 'chat')

    def test_click(self):
        # Просто добавляем текст в чат, проверяя, что UI работает
        lbl = Label(text="Кнопка работает!", size_hint_y=None, height=dp(40), color=(0,0.5,0,1))
        self.ids.chat_container.add_widget(lbl)

class NotesApp(App):
    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    NotesApp().run()
