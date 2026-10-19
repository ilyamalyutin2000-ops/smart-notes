from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

class TestApp(App):
    def build(self):
        # Простой интерфейс: зеленая надпись и кнопка
        layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        layout.add_widget(Label(text="ТЕСТ РАБОТАЕТ!", font_size='30sp', color=(0,1,0,1)))
        
        btn = Button(text="Нажми меня", size_hint=(1, 0.5))
        btn.bind(on_release=lambda x: print("Кнопка нажата!"))
        layout.add_widget(btn)
        
        return layout

if __name__ == '__main__':
    TestApp().run()
