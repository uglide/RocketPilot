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

## Introspect application
0. Build rocketpilot-driver
    
    ### macOS
    ```bash
    export PATH=~/Qt/5.14.1/clang_64/bin:$PATH
    ln -s ~/Qt/5.14.1/clang_64/bin/qmake /usr/local/bin/qmake
    cd rocketpilot-driver
    qmake
    make -j4
 
    export DYLD_LIBRARY_PATH=~/Qt/5.14.1/clang_64/lib:~/RocketPilot/rocketpilot-driver

    brew install boost
    cd 3rdparty/xpathselect
    qmake
    make -j4
    ```

### Ubuntu and macOS
1. Install PyQt5
2. Run vis tool
    ```bash
    rocketpilot-vis APPNAME
    ```
