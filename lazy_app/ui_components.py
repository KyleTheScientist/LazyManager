from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty

class MainBox(BoxLayout):
    pass

class BorderedButton(Button):
    pass

class TextButton(Button):
    pass 

class HeightBox(BoxLayout):
    pass

class OutlinedSection(HeightBox):
    pass

class TitleBar(BoxLayout):

    title = StringProperty("")
    back_screen = StringProperty("devices")