import time

from pykeyboard import PyKeyboard

from rocketpilot.introspection import ProxyBase
from rocketpilot.input import Mouse
from rocketpilot.exceptions import StateNotFoundError

mouse_obj = Mouse()
keyboard_obj = PyKeyboard()


class ApplicationItemProxy(ProxyBase):

    def __init__(self, state_dict, path, backend):
        super().__init__(state_dict, path, backend)

        self.mouse = mouse_obj
        self.keyboard = keyboard_obj

    def click(self, **kwargs):
        self.mouse.move_to_object(self)
        self.mouse.click_object(self, **kwargs)

    def send_text(self, text, clicks_to_focus=1,
                  focus_delay=0.1, input_delay=0.05):

        self.click(n=clicks_to_focus)
        time.sleep(focus_delay)
        self.keyboard.type_string(text, interval=input_delay)

    def wait_object_chain(self, object_names):
        current_item = self

        while len(object_names):
            obj_name = object_names.pop(0)

            current_item = current_item.wait_select_single(
                objectName=obj_name
            )

        return current_item

    def wait_object(self, objectName):
        return self.wait_select_single(objectName=objectName)

    def wait_select_any(self, type_name, filter_groups, ap_query_timeout=5,
                        delay=1):
        if ap_query_timeout <= 0:
            ap_query_timeout = 1
            delay = 0

        for i in range(ap_query_timeout):
            for filters in filter_groups:
                try:
                    return self._select_single(type_name, **filters)
                except StateNotFoundError:
                    continue

            time.sleep(delay)
            self.refresh_state()

        raise StateNotFoundError(type_name)
