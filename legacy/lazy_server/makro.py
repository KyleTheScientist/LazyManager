import asyncio
from device import DEVICES, get_device
from pathlib import Path
from textwrap import indent
from tempfile import TemporaryDirectory
from printmoji import print
from asyncio.subprocess import PIPE

SCHEDULE_TASK_COMMANDS = [
    'powershell.exe -Command "Set-Content -Path {cwd}\\lazy.bat -Value \'cd /d %~dp0 & {command}\'"',
    "schtasks /create /SC ONCE /TN {name} /TR {cwd}\\lazy.bat /ST 23:58",
    "schtasks /run /TN {name}",
    "schtasks /delete /TN {name} /F",
    "ping 127.0.0.1 -n 10",
    "del {cwd}\\lazy.bat"
]


class MakroServer:
    def __init__(self):
        self.connections = []

    async def run_ssh_command(self, device, name, command, success_str=None):
        """Execute a command via SSH using paramiko"""
        # Check if device is reachable
        connected = await device.is_reachable()
        if not connected:
            return "status", f"{device} is offline"

        # Run the command
        print(f"Running {name} command on {device}...")
        print(f"$ 🟦{command}")

        loop = asyncio.get_running_loop()
        stdin, stdout, stderr = await loop.run_in_executor(None, device.client.exec_command, command)
        out = await loop.run_in_executor(None, stdout.read)
        err = await loop.run_in_executor(None, stderr.read)

        out = out.decode(errors="ignore").strip() if isinstance(out, (bytes, bytearray)) else str(out).strip()
        err = err.decode(errors="ignore").strip() if isinstance(err, (bytes, bytearray)) else str(err).strip()

        # Print output for debugging
        print(f"{name} ({device}):")
        if out:
            print(f"OUT: {indent(out, '    ')}")
        if err:
            print(f"ERR: {indent(err, '    ')}")

        # Check for success string in output if provided
        if success_str:
            combined_output = (out + err).lower()
            if success_str.lower() in combined_output:
                return "status", f"({device}) Sent {name} command"
            else:
                return "status", f"({device}) Failed to send {name} command"

        return "status", f"({device}) Sent {name} command"

    def get_egm_config(self, device):
        config_xml = Path(__file__).parent / "resource/Config.xml"
        text = config_xml.read_text(encoding="utf-8")
        return text.format(terminal_number=device.octet)

    def get_device_config(self, device):
        device_configuration_xml = Path(__file__).parent / "resource/DeviceConfiguration.xml"
        text = device_configuration_xml.read_text(encoding="utf-8")
        return text.format(bv_type=device.bv_type)

    def generate_configs_directory(self, device):
        with TemporaryDirectory(delete=False) as tempdir:
            # Copy the two XML files into the temporary directory
            config_xml_dst = Path(tempdir) / "Config.xml"
            device_configuration_xml_dst = Path(tempdir) / "DeviceConfiguration.xml"

            config_xml_dst.write_text(self.get_egm_config(device))
            device_configuration_xml_dst.write_text(self.get_device_config(device))
        return Path(tempdir)

    async def update_configs(self, device):
        """Update configuration files via SFTP"""
        connected = await device.is_reachable()
        if not connected:
            return "status", f"{device} is offline"

        config_dir = self.generate_configs_directory(device)

        try:
            loop = asyncio.get_running_loop()

            # Open SFTP session
            sftp = await loop.run_in_executor(None, device.client.open_sftp)

            # Upload Config.xml
            local_config = str(config_dir / "Config.xml")
            remote_config = "E:/Config/Config.xml"
            await loop.run_in_executor(None, sftp.put, local_config, remote_config)

            # Upload DeviceConfiguration.xml
            local_device_config = str(config_dir / "DeviceConfiguration.xml")
            remote_device_config = "E:/Config/DeviceConfiguration.xml"
            await loop.run_in_executor(None, sftp.put, local_device_config, remote_device_config)

            await loop.run_in_executor(None, sftp.close)

            return "status", f"({device}) Config Update successful"
        except Exception as e:
            print(f"Error updating configs: {e}")
            return "status", f"({device}) Failed to update configs: {str(e)}"

    async def deploy(self, ip, client):
        device = get_device(ip)
        sftp_client = device.client.open_sftp()

        local_file_path = "C:/Users/kwilliams/work/quality_assurance/AutoMakro/dist/AutoMakro.exe"
        remote_file_path = "D:/AutoMakro/AutoMakro.exe"

        sftp_client.put(local_file_path, remote_file_path)
        print(f"File '{local_file_path}' uploaded to '{remote_file_path}' successfully.")

        return "status", f"({device}) Deployment successful"

    async def clear_ram(self, ip):
        device = get_device(ip)
        config_result = await self.update_configs(device)

        # Kill EGMController.exe, wait, then remove directory
        command = r"taskkill /IM EGMController.exe & timeout 3 & rmdir /s /q E:\Storage"
        ram_result = await self.run_ssh_command(device, "RAM Clear", command)

        return "status", f"{config_result[1]}; {ram_result[1]}"

    async def stop_egm_controller(self, ip):
        device = get_device(ip)
        command = r"taskkill /IM EGMController.exe"
        return await self.run_ssh_command(device, "EGM Controller stop", command)

    async def start_egm_controller(self, ip):
        device = get_device(ip)
        command = r"D:\BS.lnk"
        return await self.run_ssh_command(device, "EGM Controller start", command)

    async def start_automakro(self, ip):
        device = get_device(ip)
        command = " & ".join(SCHEDULE_TASK_COMMANDS).format(
            name="StartAutomakro",
            cwd=r"D:\AutoMakro",
            command=r'AutoMakro.exe'
        )
        return await self.run_ssh_command(device, "Start Automakro", command)

    async def stop_automakro(self, ip):
        device = get_device(ip)
        command = r"taskkill /F /IM AutoMakro.exe"
        return await self.run_ssh_command(device, "AutoMakro stop", command)

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
