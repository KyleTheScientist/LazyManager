from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.properties import StringProperty, ObjectProperty, ColorProperty
from kivy.lang import Builder

Builder.load_file('devices.kv')

class DButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pressed = False

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.ud['scrollview_ignore'] = True 
            return super().on_touch_down(touch)
        return False

class SButton(Button):
    pass 

class Device(DButton):
    label = StringProperty("-")
    ip = StringProperty("-")
    status = StringProperty("-")
    site = StringProperty("-")
    bv_type = StringProperty("-")

    def __init__(self, app, properties={}, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._manager = app._manager
        self.status_label = app.status
        self.update_properties(properties)

    def update_properties(self, properties):
        for key, value in properties.items():
            setattr(self, key, value)
        
        if "label" not in properties:
            self.label = f"EGM {self.id}"

    def stop_automakro(self):
        print(f"Stopping AutoMakro on {self.id}")
        self.status_label.text = "Stopping AutoMakro..."
        self._manager.send(f"controller:stop_automakro:{self.ip}")

    def start_automakro(self):
        print(f"Starting AutoMakro on {self.id}")
        self.status_label.text = "Starting AutoMakro..."
        self._manager.send(f"controller:start_automakro:{self.ip}")

    def clear_ram(self):
        print(f"Clearing RAM on {self.id}")
        self.status_label.text = "Clearing RAM..."
        self._manager.send(f"controller:clear_ram:{self.ip}")

    def stop_egm_controller(self):
        print(f"Stopping EGM Controller on {self.id}")
        self.status_label.text = "Stopping EGM Controller..."
        self._manager.send(f"controller:stop_egmc:{self.ip}")

    def start_egm_controller(self):
        print(f"Starting EGM Controller on {self.id}")
        self.status_label.text = "Starting EGM Controller..."
        self._manager.send(f"controller:start_egmc:{self.ip}")
    
    def ping(self):
        print(f"Pinging {self.id}")
        self.status_label.text = "Pinging..."
        self._manager.send(f"controller:ping:{self.ip}")

    def f1(self):
        print(f"Pressing F1 on {self.id}")
        self.status_label.text = "F1"
        self._manager.send(f"controller:f1:{self.ip}")

    def f2(self):
        print(f"Pressing F2 on {self.id}")
        self.status_label.text = "F2"
        self._manager.send(f"controller:f2:{self.ip}")

class Site(BoxLayout):
    name = StringProperty("-")
    count = StringProperty("0")
    device_list = StringProperty("")

    def add_device(self, device: Device):
        self.count = str(int(self.count) + 1)
        container = self.ids.container
        container.add_widget(device)
        container.children = sorted(
            container.children,
            key=lambda d: int(d.ip.split(".")[-1]),
            reverse=True
        )
        self.device_list = ", ".join(d.id for d in reversed(container.children))
        # self.device_list = textwrap.fill(self.device_list, width=50)

class DeviceList(Screen):

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.sites = {}
        self.all_devices = []


    def add_device(self, properties):
        for d in self.all_devices:
            if d.ip == properties.get("ip", None):
                d.update_properties(properties)
                return

        device = Device(self.app, properties)
        self.all_devices.append(device)
        container = self.ids.container
        if device.site not in self.sites:
            site = Site(name=device.site)
            self.sites[device.site] = site
            container.add_widget(site)
        self.sites[device.site].add_device(device)
        
        container.children = sorted(
            container.children,
            key=lambda s: s.name,
            reverse=True
        )

class PropertyLabel(BoxLayout):
    title = StringProperty("")
    value = StringProperty("")
    color = ColorProperty((1, 1, 1, 1))

class DeviceProperties(Screen):

    device = ObjectProperty(None)
    
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.status = app.status

    def update_properties(self, device):
        self.device = device

    def stop_automakro(self):
        self.device.stop_automakro()
    
    def start_automakro(self):
        self.device.start_automakro()
    
    def clear_ram(self):
        self.device.clear_ram()

    def stop_egm_controller(self):
        self.device.stop_egm_controller()

    def start_egm_controller(self):
        self.device.start_egm_controller()

    def ping(self):
        self.device.ping()

    def f1(self):
        self.device.f1()

    def f2(self):
        self.device.f2()

class SiteProperties(Screen):

    site = ObjectProperty(None)
    
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.status = app.status

    def update_properties(self, site):
        self.site = site
    
    def stop_automakro(self):
        for device in self.site.ids.container.children:
            device.stop_automakro()

    def start_automakro(self):
        for device in self.site.ids.container.children:
            device.start_automakro()

    def clear_ram(self):
        for device in self.site.ids.container.children:
            device.clear_ram()

    def stop_egm_controller(self):
        for device in self.site.ids.container.children:
            device.stop_egm_controller()

    def start_egm_controller(self):
        for device in self.site.ids.container.children:
            device.start_egm_controller()

    def ping(self):
        for device in self.site.ids.container.children:
            device.ping()

    def f1(self):
        for device in self.site.ids.container.children:
            device.f1()

    def f2(self):
        for device in self.site.ids.container.children:
            device.f2()