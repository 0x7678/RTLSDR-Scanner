import wx

from misc import format_device_name


class Device():
    def __init__(self):
        self.index = None
        self.name = None
        self.gain = 0
        self.calibration = None
        self.lo = None
        self.offset = 250e3


class Settings():
    def __init__(self):
        self.cfg = None
        self.start = None
        self.stop = None
        self.mode = 0
        self.dwell = 0.0
        self.nfft = 0
        self.calFreq = None
        self.yAuto = True
        self.yMax = 1
        self.yMin = 0
        self.devices = []
        self.index = None

        self.load()

    def load(self):
        self.cfg = wx.Config('rtlsdr-scanner')
        self.start = self.cfg.ReadInt('start', 87)
        self.stop = self.cfg.ReadInt('stop', 108)
        self.mode = self.cfg.ReadInt('mode', 0)
        self.dwell = self.cfg.ReadFloat('dwell', 0.1)
        self.nfft = int(self.cfg.Read('nfft', '1024'))
        self.calFreq = self.cfg.ReadFloat('calFreq', 1575.42)
        self.index = self.cfg.ReadInt('index', 0)
        self.cfg.SetPath("/Devices")
        group = self.cfg.GetFirstGroup()
        while group[0]:
            self.cfg.SetPath("/Devices/" + group[1])
            device = Device()
            device.name = group[1]
            device.gain = self.cfg.ReadFloat('gain', 0)
            device.calibration = self.cfg.ReadFloat('calibration', 0)
            device.lo = self.cfg.ReadFloat('lo', 0)
            device.offset = self.cfg.ReadFloat('offset', 250e3)
            self.devices.append(device)
            self.cfg.SetPath("/Devices")
            group = self.cfg.GetNextGroup(group[2])

    def save(self):
        self.cfg.SetPath("/")
        self.cfg.WriteInt('start', self.start)
        self.cfg.WriteInt('stop', self.stop)
        self.cfg.WriteInt('mode', self.mode)
        self.cfg.WriteFloat('dwell', self.dwell)
        self.cfg.Write('nfft', str(self.nfft))
        self.cfg.WriteFloat('calFreq', self.calFreq)
        self.cfg.WriteInt('index', self.index)
        if self.devices:
            for device in self.devices:
                self.cfg.SetPath("/Devices/" + format_device_name(device.name))
                self.cfg.WriteFloat('gain', device.gain)
                self.cfg.WriteFloat('lo', device.lo)
                self.cfg.WriteFloat('calibration', device.calibration)
                self.cfg.WriteFloat('offset', device.offset)
