import json
import asyncio
from makro.lazy_manager.egm import DEVICES, get_device
from pathlib import Path
from textwrap import indent
from tempfile import TemporaryDirectory
from printmoji import print
from asyncio.subprocess import PIPE


psexec_command = r'psexec \\{ip} -i 1 -d -u Administrator -p replay -w "D:\AutoMakro" cmd /c "{command}"'
kill_command = psexec_command.format(ip="{ip}", command=r"taskkill /F /IM AutoMakro.exe")
start_command = psexec_command.format(ip="{ip}", command=r".\AutoMakro.exe")
clear_ram = psexec_command.format(
    ip="{ip}", command=r"taskkill /IM EGMController.exe & timeout 3 & rmdir /s /q E:\Storage"
)
stop_egm_controller_command = psexec_command.format(ip="{ip}", command=r"taskkill /IM EGMController.exe")
start_egm_controller_command = psexec_command.format(ip="{ip}", command=r"D:\BS.lnk")
update_configs_command = r"pushd \\{ip}\E$ & copy {path} .\Config\ /Y & popd"


class MakroServer:
    def __init__(self):
        pass

    # async def run_all(self, name, command):
    #     tasks = []
    #     offline = []
    #     for device in DEVICES:
    #         # Check if device is reachable
    #         if not await device.is_reachable():
    #             offline.append(device)
    #             print(f"🟥{device} is offline, skipping {name} command.")
    #             continue
    #         # Run the command
    #         task = asyncio.create_task(self.run_subprocess(device.ip, name, command))
    #         tasks.append(task)

    #     # Wait for all tasks to complete
    #     await asyncio.gather(*tasks, return_exceptions=True)

    #     if offline: # List devices that were offline and skipped
    #         failed = [d.id for d in offline]
    #         return "status", f"({name}) Failed on device {', '.join(failed)}"

    #     return "status", f"Sent {name} command to all devices"

    async def run_subprocess(self, device, name, command, success_str="cmd started"):
        # Run command on all devices in parallel
        # if ip == "All":
        #     return await self.run_all(name, command)

        # Check if device is reachable
        connected = await device.is_reachable()
        if not connected:
            return "status", f"{device} is offline"

        # Run the command
        print(f"Running {name} command on {device}...")
        command = command.format(ip=device.ip)
        print(f"$ 🟦{command}")
        process = await asyncio.create_subprocess_shell(command, stdout=PIPE, stderr=PIPE)

        # Await process completion and get output
        stdout, stderr = await process.communicate()
        stdout, stderr = stdout.decode().strip(), stderr.decode().strip()

        # Print output for debugging
        print(f"{name} ({device}):")
        if not command.startswith("psexec"):
            print(f"OUT: {indent(stdout, '    ')}")
        print(f"ERR: {indent(stderr, '    ')}")

        # Check for success string in output
        if success_str in (stdout + stderr).lower():
            return "status", f"({device}) Sent {name} command"
        else:
            return "status", f"({device}) Failed to send {name} command"

    def get_egm_config(self, device):
        config_xml = Path(__file__).parent / "resource/Config.xml"
        text = config_xml.read_text(encoding="utf-8")
        return text.format(terminal_number=device.id)

    def get_device_config(self, device):
        device_configuration_xml = Path(__file__).parent / "resource/DeviceConfiguration.xml"
        text = device_configuration_xml.read_text(encoding="utf-8")
        return text.format(bv_type=device.bv_type)

    def generate_configs_directory(self, device):
        with TemporaryDirectory() as tempdir:
            # Copy the two XML files into the temporary directory
            config_xml_dst = Path(tempdir) / "Config.xml"
            device_configuration_xml_dst = Path(tempdir) / "DeviceConfiguration.xml"

            config_xml_dst.write_text(self.get_egm_config(device))
            device_configuration_xml_dst.write_text(self.get_device_config(device))

        return Path(tempdir)

    async def update_configs(self, device):
        config_dir = self.generate_configs_directory(device)
        command = update_configs_command.format(ip=device.ip, path=str(config_dir / "*"))
        result = await self.run_subprocess(device, "Config Update", command, success_str="1 file(s) copied")
        return result

    async def clear_ram(self, ip):
        device = get_device(ip)
        config_result = await self.update_configs(device)
        ram_result = await self.run_subprocess(device, "RAM Clear", clear_ram)
        return "status", f"{config_result[1]}; {ram_result[1]}"

    async def stop_egm_controller(self, ip):
        device = get_device(ip)
        return await self.run_subprocess(device, "EGM Controller stop", stop_egm_controller_command)

    async def start_egm_controller(self, ip):
        device = get_device(ip)
        return await self.run_subprocess(device, "EGM Controller start", start_egm_controller_command)

    async def start_automakro(self, ip):
        device = get_device(ip)
        return await self.run_subprocess(device, "Start Automakro", start_command)

    async def stop_automakro(self, ip):
        device = get_device(ip)
        return await self.run_subprocess(device, "Stop Automakro", kill_command)

    async def ping(self, ip, client):
        device = get_device(ip)
        connected = await device.is_reachable()
        device.status = "Online" if connected else "Offline"
        await client.send(f"device:{device.serialize()}")
        await client.send(f"status:({device}) Ping {'successful' if connected else 'failed'}")

    async def send_device(self, device, client):
        await device.is_reachable()
        await client.send(f"device:{device.serialize()}")

    async def list_devices(self, client):
        tasks = []
        for d in DEVICES:
            task = asyncio.create_task(self.send_device(d, client))
            tasks.append(task)
        await asyncio.gather(*tasks)

    def get_log(self, ip, log_type):
        print(f"Fetching {log_type} log for {ip}")
        device = DEVICES.get(ip)
        if device and device["status"] == "online":
            return device.get(f"{log_type}_log")
        return ""
