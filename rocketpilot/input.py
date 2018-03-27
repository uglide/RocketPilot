import logging

from pymouse import PyMouse


_logger = logging.getLogger(__name__)


class Mouse(PyMouse):

    def click_object(self, object_proxy, button=1, n=1,
                     offset_x=None, offset_y=None):
        """Click the center point of a given object.

        It does this by looking for several attributes, in order. The first
        attribute found will be used. The attributes used are (in order):

         * globalRect (x,y,w,h)
         * center_x, center_y
         * x, y, w, h

         """
        x, y = get_center_point(
            object_proxy,
            offset_x=offset_x,
            offset_y=offset_y
        )
        self.click(int(x), int(y), button=button, n=n)

    def move_to_object(self, object_proxy):
        """Attempts to move the mouse to 'object_proxy's centre point.

        It does this by looking for several attributes, in order. The first
        attribute found will be used. The attributes used are (in order):

         * globalRect (x,y,w,h)
         * center_x, center_y
         * x, y, w, h

        :raises: **ValueError** if none of these attributes are found, or if an
         attribute is of an incorrect type.

        """
        x, y = get_center_point(object_proxy)
        self.move(int(x), int(y))


def get_center_point(object_proxy, offset_x=None, offset_y=None):
    """Get the center point of an object.

    It searches for several different ways of determining exactly where the
    center is. The attributes used are (in order):

     * globalRect (x,y,w,h)
     * center_x, center_y
     * x, y, w, h

    :raises ValueError: if `object_proxy` has the globalRect attribute but it
        is not of the correct type.
    :raises ValueError: if `object_proxy` doesn't have the globalRect
        attribute, it has the x and y attributes instead, but they are not of
        the correct type.
    :raises ValueError: if `object_proxy` doesn't have any recognised position
        attributes.

    """

    def get_offsets(w, h):
        return offset_x or w//2, offset_y or h//2

    try:
        x, y, w, h = object_proxy.globalRect
        _logger.debug("Moving to object's globalRect coordinates.")
        o_x, o_y = get_offsets(w, h)
        return x + o_x, y + o_y
    except AttributeError:
        pass
    except (TypeError, ValueError):
        raise ValueError(
            "Object '%r' has globalRect attribute, but it is not of the "
            "correct type" % object_proxy)

    try:
        x, y = object_proxy.center_x, object_proxy.center_y
        _logger.debug("Moving to object's center_x, center_y coordinates.")
        return x, y
    except AttributeError:
        pass

    try:
        x, y, w, h = (
            object_proxy.x, object_proxy.y, object_proxy.width, object_proxy.height)
        _logger.debug(
            "Moving to object's center point calculated from x,y,w,h "
            "attributes.")
        o_x, o_y = get_offsets(w, h)
        return x + o_x, y + o_y
    except AttributeError:
        raise ValueError(
            "Object '%r' does not have any recognised position attributes" %
            object_proxy)
    except (TypeError, ValueError):
        raise ValueError(
            "Object '%r' has x,y attribute, but they are not of the correct "
            "type" % object_proxy)
