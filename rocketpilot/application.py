from pykeyboard import PyKeyboard

from rocketpilot.introspection import ProxyBase
from rocketpilot.input import Mouse

mouse_obj = Mouse()
keyboard_obj = PyKeyboard()


class ApplicationProxy(ProxyBase):

    def __init__(self, state_dict, path, backend):
        super().__init__(state_dict, path, backend)

        self.mouse = mouse_obj
        self.keyboard = keyboard_obj