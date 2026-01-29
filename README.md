# 🖥️ PC Manager Server

#### Lighweight websockets server written in Python & Rust to get PC data to the PC Manager App

---

## How to run the server

#### 0. Make sure to have all the DLLs in /libs folder!

---

#### 1. Run CMD as ADMINISTRATOR (Required to access needed PC information)

---

#### 2. Go to the directory where the server is located

```
cd /Directory/To/The/Server
```

---

#### 3. Install the dependencies

```
pip install -r /libs/requirements.txt
```

---

#### 4. Run the server

```
py main.py
```

---

## Server features & status

<table>
  <tr>
    <td>Features</td>
    <td>Status</td>
    <td>Explanation</td>
  </tr>
  <tr>
    <td>PC Specs</td>
    <td>✅</td>
    <td>Ability to get PC specs like CPU & GPU name, total RAM, all disks available to use & OS info</td>
  </tr>
  <tr>
    <td>Hardware info</td>
    <td>🔨</td>
    <td>Information like CPU & GPU usage, temps etc. RAM usage/total & available disk space across all disks (AMD CPU & GPU ONLY FOR NOW)</td>
  </tr>
  <tr>
    <td>Game performance</td>
    <td>🔨</td>
    <td>Things like FPS of a game and frametimes. Possibly CPU & GPU wait times.</td>
  </tr>
  <tr>
    <td>PC Analyzer</td>
    <td>🔨</td>
    <td>Using AI to analyze your PC and its performance & game performance and figuring out if there is a problem with your PC or writing a self-made script for that</td>
  </tr>
  <tr>
    <td>Support for more hardware/OS's</td>
    <td>🔨</td>
    <td>Support for Intel CPU's aswell as NVidia & Intel GPU's (NVidia/Intel GPU's were not tested altough they might already be supported) & support for Linux.</td>
  </tr>
</table>
