import logging

from pymouse import PyMouse


_logger = logging.getLogger(__name__)


class Mouse(PyMouse):

    def click_object(self, object_proxy, button=1, n=1):
        """Click the center point of a given object.

        It does this by looking for several attributes, in order. The first
        attribute found will be used. The attributes used are (in order):

         * globalRect (x,y,w,h)
         * center_x, center_y
         * x, y, w, h

         """
        x, y = get_center_point(object_proxy)
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


def get_center_point(object_proxy):
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
    try:
        x, y, w, h = object_proxy.globalRect
        _logger.debug("Moving to object's globalRect coordinates.")
        return x + w//2, y + h//2
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
        return x + w//2, y + h//2
    except AttributeError:
        raise ValueError(
            "Object '%r' does not have any recognised position attributes" %
            object_proxy)
    except (TypeError, ValueError):
        raise ValueError(
            "Object '%r' has x,y attribute, but they are not of the correct "
            "type" % object_proxy)
