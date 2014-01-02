#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012 - 2014 Al Brown
#
# A frequency scanning GUI for the OsmoSDR rtl-sdr library at
# http://sdr.osmocom.org/trac/wiki/rtl-sdr
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import wx

from constants import Display, Mode
from devices import Device, format_device_name


class Settings():
    def __init__(self, load=True):
        self.cfg = None

        self.saveWarn = True
        self.fileHistory = wx.FileHistory(5)

        self.display = Display.PLOT

        self.annotate = True

        self.retainScans = True
        self.retainMax = 20
        self.fadeScans = True
        self.colourMap = 'jet'

        self.start = 87
        self.stop = 108
        self.mode = Mode.SINGLE
        self.dwell = 0.1
        self.nfft = 1024
        self.liveUpdate = False
        self.calFreq = 1575.42
        self.autoScale = True
        self.yMax = 20
        self.yMin = -60

        self.devices = []
        self.index = 0

        if load:
            self.load()

    def load(self):
        servers = 0
        self.cfg = wx.Config('rtlsdr-scanner')
        self.display = self.cfg.ReadInt('display', self.display)
        self.saveWarn = self.cfg.ReadBool('saveWarn', self.saveWarn)
        self.fileHistory.Load(self.cfg)
        self.annotate = self.cfg.ReadBool('annotate', self.annotate)
        self.retainScans = self.cfg.ReadBool('retainScans', self.retainScans)
        self.fadeScans = self.cfg.ReadBool('fadeScans', self.fadeScans)
        self.retainMax = self.cfg.ReadInt('retainMax', self.retainMax)
        self.colourMap = self.cfg.Read('colourMap', self.colourMap)
        self.start = self.cfg.ReadInt('start', self.start)
        self.stop = self.cfg.ReadInt('stop', self.stop)
        self.mode = self.cfg.ReadInt('mode', self.mode)
        self.dwell = self.cfg.ReadFloat('dwell', self.dwell)
        self.nfft = self.cfg.ReadInt('nfft', self.nfft)
        self.liveUpdate = self.cfg.ReadBool('liveUpdate', self.liveUpdate)
        self.calFreq = self.cfg.ReadFloat('calFreq', self.calFreq)
        self.autoScale = self.cfg.ReadBool('autoScale', self.autoScale)
        self.yMax = self.cfg.ReadInt('yMax', self.yMax)
        self.yMin = self.cfg.ReadInt('yMin', self.yMin)
        self.index = self.cfg.ReadInt('index', self.index)
        self.cfg.SetPath("/Devices")
        group = self.cfg.GetFirstGroup()
        while group[0]:
            self.cfg.SetPath("/Devices/" + group[1])
            device = Device()
            device.name = group[1]
            device.serial = self.cfg.Read('serial', '')
            device.isDevice = self.cfg.ReadBool('isDevice', True)
            if not device.isDevice:
                servers += 1
            device.server = self.cfg.Read('server', 'localhost')
            device.port = self.cfg.ReadInt('port', 1234)
            device.gain = self.cfg.ReadFloat('gain', 0)
            device.calibration = self.cfg.ReadFloat('calibration', 0)
            device.lo = self.cfg.ReadFloat('lo', 0)
            device.offset = self.cfg.ReadFloat('offset', 250e3)
            device.tuner = self.cfg.ReadInt('tuner', 0)
            self.devices.append(device)
            self.cfg.SetPath("/Devices")
            group = self.cfg.GetNextGroup(group[2])

        if servers == 0:
            device = Device()
            device.name = 'Server'
            device.isDevice = False
            device.server = 'localhost'
            device.port = 1234
            self.devices.append(device)

    def save(self):
        self.cfg.SetPath("/")
        self.cfg.WriteInt('display', self.display)
        self.cfg.WriteBool('saveWarn', self.saveWarn)
        self.fileHistory.Save(self.cfg)
        self.cfg.WriteBool('annotate', self.annotate)
        self.cfg.WriteBool('retainScans', self.retainScans)
        self.cfg.WriteBool('fadeScans', self.fadeScans)
        self.cfg.WriteInt('retainMax', self.retainMax)
        self.cfg.Write('colourMap', self.colourMap)
        self.cfg.WriteInt('start', self.start)
        self.cfg.WriteInt('stop', self.stop)
        self.cfg.WriteInt('mode', self.mode)
        self.cfg.WriteFloat('dwell', self.dwell)
        self.cfg.WriteInt('nfft', self.nfft)
        self.cfg.WriteBool('liveUpdate', self.liveUpdate)
        self.cfg.WriteFloat('calFreq', self.calFreq)
        self.cfg.WriteBool('autoScale', self.autoScale)
        self.cfg.WriteInt('yMax', self.yMax)
        self.cfg.WriteInt('yMin', self.yMin)
        self.cfg.WriteInt('index', self.index)
        if self.devices:
            for device in self.devices:
                self.cfg.SetPath("/Devices/" + format_device_name(device.name))
                self.cfg.Write('serial', device.serial)
                self.cfg.WriteBool('isDevice', device.isDevice)
                self.cfg.Write('server', device.server)
                self.cfg.WriteInt('port', device.port)
                self.cfg.WriteFloat('gain', device.gain)
                self.cfg.WriteFloat('lo', device.lo)
                self.cfg.WriteFloat('calibration', device.calibration)
                self.cfg.WriteFloat('offset', device.offset)
                self.cfg.WriteInt('tuner', device.tuner)


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)
