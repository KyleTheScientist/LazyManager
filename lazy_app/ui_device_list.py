import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.properties import StringProperty
from ui_components import BorderedButton


class Device(BorderedButton):

    label = StringProperty("?")
    ip = StringProperty("?")
    status = StringProperty("?")
    site = StringProperty("?")
    bv_type = StringProperty("?")
    lazy_egm_version = StringProperty("?")

    def __init__(self, app, properties={}, **kwargs):
        super().__init__(**kwargs)
        if not app:
            return
        self.app = app
        self.ws = app._manager
        self.status_label = app.status
        self.update_properties(properties)

    def update_properties(self, properties):
        for key, value in properties.items():
            print(key, "=", value)
            setattr(self, key, value)

        if "label" not in properties:
            self.label = f"EGM {self.id}"

    def send_command(self, command, status_text):
        print(status_text)
        self.status_label.text = status_text

        message = {"sender": "app", "command": command, "target": self.ip}
        self.ws.send(json.dumps(message))

    def stop_automakro(self):
        self.send_command("stop_automakro", f"Stopping AutoMakro on {self.id}")

    def start_automakro(self):
        self.send_command("start_automakro", f"Starting AutoMakro on {self.id}")

    def clear_ram(self):
        self.send_command("clear_ram", f"Clearing RAM on {self.id}")

    def stop_egm_controller(self):
        self.send_command("stop_egmc", f"Stopping EGM Controller on {self.id}")

    def start_egm_controller(self):
        self.send_command("start_egmc", f"Starting EGM Controller on {self.id}")

    def ping(self):
        self.send_command("ping", f"Pinging {self.id}")

    def f1(self):
        self.send_command("f1", f"Pressing F1 on {self.id}")

    def alt_tab(self):
        self.send_command("alt_tab", f"Pressing Alt+Tab on {self.id}")

    def start_explorer(self):
        self.send_command("start_explorer", f"Starting Explorer on {self.id}")

    def start_task_manager(self):
        self.send_command("start_task_manager", f"Starting Task Manager on {self.id}")

    def a(self):
        self.send_command("a", f"Pressing A on {self.id}")

    def b(self):
        self.send_command("b", f"Pressing B on {self.id}")

    def c(self):
        self.send_command("c", f"Pressing C on {self.id}")

    def d(self):
        self.send_command("d", f"Pressing D on {self.id}")


class Site(BoxLayout):
    name = StringProperty("-")
    count = StringProperty("0")
    device_list = StringProperty("")

    def add_device(self, device: Device):
        self.count = str(int(self.count) + 1)
        container = self.ids.container
        container.add_widget(device)
        container.children = sorted(container.children, key=lambda d: int(d.ip.split(".")[-1]), reverse=True)
        self.device_list = ", ".join(str(d.id) for d in reversed(container.children))
        # self.device_list = textwrap.fill(self.device_list, width=50)


class DeviceList(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sites = {}
        self.all_devices = []
        self.app = App.get_running_app()

    def add_or_update_device(self, properties):
        for d in self.all_devices:
            if d.ip == properties.get("ip", None):
                d.update_properties(properties)
                if self.app.device_properties.device == d:
                    self.app.device_properties.device = d  # Assignment triggers property refresh
                return

        device = Device(self.app, properties)
        self.all_devices.append(device)
        container = self.ids.container
        if device.site not in self.sites:
            site = Site(name=device.site)
            self.sites[device.site] = site
            container.add_widget(site)
        self.sites[device.site].add_device(device)

        container.children = sorted(container.children, key=lambda s: s.name, reverse=True)
