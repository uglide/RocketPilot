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
### OS X

```
brew install python3 pkgconfig dbus dbus-glib
brew services start dbus

virtualenv --system-site-packages -p python3 .venv

source .venv/bin/activate

pip install -e . 
```
