#
# rtlsdr_scan
#
# http://eartoearoak.com/software/rtlsdr-scanner
#
# Copyright 2012, 2013 Al Brown
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


EVENT_STARTING = 0
EVENT_SCAN = 1
EVENT_DATA = 2
EVENT_FINISHED = 3
EVENT_STOPPED = 4
EVENT_ERROR = 5
EVENT_PLOTTED = 6

EVT_THREAD_STATUS = wx.NewId()


class Status():
    def __init__(self, status, freq, data):
        self.status = status
        self.freq = freq
        self.data = data

    def get_status(self):
        return self.status

    def get_freq(self):
        return self.freq

    def get_data(self):
        return self.data


class EventThreadStatus(wx.PyEvent):
    def __init__(self, status, freq=None, data=None):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_THREAD_STATUS)
        self.data = Status(status, freq, data)


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)
