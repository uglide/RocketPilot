# 🚀 RocketPilot

Cross-platform tool for functional GUI testing of Qt applications based on Canonical Autopilot project.

## Installation

### Ubuntu
```
sudo apt-get install python3 python3-pyqt5 -y
sudo apt-get install libxpathselect-dev -y
sudo apt-get install libdbus-1-dev libdbus-glib-1-dev -y

virtualenv --system-site-packages -p python3 .venv

source .venv/bin/activate

pip install -e . 
```

### macOS
> WARNING: Do NOT install Qt from brew, use the official Qt version instead (https://www.qt.io/download-open-source).

```
brew install python3 pkgconfig dbus dbus-glib
brew services start dbus

python3 -m venv --system-site-packages ~/.venv

source ~/.venv/bin/activate

pip install -e . 
```

### Windows
1. Install Python3, Qt5 (https://www.qt.io/download-open-source)
2. Install Msys2 to C:\msys64 & update core packages
3. Install dbus:
```
pacman -S mingw64/mingw-w64-x86_64-dbus
```
4. Update C:\msys64\mingw64\share\dbus-1\session.conf :
```
<listen>tcp:host=localhost,port=54321,family=ipv4</listen>
```
5. Add `C:\msys64\mingw64\bin` to PATH
6. Add `DBUS_SESSION_BUS_ADDRESS` env variable with value `tcp:host=localhost,port=54321,family=ipv4`
7. Run `dbus-daemon.exe --session`


## Introspect application
0. Build rocketpilot-driver https://github.com/uglide/rocketpilot-driver/blob/master/README.md


### Ubuntu and macOS
1. Install PyQt5
2. Run vis tool
    ```bash
    rocketpilot-vis APPNAME
    ```
