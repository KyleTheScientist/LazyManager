from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.properties import StringProperty, ObjectProperty, ColorProperty
from kivy.lang import Builder
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
        self._manager = app._manager
        self.status_label = app.status
        self.update_properties(properties)

    def update_properties(self, properties):
        for key, value in properties.items():
            print(key, "=", value)
            setattr(self, key, value)

        if "label" not in properties:
            self.label = f"EGM {self.id}"

    def stop_automakro(self):
        print(f"Stopping AutoMakro on {self.id}")
        self.status_label.text = "Stopping AutoMakro..."
        self._manager.send(f"app:stop_automakro:{self.ip}")

    def start_automakro(self):
        print(f"Starting AutoMakro on {self.id}")
        self.status_label.text = "Starting AutoMakro..."
        self._manager.send(f"app:start_automakro:{self.ip}")

    def clear_ram(self):
        print(f"Clearing RAM on {self.id}")
        self.status_label.text = "Clearing RAM..."
        self._manager.send(f"app:clear_ram:{self.ip}")

    def stop_egm_controller(self):
        print(f"Stopping EGM Controller on {self.id}")
        self.status_label.text = "Stopping EGM Controller..."
        self._manager.send(f"app:stop_egmc:{self.ip}")

    def start_egm_controller(self):
        print(f"Starting EGM Controller on {self.id}")
        self.status_label.text = "Starting EGM Controller..."
        self._manager.send(f"app:start_egmc:{self.ip}")

    def ping(self):
        print(f"Pinging {self.id}")
        self.status_label.text = "Pinging..."
        self._manager.send(f"app:ping:{self.ip}")

    def f1(self):
        print(f"Pressing F1 on {self.id}")
        self.status_label.text = "F1"
        self._manager.send(f"app:f1:{self.ip}")

    def alt_tab(self):
        print(f"Pressing Alt+Tab on {self.id}")
        self.status_label.text = "Alt+Tab"
        self._manager.send(f"app:alt_tab:{self.ip}")

    def start_explorer(self):
        print(f"Starting Explorer on {self.id}")
        self.status_label.text = "Starting Explorer..."
        self._manager.send(f"app:start_explorer:{self.ip}")

    def start_task_manager(self):
        print(f"Starting Task Manager on {self.id}")
        self.status_label.text = "Starting Task Manager..."
        self._manager.send(f"app:start_task_manager:{self.ip}")

    def a(self):
        print(f"Pressing A on {self.id}")
        self.status_label.text = "A"
        self._manager.send(f"app:a:{self.ip}")

    def b(self):
        print(f"Pressing B on {self.id}")
        self.status_label.text = "B"
        self._manager.send(f"app:b:{self.ip}")

    def c(self):
        print(f"Pressing C on {self.id}")
        self.status_label.text = "C"
        self._manager.send(f"app:c:{self.ip}")

    def d(self):
        print(f"Pressing D on {self.id}")
        self.status_label.text = "D"
        self._manager.send(f"app:d:{self.ip}")


class Site(BoxLayout):
    name = StringProperty("-")
    count = StringProperty("0")
    device_list = StringProperty("")

    def add_device(self, device: Device):
        self.count = str(int(self.count) + 1)
        container = self.ids.container
        container.add_widget(device)
        container.children = sorted(container.children, key=lambda d: int(d.ip.split(".")[-1]), reverse=True)
        self.device_list = ", ".join(d.id for d in reversed(container.children))
        # self.device_list = textwrap.fill(self.device_list, width=50)


class DeviceList(Screen):

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.sites = {}
        self.all_devices = []

    def add_or_update_device(self, properties):
        for d in self.all_devices:
            if d.ip == properties.get("ip", None):
                d.update_properties(properties)
                if self.app.device_properties.device == d:
                    self.app.device_properties.device = d # Assignment triggers property refresh
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