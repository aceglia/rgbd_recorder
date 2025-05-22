from enum import Enum

class DataType(Enum):
    RGBD = 'rgbd'
    TRIGGER = 'trigger'
    DELSYS = 'delsys'


class DisplayType(Enum):
    IMAGE = 'image'
    CURVE = 'curve'


class DelsysType(Enum):
    Emg = "emg"
    Gogniometer = "gogniometer"


class ImageResolution(Enum):
    """
    The different types of image resolutions that can be used.
    """
    R_424x240 = (424, 240)
    R_480x270 = (480, 270)
    R_640x360 = (640, 360)
    R_640x480 = (640, 480)
    R_848x480 = (848, 480)
    R_1280x720 = (1280, 720)
    R_1280x800 = (1280, 800)

    @classmethod
    def list(cls):
        return list(map(lambda c: str(c.value[0]) + 'x' + str(c.value[1]), cls))