import json
from kivy.properties import NumericProperty, ObjectProperty
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from ui_device_list import Device


class Trackpad(Widget):

    executor = ObjectProperty(None)

    # Sensitivity multiplier for mouse movement
    sensitivity = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_touches = {}
        self.first_touch_pos = {}
        self.last_touch_pos = {}

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False

        touch.grab(self)

        self.active_touches[touch.uid] = touch
        self.first_touch_pos[touch.uid] = touch.pos
        self.last_touch_pos[touch.uid] = touch.pos

        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False

        if touch.uid not in self.last_touch_pos:
            return False

        # Calculate delta movement
        last_pos = self.last_touch_pos[touch.uid]
        dx = (touch.x - last_pos[0]) * self.sensitivity
        dy = (touch.y - last_pos[1]) * self.sensitivity

        self.last_touch_pos[touch.uid] = touch.pos

        # Determine gesture type based on number of touches
        if len(self.active_touches) == 1:
            # Single finger drag = mouse move
            self.executor.on_mouse_move(dx, dy)

        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False

        touch.ungrab(self)

        if touch.uid in self.active_touches:
            dx = touch.x - self.first_touch_pos[touch.uid][0]
            dy = touch.y - self.first_touch_pos[touch.uid][1]
            if abs(dx) < 5 and abs(dy) < 5:
                self.executor.on_left_click()

        # Clean up
        if touch.uid in self.active_touches:
            del self.active_touches[touch.uid]
        if touch.uid in self.last_touch_pos:
            del self.last_touch_pos[touch.uid]

        return True


class TrackpadScreen(Screen):

    device: Device = ObjectProperty(Device(None))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.moves = []
        Clock.schedule_interval(self.sum_mouse_moves, 0.1)
    
    def send_command(self, command, status_text, **kwargs):
        print(status_text)
        message = {"sender": "app", "command": command, "target": self.device.ip}
        message.update(kwargs)
        self.device.ws.send(json.dumps(message))

    def sum_mouse_moves(self, dt):
        if not self.moves:
            return
        total_dx = sum(dx for dx, dy in self.moves)
        total_dy = sum(dy for dx, dy in self.moves)
        self.moves = []
        self.send_command("mouse_move", f"Moving mouse by ({total_dx}, {total_dy})", dx=total_dx, dy=total_dy)

    def on_mouse_move(self, dx, dy):
        self.moves.append((dx, dy))

    def on_left_click(self):
        self.send_command("left_click", f"Mouse left click")

    def on_right_click(self):
        self.send_command("right_click", f"Mouse right click")

    def on_key_press(self, key):
        self.send_command("key_press", f"Key pressed: {key}", key=key)

class KeyboardInput(TextInput):

    executor = ObjectProperty(None)

    def insert_text(self, substring, from_undo=False):
        self.executor.on_key_press(substring)
        self.text = ''  # Clear the TextInput after capturing the key
        return super().insert_text(substring, from_undo)
    

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        key_num, key_name = keycode
        
        print(f"Key pressed: {key_name}")
        if key_name == 'backspace':
            self.executor.on_key_press('backspace')
        elif key_name == 'shift':
            self.executor.on_key_press('shift')
        elif key_name == 'escape':
            self.executor.on_key_press('escape')
        elif key_name == 'lctrl':
            self.executor.on_key_press('ctrl')
        elif key_name == 'enter':
            self.executor.on_key_press('enter')
        
        return super().keyboard_on_key_down(window, keycode, text, modifiers)