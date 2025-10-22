from kivy.config import Config
from kivy.lang import Builder
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

import asyncio
import threading
from printmoji import print
from lazy_socket.server import LazyServer

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager

from ui_components import MainBox
from ui_device_list import DeviceList
from ui_properties import DeviceProperties, SiteProperties


class Manager:

    def __init__(self, app: "MainApp"):
        self.client = None
        self.app = app

    def send(self, message):
        if self.client:
            print(f"🟧Sending: {message}")
            self.app.server.send(message, client=self.client)
        else:
            print("No client connected to send message")


class MainApp(App):

    BACKGROUND = 0.204, 0.278, 0.341, 1
    POSITIVE = 0.263, 0.667, 0.545, 1
    NEGATIVE = 0.976, 0.255, 0.267, 1
    NEUTRAL = 0.976, 0.78, 0.31, 1
    BLACK = 0, 0, 0, 1
    WHITE = 1, 1, 1, 1
    BUTTON_UP = 0.11, 0.239, 0.349, 1
    BUTTON_DOWN = 0.051, 0.173, 0.278, 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Builder.load_file("ui_components.kv")
        Builder.load_file("ui_device_list.kv")
        Builder.load_file("ui_properties.kv")
        self.server = LazyServer(name="LazyApp", host="0.0.0.0", port=8767, broadcast=True)
        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server.process_message = self.process_message
        self.server_thread.start()
        self._manager = Manager(self)

        Clock.schedule_interval(lambda dt: self.update_devices(), 10)

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
        print("Building!")
        self.status = Label(text="Lazy App", size_hint_y=None, height=30)

        self.screen_manager = ScreenManager()
        self.screen_manager.add_widget(self.build_device_list_screen())
        self.screen_manager.add_widget(self.build_device_properties_screen())
        self.screen_manager.add_widget(self.build_site_properties_screen())
        self.screen_manager.current = "devices"

        layout = MainBox(orientation="vertical")
        layout.add_widget(self.screen_manager)
        layout.add_widget(self.status)

        return layout

    def update_devices(self):
        print("🟪Updating device list")
        self._manager.send("app:list_devices")

    def add_device(self, properties):
        _properties = {}
        for prop in properties.split("&"):
            k, v = prop.split("=")
            _properties[k] = v
        properties = _properties
        self.device_list.add_or_update_device(properties)
        print(f"🟩Added/Updated device {properties.get('ip', 'Unknown IP')}")

    async def process_message(self, client, message):
        split = message.split(":")
        sender, command = split[0], split[1:]
        print(f"Received message from {sender}: {command}")

        if sender == "manager":
            if command[0] == "connected":
                self._manager.client = client
                print("🟨Connected to manager")
                self.status.text = "Connected to manager"
                self.update_devices()
                return
            if command[0] == "egm":
                Clock.schedule_once(lambda dt: self.add_device(command[1]))
                return
            if command[1] == "status":
                status_message = ":".join(command[2:])
                print(f"🟨Manager status: {status_message}")
                self.status.text = f"Manager: {status_message}"

        if sender == "egm" and command[0] == "result":
            _, __, agent_ip, command, result = message.split(":", 4)
            print(f"🟨EGM {agent_ip} - {command} result: {result}")
            self.status.text = f"EGM {agent_ip} - {command}: {result}"


if __name__ == "__main__":
    MainApp().run()
