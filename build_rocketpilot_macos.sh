#!/usr/bin/env bash

QT_VERSION="$1"

if [[ -z "$QT_VERSION" ]]; then
    echo "Qt version argument is missing"
    exit
fi
echo "Qt version: $QT_VERSION"

# Setup dependencies
which -s brew
if [[ $? != 0 ]] ; then
    # Install Homebrew if not found
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
fi

brew install python3 pkgconfig dbus dbus-glib
brew services start dbus

# Setup venv
python3 -m venv --system-site-packages $HOME/.venv
source $HOME/.venv/bin/activate
pip install -e .

# Build rocketpilot-driver
export PATH=$HOME/Qt/$QT_VERSION/clang_64/bin:$PATH
echo "PATH: $PATH"
rm /usr/local/bin/qmake
ln -s $HOME/Qt/$QT_VERSION/clang_64/bin/qmake /usr/local/bin/qmake


echo "Building xpathselect"
brew install boost
cd rocketpilot-driver/3rdparty/xpathselect
qmake
make clean
make -j4

echo "Building rocketpilot-driver"
cd ../..
qmake
make clean
make -j4

export DYLD_LIBRARY_PATH=$HOME/Qt/$QT_VERSION/clang_64/lib:$PWD
echo "DYLD_LIBRARY_PATH: $DYLD_LIBRARY_PATH"


echo "Building PyQt5"
pip install sip PyQt-builder PyQt5-sip

# Get PyQt5
cd $HOME
curl -O https://www.riverbankcomputing.com/static/Downloads/PyQt5/$QT_VERSION/PyQt5-$QT_VERSION.tar.gz -o PyQt5-$QT_VERSION.tar.gz
gunzip -c $HOME/PyQt5-$QT_VERSION.tar.gz | tar xopf -

# Get dbus-python
curl -O https://dbus.freedesktop.org/releases/dbus-python/dbus-python-1.2.16.tar.gz -o dbus-python-1.2.16.tar.gz
gunzip -c $HOME/dbus-python-1.2.16.tar.gz | tar xopf -

# Install PyQt5
cd $HOME/PyQt5-$QT_VERSION
echo yes | sip-install --dbus $HOME/dbus-python-1.2.16/include

cp $HOME/PyQt5-$QT_VERSION/build/dbus/pyqt5.abi3.so $HOME/.venv/lib/python3.7/site-packages/dbus/mainloop/
