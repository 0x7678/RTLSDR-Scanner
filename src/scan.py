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

import itertools
import math
import threading
import time

import matplotlib
import rtlsdr

from constants import WINFUNC
from events import EventThreadStatus, Event, post_event
import rtltcp


class ThreadScan(threading.Thread):
    def __init__(self, notify, sdr, settings, device, samples, isCal):
        threading.Thread.__init__(self)
        self.name = 'Scan'
        self.notify = notify
        self.sdr = sdr
        self.fstart = settings.start * 1e6
        self.fstop = settings.stop * 1e6
        self.samples = samples
        self.isCal = isCal
        self.index = settings.index
        self.isDevice = settings.devices[device].isDevice
        self.server = settings.devices[device].server
        self.port = settings.devices[device].port
        self.gain = settings.devices[device].gain
        self.lo = settings.devices[device].lo * 1e6
        self.rate = settings.devices[device].rate
        self.bandwidth = settings.devices[device].bandwidth
        self.offset = settings.devices[device].offset
        self.cancel = False

        post_event(self.notify, EventThreadStatus(Event.STARTING))
        steps = int((self.f_stop() - self.f_start()) / self.f_step())
        post_event(self.notify, EventThreadStatus(Event.STEPS, steps))
        self.start()

    def f_start(self):
        return self.fstart - self.offset - self.bandwidth

    def f_stop(self):
        return self.fstop + self.offset + self.bandwidth * 2

    def f_step(self):
        return self.bandwidth / 2

    def run(self):
        tuner = self.rtl_setup()
        if self.sdr is None:
            return
        post_event(self.notify, EventThreadStatus(Event.INFO, None, tuner))

        freq = self.f_start()
        timeStamp = time.time()
        while freq <= self.f_stop():
            if self.cancel:
                post_event(self.notify,
                           EventThreadStatus(Event.STOPPED))
                self.rtl_close()
                return
            try:
                scan = self.rtl_scan(freq)
                post_event(self.notify,
                           EventThreadStatus(Event.DATA, freq,
                                            (timeStamp, scan)))
            except IOError:
                if self.sdr is not None:
                    self.rtl_close()
                self.rtl_setup()
            except (TypeError, AttributeError) as error:
                if self.notify:
                    post_event(self.notify,
                               EventThreadStatus(Event.ERROR,
                                                 0, error.message))
                return
            except WindowsError:
                if self.sdr is not None:
                    self.rtl_close()

            freq += self.f_step()

        post_event(self.notify, EventThreadStatus(Event.FINISHED, 0, None))

        if self.isCal:
            post_event(self.notify, EventThreadStatus(Event.CAL))

    def abort(self):
        self.cancel = True

    def rtl_setup(self):

        if self.sdr is not None:
            return

        tuner = 0

        if self.isDevice:
            try:
                self.sdr = rtlsdr.RtlSdr(self.index)
                self.sdr.set_sample_rate(self.rate)
                self.sdr.set_manual_gain_enabled(1)
                self.sdr.set_gain(self.gain)
                tuner = self.sdr.get_tuner_type()
            except IOError as error:
                post_event(self.notify, EventThreadStatus(Event.ERROR,
                                                          0, error.message))
        else:
            try:
                self.sdr = rtltcp.RtlTcp(self.server, self.port)
                self.sdr.set_sample_rate(self.rate)
                self.sdr.set_manual_gain_enabled(1)
                self.sdr.set_gain(self.gain)
                tuner = self.sdr.get_tuner_type()
            except IOError as error:
                post_event(self.notify, EventThreadStatus(Event.ERROR,
                                                          0, error))

        return tuner

    def rtl_scan(self, freq):
        self.sdr.set_center_freq(freq + self.lo)
        capture = self.sdr.read_samples(self.samples)

        return capture

    def rtl_close(self):
        self.sdr.close()

    def get_sdr(self):
        return self.sdr


def anaylse_data(freq, data, cal, nfft, rate, winFunc):
    spectrum = {}
    timeStamp = data[0]
    samples = data[1]
    pos = WINFUNC[::2].index(winFunc)
    function = WINFUNC[1::2][pos]
    powers, freqs = matplotlib.mlab.psd(samples,
                     NFFT=nfft,
                     Fs=rate / 1e6,
                     window=function(nfft))
    for freqPsd, pwr in itertools.izip(freqs, powers):
        xr = freqPsd + (freq / 1e6)
        xr = xr + (xr * cal / 1e6)
        spectrum[xr] = pwr

    return (timeStamp, freq, spectrum)


def update_spectrum(notify, lock, start, stop, freqCentre, data, bandwidth,
                    offset, spectrum, average, alertLevel=None):
    with lock:
        updated = False
        if average:
            timeStamp = 0
        else:
            timeStamp = data[0]
        scan = data[1]

        upperStart = freqCentre + offset
        upperEnd = freqCentre + offset + bandwidth / 2
        lowerStart = freqCentre - offset - bandwidth / 2
        lowerEnd = freqCentre - offset

        if not timeStamp in spectrum:
            spectrum[timeStamp] = {}

        for freq in scan:
            if start <= freq < stop:
                power = 10 * math.log10(scan[freq])
                if upperStart <= freq * 1e6 <= upperEnd or \
                   lowerStart <= freq * 1e6 <= lowerEnd:
                    if freq in spectrum[timeStamp]:
                        spectrum[timeStamp][freq] = \
                            (spectrum[timeStamp][freq] + power) / 2
                        if alertLevel is not None and \
                        spectrum[timeStamp][freq] > alertLevel:
                            post_event(notify, EventThreadStatus(Event.LEVEL))
                        updated = True
                    else:
                        spectrum[timeStamp][freq] = power
                        updated = True

    post_event(notify, EventThreadStatus(Event.UPDATED, None, updated))


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)
