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

import Queue
import os
import sys
from threading import Thread
import threading
from urlparse import urlparse

from constants import SAMPLE_RATE
from devices import DeviceRTL, get_devices_rtl
from events import Event, post_event, EventThread
from file import save_plot, export_plot, ScanInfo, File
from misc import nearest, calc_real_dwell, next_2_to_pow
from scan import ThreadScan, anaylse_data, update_spectrum
from settings import Settings


class Cli(object):
    def __init__(self, pool, args):
        start = args.start
        end = args.end
        sweeps = args.sweeps
        gain = args.gain
        dwell = args.dwell
        nfft = args.fft
        lo = args.lo
        index = args.index
        remote = args.remote
        directory, filename = os.path.split(args.file)
        _null, ext = os.path.splitext(args.file)

        self.lock = threading.Lock()

        self.stepsTotal = 0
        self.steps = 0

        self.spectrum = {}
        self.settings = Settings(load=False)

        self.queue = Queue.Queue()

        error = None

        if end <= start:
            error = "Start should be lower than end"
        elif dwell <= 0:
            error = "Dwell should be positive"
        elif nfft <= 0:
            error = "FFT bins should be positive"
        elif ext != ".rfs" and File.get_type_index(ext) == -1:
            error = "File extension should be "
            error += File.get_type_pretty(File.Types.SAVE)
            error += File.get_type_pretty(File.Types.PLOT)
        else:
            device = DeviceRTL()
            if remote is None:
                self.settings.devicesRtl = get_devices_rtl()
                count = len(self.settings.devicesRtl)
                if index > count - 1:
                    error = "Device not found ({} devices in total):\n".format(count)
                    for device in self.settings.devicesRtl:
                        error += "\t{}: {}\n".format(device.indexRtl,
                                                       device.name)
            else:
                device.isDevice = False
                url = urlparse('//' + remote)
                if url.hostname is not None:
                    device.server = url.hostname
                else:
                    error = "Invalid hostname"
                if url.port is not None:
                    device.port = url.port
                else:
                    device.port = 1234
                self.settings.devicesRtl.append(device)
                index = len(self.settings.devicesRtl) - 1

        if error is not None:
            print "Error: {}".format(error)
            exit(1)

        if end - 1 < start:
            end = start + 1
        if remote is None:
            gain = nearest(gain, self.settings.devicesRtl[index].gains)

        self.settings.start = start
        self.settings.stop = end
        self.settings.dwell = calc_real_dwell(dwell)
        self.settings.nfft = nfft
        self.settings.devicesRtl[index].gain = gain
        self.settings.devicesRtl[index].lo = lo

        print "{} - {}MHz".format(start, end)
        print "{} Sweeps".format(sweeps)
        print "{}dB Gain".format(gain)
        print "{}s Dwell".format(self.settings.dwell)
        print "{} FFT points".format(nfft)
        print "{}MHz LO".format(lo)
        if remote is not None:
            print remote
        else:
            print self.settings.devicesRtl[index].name

        self.__scan(sweeps, self.settings, index, pool)

        fullName = os.path.join(directory, filename)
        if ext == ".rfs":
            scanInfo = ScanInfo()
            scanInfo.set_from_settings(self.settings)

            save_plot(fullName, scanInfo, self.spectrum, {})
        else:
            exportType = File.get_type_index(ext)
            export_plot(fullName, exportType, self.spectrum)

        print "Done"

    def __scan(self, sweeps, settings, index, pool):
        samples = settings.dwell * SAMPLE_RATE
        samples = next_2_to_pow(int(samples))
        for sweep in range(0, sweeps):
            print '\nSweep {}:'.format(sweep)
            threadScan = ThreadScan(self.queue, None, settings, index, samples,
                                    False)
            while threadScan.isAlive() or self.steps > 0:
                if not self.queue.empty():
                    self.__process_event(self.queue, pool)
            print ""
        print ""

    def __process_event(self, queue, pool):
        event = queue.get()
        status = event.data.get_status()
        freq = event.data.get_arg1()
        data = event.data.get_arg2()

        if status == Event.STARTING:
            print "Starting"
        elif status == Event.STEPS:
            self.stepsTotal = (freq + 1) * 2
            self.steps = self.stepsTotal
        elif status == Event.INFO:
            if data != -1:
                self.settings.devicesRtl[self.settings.indexRtl].tuner = data
        elif status == Event.DATA:
            cal = self.settings.devicesRtl[self.settings.indexRtl].calibration
            pool.apply_async(anaylse_data, (freq, data, cal,
                                            self.settings.nfft,
                                            self.settings.overlap,
                                            "Hamming"),
                             callback=self.__on_process_done)
            self.__progress()
        elif status == Event.ERROR:
            print "Error: {}".format(data)
            exit(1)
        elif status == Event.PROCESSED:
            offset = self.settings.devicesRtl[self.settings.indexRtl].offset
            Thread(target=update_spectrum, name='Update',
                   args=(queue, self.lock, self.settings.start,
                         self.settings.stop, freq,
                         data, offset, self.spectrum, False,)).start()
        elif status == Event.UPDATED:
            self.__progress()

    def __on_process_done(self, data):
        timeStamp, freq, scan = data
        post_event(self.queue, EventThread(Event.PROCESSED, freq,
                                           (timeStamp, scan)))

    def __progress(self):
        self.steps -= 1
        comp = (self.stepsTotal - self.steps) * 100 / self.stepsTotal
        sys.stdout.write("\r{0:.1f}%".format(comp))


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)
