# -*- coding: utf-8 -*-
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp

# Никаких графических инструкций и анимаций, только стандартные элементы
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

        BoxLayout:
            size_hint_y: None
            height: dp(45)
            spacing: dp(5)
            # Обычные кнопки
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
            transition: SlideTransition(direction='left', duration=0.3)
            
            Screen:
                name: 'new'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    Button:
                        text: 'Тест кнопки загрузки'
                        size_hint_y: None
                        height: dp(60)
                        background_color: 0.55, 0.3, 0.8, 1
                        on_release: root.test_click()

            Screen:
                name: 'history'
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    Label:
                        text: 'Здесь будут конспекты'

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
                        Button:
                            text: 'Ввод'
                            size_hint_x: None
                            width: dp(90)
                            background_color: 0.15, 0.45, 0.85, 1
                            on_release: root.test_click()
"""

class MainScreen(Screen):
    def switch_tab(self, name):
        self.ids.content_manager.current = name
        
        # Вручную меняем цвета обычных кнопок
        self.ids.btn_tab_new.background_color = (0.15, 0.45, 0.85, 1) if name == 'new' else (0.4, 0.4, 0.45, 1)
        self.ids.btn_tab_history.background_color = (0.15, 0.45, 0.85, 1) if name == 'history' else (0.4, 0.4, 0.45, 1)
        self.ids.btn_tab_chat.background_color = (0.15, 0.45, 0.85, 1) if name == 'chat' else (0.4, 0.4, 0.45, 1)

    def test_click(self):
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
