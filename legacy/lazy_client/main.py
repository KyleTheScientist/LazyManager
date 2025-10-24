from kivy.config import Config

Config.set(
    "kivy",
    "default_font",
    [
        "resource/firacode.ttf",
        "resource/firacode-bold.ttf",
        "resource/firacode-light.ttf",
        "resource/firacode-semibold.ttf",
    ],
)

import threading
import json
from printmoji import print
from queue import Queue
from kivy.app import App
from devices import DeviceList, DeviceProperties, SiteProperties
from kivy.clock import Clock
from connection import WebSocketClient
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager



class MainApp(App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = WebSocketClient(self)
        self.client_thread = threading.Thread(target=self.client.start, daemon=True)
        self.client_thread.start()
        self.message_queue = Queue()
        Clock.schedule_interval(lambda dt: self.process_messages(), 1)

    def build_device_list_screen(self):
        self.device_list = DeviceList(self, name="devices")
        return self.device_list

    def build_device_properties_screen(self):
        self.device_properties = DeviceProperties(self, name="device_properties")
        return self.device_properties
    
    def build_site_properties_screen(self):
        self.site_properties = SiteProperties(self, name="site_properties")
        return self.site_properties

    def build(self):
        self.status = Label(text="Lazy Client", size_hint_y=None, height=30)
        
        self.screen_manager = ScreenManager()
        self.screen_manager.add_widget(self.build_device_list_screen())
        self.screen_manager.add_widget(self.build_device_properties_screen())
        self.screen_manager.add_widget(self.build_site_properties_screen())
        self.screen_manager.current = "devices"

        layout = BoxLayout(orientation="vertical")
        layout.add_widget(self.screen_manager)
        layout.add_widget(self.status)

        return layout

    def update_devices(self):
        print("🟪Updating device list")
        self.client.send("list_devices:")

    def add_device(self, properties):
        properties = json.loads(properties)

        self.device_list.add_device(properties)
    def process_messages(self):
        if not self.message_queue.empty():
            print(f"Processing {self.message_queue.qsize()} messages")

        while not self.message_queue.empty():
            command, data = self.message_queue.get().split(":", 1)
            print(f"    Command: {command}, Data: {data}")

            if command == "device":
                self.add_device(data)
            elif command == "status":
                self.status.text = data


if __name__ == "__main__":
    MainApp().run()
