from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from ui_device_list import Device, Site
from ui_components import HeightBox
from kivy.properties import StringProperty, ObjectProperty, ColorProperty
from kivy.app import App


class PropertyLabel(BoxLayout):

    title = StringProperty("")
    value = StringProperty("")
    color = ColorProperty((1, 1, 1, 1))

class ActionButtonGroup(HeightBox):
    executor = ObjectProperty(None)
    pass

class DeviceProperties(Screen):

    device = ObjectProperty(Device(None), rebind=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.status = self.app.status

    def __getattr__(self, attr):
        if hasattr(self.device, attr):
            return lambda: getattr(self.device, attr)()
        
        raise AttributeError("%r object has no attribute %r" %
                             (self.__class__.__name__, attr))

class SiteProperties(Screen):

    site = ObjectProperty(Site(), rebind=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.status = self.app.status

    def __getattr__(self, attr):
        if self.site.ids.container.children and hasattr(self.site.ids.container.children[0], attr):
            return lambda: self.run_all(attr)
        
        raise AttributeError("%r object has no attribute %r" %
                             (self.__class__.__name__, attr))

    def run_all(self, command: str):
        for device in self.site.ids.container.children:
            getattr(device, command)()
