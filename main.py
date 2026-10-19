from kivy.app import App
from kivy.uix.label import Label

class TestApp(App):
    def build(self):
        return Label(text="ТЕСТ РАБОТАЕТ!", font_size='30sp', color=(0,1,0,1))

if __name__ == '__main__':
    TestApp().run()
