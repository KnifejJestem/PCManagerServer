# Import libraries

import asyncio
import json
import os
import platform

import psutil
import websockets
import psutil
import urllib.request
import threading
import time

os.environ["AMDSMI_GPU_METRICS_CACHE_MS"] = "200"
from amdsmi import *  # type: ignore

# Get OS info

osname = platform.system().strip()
osver = platform.release().strip()

IS_WINDOWS = "windows" in osname.lower()

if IS_WINDOWS:
    import clr

    libs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")
    dllpath = os.path.join(libs_dir, "LibreHardwareMonitorLib")

    clr.AddReference(dllpath)  # type: ignore
    from LibreHardwareMonitor.Hardware import Computer  # type: ignore

    c = Computer()
    # Enable hardware monitoring for Windows
    c.IsCpuEnabled = True
    c.IsGpuEnabled = True
    c.IsMemoryEnabled = True
    c.IsStorageEnabled = False
    c.IsMotherboardEnabled = False
    c.Open()

benchmark_start = False

cpu_hw = None
gpu_hw = None
ram_hw = None

def check_and_download_presentmon():
    url = "https://github.com/GameTechDev/PresentMon/releases/download/v2.4.1/PresentMon-2.4.1-x64.exe"
    presentmon_path = os.path.join(libs_dir, "PresentMon-2.4.1-x64.exe")
    if not os.path.exists(presentmon_path):
        print("Downloading PresentMon...")
        urllib.request.urlretrieve(url, presentmon_path)
        return False
    else:
        return True
    
check_and_download_presentmon()

def find_hardware():
    if IS_WINDOWS:
        global cpu_hw, gpu_hw, ram_hw
        for hw in c.Hardware:
            hw_type = str(hw.HardwareType)
            if hw_type == "Cpu":
                cpu_hw = hw
            elif "Gpu" in hw_type:
                gpu_hw = hw


find_hardware()

disks = psutil.disk_partitions()


