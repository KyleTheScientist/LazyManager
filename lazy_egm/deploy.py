import paramiko
import threading
import argparse
from time import sleep
from pathlib import Path

ips = [i for i in range(2, 28)]
ips.remove(3)  # Exclude POS terminal

parser = argparse.ArgumentParser(description="Deploy files to EGM devices over SSH")
parser.add_argument('--ips', nargs='*', default=ips, help='List of IPs to deploy to')
args = parser.parse_args()

ips = [f'10.0.0.{i}' for i in args.ips]

SCHEDULE_TASK_COMMANDS = [
    'powershell.exe -Command "Set-Content -Path {cwd}\\lazy.bat -Value \'cd /d %~dp0 & {command}\'"',
    "schtasks /create /SC ONCE /TN {name} /TR {cwd}\\lazy.bat /ST 23:58",
    "schtasks /run /TN {name}",
    "schtasks /delete /TN {name} /F",
    "ping 127.0.0.1 -n 20",
    "del {cwd}\\lazy.bat"
]

exe_path_local = Path("./dist/LazyEGM.exe")
exe_path_remote = Path("D:/.lazy/LazyEGM.exe")

def start_task(ssh):
    command = " & ".join(SCHEDULE_TASK_COMMANDS).format(
        name="StartLazyEGM",
        cwd=r"D:\.lazy",
        command=r'LazyEGM.exe'
    )
    stdin, stdout, stderr = ssh.exec_command(command)
    stdout.channel.recv_exit_status()  # Wait for command to complete
    print("STDOUT:", stdout.read().decode())
    stderr_output = stderr.read().decode()
    if stderr_output:
        print("Error starting LazyEGM via scheduled task:", stderr_output)
        return

def deploy_to_egm(ip):
    try:
        print(f"Deploying to EGM at {ip}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username="Administrator", password="replay")

        stdin, stdout, stderr = ssh.exec_command(f'taskkill /F /IM LazyEGM.exe')
        stdout.channel.recv_exit_status()  # Wait for command to complete

        sftp = ssh.open_sftp()
        try:
            sftp.stat(str(exe_path_remote.parent))
        except FileNotFoundError:
            sftp.mkdir(str(exe_path_remote.parent))
        sftp.put(str(exe_path_local), str(exe_path_remote))
        sftp.chdir(str(exe_path_remote.parent))

        start_task(ssh)

        stdin, stdout, stderr = ssh.exec_command(f'taskkill /F /IM sftp-server.exe')
        sftp.close()
        ssh.close()
        print(f"Deployed to EGM at {ip}.")
    except TimeoutError:
        print(f"TimeoutError: Failed to connect to EGM at {ip}.")
    except EOFError:
        print(f"EOFError: Connection to EGM at {ip} was closed unexpectedly.")

threads = []
for ip in ips:
    thread = threading.Thread(target=deploy_to_egm, args=(ip,))
    thread.start()
    threads.append(thread)
    sleep(1)  # Stagger deployments slightly

for thread in threads:
    thread.join()