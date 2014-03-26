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

import os
import sys
import time
import urllib

from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap
import wx

from constants import SAMPLE_RATE, TIMESTAMP_FILE


class ValidatorCoord(wx.PyValidator):
    def __init__(self, isLat):
        wx.PyValidator.__init__(self)
        self.isLat = isLat

    def Validate(self, _window):
        textCtrl = self.GetWindow()
        text = textCtrl.GetValue()
        if len(text) == 0 or text == '-' or text.lower() == 'unknown':
            textCtrl.SetForegroundColour("black")
            textCtrl.Refresh()
            return True

        value = None
        try:
            value = float(text)
            if self.isLat and (value < -90 or value > 90):
                raise ValueError()
            elif value < -180 or value > 180:
                raise ValueError()
        except ValueError:
            textCtrl.SetForegroundColour("red")
            textCtrl.SetFocus()
            textCtrl.Refresh()
            return False

        textCtrl.SetForegroundColour("black")
        textCtrl.Refresh()
        return True

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

    def Clone(self):
        return ValidatorCoord(self.isLat)


def next_2_to_pow(val):
    val -= 1
    val |= val >> 1
    val |= val >> 2
    val |= val >> 4
    val |= val >> 8
    val |= val >> 16
    return val + 1


def calc_samples(dwell):
    samples = dwell * SAMPLE_RATE
    samples = next_2_to_pow(int(samples))
    return samples


def calc_real_dwell(dwell):
    samples = calc_samples(dwell)
    dwellReal = samples / SAMPLE_RATE
    return (int)(dwellReal * 1000.0) / 1000.0


def nearest(value, values):
    offset = [abs(value - v) for v in values]
    return values[offset.index(min(offset))]


def format_time(timeStamp, withDate=False):
    if timeStamp <= 1:
        return 'Unknown'

    if withDate:
        return time.strftime('%c', time.localtime(timeStamp))

    return time.strftime('%H:%M:%S', time.localtime(timeStamp))


def load_bitmap(name):
    scriptDir = os.path.dirname(os.path.realpath(sys.argv[0]))
    if(os.path.isdir(scriptDir + '/res')):
        resDir = os.path.normpath(scriptDir + '/res')
    else:
        resDir = os.path.normpath(scriptDir + '/../res')

    return wx.Bitmap(resDir + '/' + name + '.png', wx.BITMAP_TYPE_PNG)


def add_colours():
    r = {'red':     ((0.0, 1.0, 1.0),
                     (1.0, 1.0, 1.0)),
         'green':   ((0.0, 0.0, 0.0),
                     (1.0, 0.0, 0.0)),
         'blue':   ((0.0, 0.0, 0.0),
                         (1.0, 0.0, 0.0))
        }
    g = {'red':     ((0.0, 0.0, 0.0),
                     (1.0, 0.0, 0.0)),
         'green':   ((0.0, 1.0, 1.0),
                     (1.0, 1.0, 1.0)),
         'blue':    ((0.0, 0.0, 0.0),
                     (1.0, 0.0, 0.0))
        }
    b = {'red':     ((0.0, 0.0, 0.0),
                     (1.0, 0.0, 0.0)),
         'green':   ((0.0, 0.0, 0.0),
                     (1.0, 0.0, 0.0)),
         'blue':    ((0.0, 1.0, 1.0),
                     (1.0, 1.0, 1.0))
        }

    rMap = LinearSegmentedColormap('red_map', r)
    gMap = LinearSegmentedColormap('red_map', g)
    bMap = LinearSegmentedColormap('red_map', b)
    cm.register_cmap(name=' Pure Red', cmap=rMap)
    cm.register_cmap(name=' Pure Green', cmap=gMap)
    cm.register_cmap(name=' Pure Blue', cmap=bMap)


def get_colours():
    colours = [colour for colour in cm.cmap_d]
    colours.sort()

    return colours


def set_version_timestamp():
    scriptDir = os.path.dirname(os.path.realpath(sys.argv[0]))
    timeStamp = str(int(time.time()))
    f = open(scriptDir + '/' + TIMESTAMP_FILE, 'w')
    f.write(timeStamp)
    f.close()


def get_version_timestamp(asSeconds=False):
    scriptDir = os.path.dirname(os.path.realpath(sys.argv[0]))
    f = open(scriptDir + '/' + TIMESTAMP_FILE, 'r')
    timeStamp = int(f.readline())
    f.close()
    if asSeconds:
        return timeStamp
    else:
        return format_time(timeStamp, True)


def get_version_timestamp_repo():
    f = urllib.urlopen('https://raw.github.com/EarToEarOak/RTLSDR-Scanner/master/src/version-timestamp')
    timeStamp = int(f.readline())
    f.close()
    return timeStamp


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)
