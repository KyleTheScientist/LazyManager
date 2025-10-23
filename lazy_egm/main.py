import time
import socket
import json
import subprocess
import pyautogui
from lazy_socket.server import LazyServer
from pathlib import Path
from shutil import rmtree

CONFIG_PATH = Path("lazy_egm.cfg")
VERSION = "1.0.2"


class EGM(LazyServer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.properties = self.load_config()
        self.properties["lazy_egm_version"] = VERSION

    def load_config(self):
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text())
        else:
            content = {"site": "lab/warehouse", "bv_type": "JcmUba/MeiCashflow", "type": "vertical/1600"}
            CONFIG_PATH.touch()
            CONFIG_PATH.write_text(json.dumps(content, indent=4))
            return content

    async def send_response(self, client, data, **kwargs):
        await client.send(
            json.dumps(dict(sender="egm", command=data["command"], **kwargs))
        )

    async def process_message(self, client, message):
        data = json.loads(message)
        if data["sender"] == "manager":
            try:
                await self.run_manager_command(client, data)
            except Exception as e:
                print(f"Error processing manager command {data['command']}: {e}")
                await self.send_response(client, data, result=f"Failure - {e}")

        if data["sender"] == "app":
            try:
                await self.run_app_command(client, data)
            except Exception as e:
                print(f"Error processing app command {data['command']}: {e}")
                await self.send_response(client, data, result=f"Failure - {e}")

    async def run_manager_command(self, client, data):
        if data["command"] == "register":
            await self.send_response(client, data, result=self.properties)

        if data["command"] == "ping":
            await self.send_response(client, data, result="pong")

    async def run_app_command(self, client, data):
        app_ip = data["sender_ip"]
        command = data["command"]

        if command == "ping":
            await self.send_response(client, data, result="Success", app_ip=app_ip)

        elif command == "start_explorer":
            result = "Success" if self._try_start("explorer.exe", poll=False) else "Failure"
            await self.send_response(client, data, result=result, app_ip=app_ip)

        elif command == "start_task_manager":
            result = "Success" if self._try_start("taskmgr.exe") else "Failure"
            await self.send_response(client, data, result=result, app_ip=app_ip)

        elif command == "stop_automakro":
            result = "Success" if self._try_kill("AutoMakro.exe") else "Failure"
            await self.send_response(client, data, result=result, app_ip=app_ip)

        elif command == "start_automakro":
            result = "Success" if self._try_start("AutoMakro.exe", cwd="D:/AutoMakro") else "Failure"
            await self.send_response(client, data, result=result, app_ip=app_ip)

        elif command == "stop_egmc":
            result = "Success" if self._try_kill("EGMController.exe", force=False) else "Failure"
            await self.send_response(client, data, result=result, app_ip=app_ip)

        elif command == "start_egmc":
            result = "Success" if self._try_start("EGMController.exe", cwd="D:/EGMController") else "Failure"
            await self.send_response(client, data, result=result, app_ip=app_ip)

        elif command == "clear_ram":
            try:
                rmtree("E:/Storage")
                await self.send_response(client, data, result="Success", app_ip=app_ip)
            except FileNotFoundError:
                await self.send_response(client, data, result="No files to delete", app_ip=app_ip)
            except Exception as e:
                await self.send_response(client, data, result=f"Failure - {e}", app_ip=app_ip)

        elif command == "f1":
            pyautogui.press("f1")
            await self.send_response(client, data, result="Success", app_ip=app_ip)

        elif command == "alt_tab":
            pyautogui.hotkey("alt", "tab", interval=0.2)
            await self.send_response(client, data, result="Success", app_ip=app_ip)

        elif command == "mouse_move":
            dx = data.get("dx", 0)
            dy = data.get("dy", 0)
            pyautogui.moveRel(dx, -dy, duration=0.1)
            await self.send_response(client, data, result="Success", app_ip=app_ip)

        elif command == "left_click":
            pyautogui.click()
            await self.send_response(client, data, result="Success", app_ip=app_ip)

        elif command == "right_click":
            pyautogui.click(button="right")
            await self.send_response(client, data, result="Success", app_ip=app_ip)

        elif command == "key_press":
            pyautogui.press(data["key"])
            await self.send_response(client, data, result="Success", app_ip=app_ip)

        elif command == "a":
            pass

        elif command == "b":
            pass

        elif command == "c":
            pass

        elif command == "d":
            pass

        else:
            await self.send_response(client, data, result="Unknown command", app_ip=app_ip)

    def _try_kill(self, process_name, force=True):
        command = f"taskkill {'/F' if force else ''} /IM {process_name}"
        print(command)
        result = subprocess.run(command, capture_output=True, shell=True)
        return result.returncode == 0 or result.returncode == 128

    def _try_start(self, process_path, cwd=None, poll=True):
        print(process_path)
        result = subprocess.Popen(process_path, cwd=cwd, shell=True)
        if not poll:
            return True
        time.sleep(2)
        return result.poll() is None

    def _try_run(self, command, rc=0):
        print(command)
        result = subprocess.run(command, capture_output=True, shell=True)
        print(result.returncode)
        return result.returncode == rc

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip


if __name__ == "__main__":
    egm = EGM(name="LazyEGM", host="0.0.0.0", port=8765, broadcast=False)
    egm.start()