def get_stats():
    global stats
    if IS_WINDOWS:
        if cpu_hw is None or gpu_hw is None or ram_hw is None:
            find_hardware()
        if cpu_hw:
            cpu_hw.Update()
        if gpu_hw:
            gpu_hw.Update()

        stats = {
            "cpu": {
                "name": "",
                "usage": 0.0,
                "temperature": 0.0,
                "voltage": 0.0,
                "power": 0.0,
                "clock_speed": 0.0,
            },
            "gpu": {
                "name": "",
                "usage": 0.0,
                "temperature": 0.0,
                "memory_used": 0.0,
                "memory_total": 0.0,
                "power": 0.0,
            },
            "ram": {"total": 0, "used": 0},
            "os": {"name": osname, "version": osver},
            "disks": [],
            "benchmarking": {
                "fps": 0,
                "min_fps": 0,
                "max_fps": 0,
                "frametimes": 0.0,
                "is_running": False,
            },
        }

        for hw in c.Hardware:
            hw.Update()
            hw_type = str(hw.HardwareType)

            # Get CPU stats
            if hw_type == "Cpu":
                stats["cpu"]["name"] = hw.Name
                for sensor in hw.Sensors:
                    s_type = str(sensor.SensorType)
                    s_name = sensor.Name
                    # print(f"Sensor: {sensor.Name}, Type: {sensor.SensorType}, Value: {sensor.Value}") # For debugging purposes

                    # Usage

                    if s_type == "Load" and "Total" in s_name:
                        stats["cpu"]["usage"] = round(float(sensor.Value or 0), 1)

                    # Temperature

                    elif s_type == "Temperature" and "Core (Tctl/Tdie)" in s_name:
                        stats["cpu"]["temperature"] = round(float(sensor.Value or 0), 1)

                    # Clock Speed

                    elif s_type == "Clock" and "Cores (Average)" in s_name:
                        stats["cpu"]["clock_speed"] = round(float(sensor.Value or 0), 1)

                    # Voltage

                    elif s_type == "Voltage" and "Core" in s_name:
                        stats["cpu"]["voltage"] = round(float(sensor.Value or 0), 2)

                    # Power

                    elif s_type == "Power" and "Package" in s_name:
                        stats["cpu"]["power"] = round(float(sensor.Value or 0), 1)

            # Get GPU usage and temps
            elif "Gpu" in hw_type:
                stats["gpu"]["name"] = hw.Name
                for sensor in hw.Sensors:
                    s_type = str(sensor.SensorType)
                    # print(f"GPU Sensor: {sensor.Name}, Type: {sensor.SensorType}, Value: {sensor.Value}") # For debugging purposes

                    # Usage

                    if s_type == "Load" and "Core" in sensor.Name:
                        stats["gpu"]["usage"] = round(sensor.Value, 1)

                    # Temperature

                    elif s_type == "Temperature" and "Core" in sensor.Name:
                        stats["gpu"]["temperature"] = round(sensor.Value, 1)

                    # Power

                    elif s_type == "Power" and "GPU Package" in sensor.Name:
                        stats["gpu"]["power"] = round(sensor.Value, 1)

                    # Memory Used

                    if s_type == "SmallData" and "GPU Memory Used" in sensor.Name:
                        stats["gpu"]["memory_used"] = round(sensor.Value, 2)

                    # Memory Total

                    elif s_type == "SmallData" and "GPU Memory Total" in sensor.Name:
                        stats["gpu"]["memory_total"] = round(sensor.Value, 2)

            # Get RAM usage and total
            elif hw_type == "Memory":
                for sensor in hw.Sensors:
                    s_type = str(sensor.SensorType)
                    if s_type == "Data":
                        if "Used" in sensor.Name:
                            stats["ram"]["used"] = round(sensor.Value, 2)

                        elif "Available" in sensor.Name:
                            stats["ram"]["total"] = round(
                                stats["ram"]["used"] + sensor.Value, 2
                            )

            # Get Disk space usage and total
            stats["disks"] = []
            for disk in disks:
                # Check if the disk is a CD-ROM or has no file system (to avoid errors on Windows)

                if os.name == "nt":
                    if "cdrom" in disk.opts or disk.fstype == "":
                        continue

                # Get disk usage

                usage = psutil.disk_usage(disk.mountpoint)

                # Add disk info to stats

                stats["disks"].append(
                    {
                        "number": len(stats["disks"]) + 1,
                        "name": os.path.basename(disk.device),
                        "device": disk.device,
                        "mountpoint": disk.mountpoint,
                        "fstype": disk.fstype,
                        "total": round(usage.total / (1024**3), 2),
                        "used": round(usage.used / (1024**3), 2),
                        "free": round(usage.free / (1024**3), 2),
                        "percent": usage.percent,
                    }
                )
    if not IS_WINDOWS:
        stats = {
            "cpu": {
                "name": "",
                "usage": 0.0,
                "temperature": 0.0,
                "voltage": 0.0,
                "power": 0.0,
                "clock_speed": 0.0,
            },
            "gpu": {
                "name": "",
                "usage": 0.0,
                "temperature": 0.0,
                "memory_used": 0.0,
                "memory_total": 0.0,
                "power": 0.0,
            },
            "ram": {"total": 0, "used": 0},
            "os": {"name": osname, "version": osver},
            "disks": [],
            "benchmarking": {
                "fps": 0,
                "min_fps": 0,
                "max_fps": 0,
                "frametimes": 0.0,
                "is_running": False,
            },
        }

        # Get GPU stats
        try:
            ret = amdsmi_init(AmdSmiInitFlags.INIT_AMD_APUS)
            devices = amdsmi_get_processor_handles()
            if len(devices) == 0:
                print("No GPUs on machine")
            else:
                for device in devices:
                    # GPU Stats

                    asic_info = amdsmi_get_gpu_asic_info(device)
                    stats["gpu"]["name"] = asic_info["market_name"]

                    engine_usage = amdsmi_get_gpu_activity(device)
                    stats["gpu"]["usage"] = engine_usage["gfx_activity"]

                    vram_memory_total = round(
                        int(
                            amdsmi_get_gpu_memory_total(
                                device, amdsmi_interface.AmdSmiMemoryType.VRAM
                            )
                        )
                        / 1024**3,
                        2,
                    )

                    stats["gpu"]["memory_total"] = vram_memory_total
                    vram_memory_usage = round(
                        int(
                            amdsmi_get_gpu_memory_usage(
                                device, amdsmi_interface.AmdSmiMemoryType.VRAM
                            )
                        )
                        / 1024**3,
                        2,
                    )

                    stats["gpu"]["memory_used"] = vram_memory_usage
                    temp_metric = amdsmi_get_temp_metric(
                        device,
                        AmdSmiTemperatureType.EDGE,
                        AmdSmiTemperatureMetric.CURRENT,
                    )
                    stats["gpu"]["temperature"] = temp_metric

                    power_info = amdsmi_get_power_info(device)
                    stats["gpu"]["power"] = power_info["socket_power"]

                    # CPU Stats

                    cpu_name = amdsmi_get_cpu_model_name(device)
                    stats["cpu"]["name"] = cpu_name.lstrip("b'").rstrip("'")
        except AmdSmiException as e:
            print(e)

    return stats
