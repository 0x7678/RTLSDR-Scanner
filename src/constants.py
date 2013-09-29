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

F_MIN = 0
F_MAX = 9999
GAIN = 0
SAMPLE_RATE = 2e6
BANDWIDTH = 500e3


class Warn:
    SCAN, OPEN, EXIT = range(3)


class Cal:
    START, DONE, OK, CANCEL = range(4)


class Mode:
    SINGLE, CONTIN = range(2)


class Plot:
    NONE, PARTIAL, FULL = range(3)
    STR_FULL = 'Full'
    STR_PARTIAL = 'Partial'


class File:
    RFS = "RTLSDR frequency scan (*.rfs)|*.rfs"
    CSV = "CSV table (*.csv)|*.csv"
    HEADER = "RTLSDR Scanner"
    VERSION = 1


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)
