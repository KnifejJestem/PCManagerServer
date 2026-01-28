# Import libraries

import json
import clr
import os
import platform
import asyncio
import websockets
import psutil

libs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")
dllpath = os.path.join(libs_dir, "LibreHardwareMonitorLib")

clr.AddReference(dllpath)

from LibreHardwareMonitor.Hardware import Computer  # type: ignore

c = Computer()

# Enable hardware monitoring

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


def find_hardware():
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
    # Get OS info
    osname = platform.system().strip()
    osver = platform.release().strip()

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

    return stats


async def stats_server(websocket):
    while True:
        stats = await asyncio.to_thread(get_stats)
        try:
            await websocket.send(json.dumps(stats))
        except Exception as e:
            if e == websockets.ConnectionClosedOK:
                pass
            else:
                print(f"Error sending stats: {e}")
            break
        except websockets.ConnectionClosed:
            break


async def main():
    async with websockets.serve(stats_server, "0.0.0.0", 8765, ping_interval=None):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