async def get_benchmark_stats(process):
    print("getbechstats running")
    global lines
    global parts
    lines = []
    new_data_found = False
    try:
        while True:
            try:
                line_raw = await asyncio.wait_for(process.stdout.readline(), timeout=0.02)
                if not line_raw:
                    break
                line = line_raw.decode().strip()
                parts = line.split(",")
                if parts:
                    new_data_found = True
                    # 1'Application',
                    # 2'ProcessID', 
                    # 3'SwapChainAddress', 
                    # 4'PresentRuntime', 
                    # 5'SyncInterval',
                    # 6'PresentFlags', 
                    # 7'AllowsTearing', 
                    # 8'PresentMode', 
                    # 9'CPUStartTime', 
                    # 10'FrameTime', 
                    # 11'CPUBusy',
                    # 12'CPUWait', 
                    # 13'GPULatency', 
                    # 14'GPUTime', 
                    # 15'GPUBusy', 
                    # 16'GPUWait', 
                    # 17'DisplayLatency',
                    # 18'DisplayedTime', 
                    # 19'AnimationError', 
                    # 20'AnimationTime',
                    # 21'MsFlipDelay', 
                    # 22'AllInputToPhotonLatency',
                    # 23'ClickToPhotonLatency'

            except asyncio.TimeoutError:
                continue
        if not new_data_found:
            pass
    except Exception as e:
        print(f"Error getting benchmark stats: {e}")

async def get_app_stats(app: str):
    if not app:
        print("Didnt specify an app!")
    if app and app.lower() in parts[0].lower():
        fps = round(1000 / float(parts[10]), 2)
        frametime = round(float(parts[10]), 2)
        stats["benchmarking"]["fps"] = fps
        stats["benchmarking"]["frametime"] = frametime



async def stats_server(websocket):
    cmd = [os.path.join(libs_dir, "PresentMon-2.4.1-x64.exe"), "--output_stdout", "--no_console_stats", "--v2_metrics"]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    print("starting getbenchstats")
    benchmark_start = asyncio.create_task(get_benchmark_stats(process))
    while True:
        try:
            await websocket.send(json.dumps(stats))
            print(f"\n -------------------------\n Sent stats: {stats} \n -------------------------\n")
            await asyncio.sleep(1)
            recv = await websocket.recv()
            if "app" in recv:
                app = str(recv.split(",")[1].strip())
                stats["benchmarking"]["is_running"] = True
                print(f"\n -------------------------\n {await get_app_stats(app)} \n -------------------------\n")
            if not app:
                stats["benchmarking"]["is_running"] = False
        except Exception as e:
            if e == websockets.ConnectionClosedOK:
                pass
            else:
                print(f"Error sending stats: {e}")
            break


async def main():
    print("Starting WebSocket server on ws://0.0.0.0:8765")
    async with websockets.serve(stats_server, "0.0.0.0", 8765, ping_interval=None):
        await asyncio.Future()


if __name__ == "__main__":
    c.Open()
    threading.Thread(target=get_stats, daemon=True).start()
    print("Starting getstats")
    asyncio.run(main())