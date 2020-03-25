# 🚀 RocketPilot

Cross-platform tool for functional GUI testing of Qt applications based on Canonical Autopilot project.

## Installation

### Ubuntu
```
sudo apt-get install python3 python3-pyqt5 python3-dbus.mainloop.pyqt5 -y
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
 
    brew install boost
    cd rocketpilot-driver/3rdparty/xpathselect
    qmake
    make -j4
 
    cd ../..
    qmake
    make -j4
 
    export DYLD_LIBRARY_PATH=~/Qt/5.14.1/clang_64/lib:~/RocketPilot/rocketpilot-driver
    ```

### Ubuntu
1. Install PyQt5
2. Run vis tool
    ```bash
    rocketpilot-vis APPNAME
    ```

### macOS
1. Build and install PyQt5 from source
    https://www.riverbankcomputing.com/static/Docs/PyQt5/installation.html#building-and-installing-from-source
    
    ```bash
    pip install sip PyQt-builder PyQt5-sip
    
    # Get PyQt5
    curl -O https://files.pythonhosted.org/packages/3a/fb/eb51731f2dc7c22d8e1a63ba88fb702727b324c6352183a32f27f73b8116/PyQt5-5.14.1.tar.gz -o ~/PyQt5-5.14.1.tar.gz
    gunzip -c ~/PyQt5-5.14.1.tar.gz | tar xopf -
    
    # Get dbus-python
    curl -O https://dbus.freedesktop.org/releases/dbus-python/dbus-python-1.2.16.tar.gz -o ~/dbus-python-1.2.16.tar.gz
    gunzip -c ~/dbus-python-1.2.16.tar.gz | tar xopf -
    
    # Install PyQt5
    cd ~/PyQt5-5.14.1
    sip-install --dbus ~/dbus-python-1.2.16/include
    
    cp ~/PyQt5-5.14.1/build/dbus/pyqt5.abi3.so ~/.venv/lib/python3.7/site-packages/dbus/mainloop/
    ```
    
    Up-to-date versions:
    
    - PyQt5 https://pypi.org/project/PyQt5/#files
    
    - dbus-python https://dbus.freedesktop.org/releases/dbus-python/

2. Run vis tool
    ```bash
    rocketpilot-vis APPNAME
    ```
