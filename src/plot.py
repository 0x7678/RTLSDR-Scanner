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
import os
import threading

from matplotlib import patheffects
import matplotlib
from matplotlib.ticker import ScalarFormatter, AutoMinorLocator
import numpy

from events import EventThreadStatus, Event, post_event
from misc import split_spectrum


class Plotter():
    def __init__(self, notify, graph, settings, grid, lock):
        self.notify = notify
        self.settings = settings
        self.graph = graph
        self.average = settings.average
        self.lock = lock
        self.figure = self.graph.get_figure()
        self.axes = None
        self.threadPlot = None
        self.setup_plot()
        self.set_grid(grid)

    def setup_plot(self):
        self.axes = self.figure.add_subplot(111)

        formatter = ScalarFormatter(useOffset=False)

        self.axes.set_xlabel("Frequency (MHz)")
        self.axes.set_ylabel('Level (dB)')
        self.axes.xaxis.set_major_formatter(formatter)
        self.axes.yaxis.set_major_formatter(formatter)
        self.axes.xaxis.set_minor_locator(AutoMinorLocator(10))
        self.axes.yaxis.set_minor_locator(AutoMinorLocator(10))
        self.axes.set_xlim(self.settings.start, self.settings.stop)
        self.axes.set_ylim(-50, 0)

    def scale_plot(self, force=False):
        if self.figure is not None:
            with self.lock:
                self.axes.set_xlim(auto=self.settings.autoF or force)
                self.axes.set_ylim(auto=self.settings.autoL or force)
                self.axes.relim()

    def redraw_plot(self):
        if self.figure is not None:
            if os.name == "nt":
                threading.Thread(target=self.thread_draw, name='Draw').start()
            else:
                post_event(self.notify, EventThreadStatus(Event.DRAW))

    def set_title(self, title):
        self.axes.set_title(title)

    def set_plot(self, data, annotate=False):
        if self.threadPlot is not None and self.threadPlot.isAlive():
            self.threadPlot.cancel()
            self.threadPlot.join()

        self.threadPlot = ThreadPlot(self, self.lock, self.axes,
                                     data, self.settings.fadeScans,
                                     annotate, self.settings.average).start()

    def clear_plots(self):
        children = self.axes.get_children()
        for child in children:
            if child.get_gid() is not None:
                if child.get_gid() == "plot" or child.get_gid() == "peak":
                    child.remove()

    def set_grid(self, on):
        self.axes.grid(on)
        self.redraw_plot()

    def close(self):
        self.figure.clear()
        self.figure = None

    def thread_draw(self):
        with self.lock:
            if self.figure is not None:
                try:
                    self.graph.get_figure().tight_layout()
                    self.graph.get_canvas().draw()
                except:
                    pass


class ThreadPlot(threading.Thread):
    def __init__(self, parent, lock, axes, data, fade, annotate, average):
        threading.Thread.__init__(self)
        self.name = "Plot"
        self.parent = parent
        self.lock = lock
        self.axes = axes
        self.data = data
        self.annotate = annotate
        self.fade = fade
        self.average = average
        self.abort = False

    def run(self):
        with self.lock:
            if self.abort:
                return
            total = len(self.data)
            if total > 0:
                self.parent.clear_plots()
                if self.average:
                    avg = {}
                    count = len(self.data)
                    length = len(self.data[(sorted(self.data))[0]])
                    for timeStamp in sorted(self.data):
                        if self.abort:
                            return
                        xs, ys = split_spectrum(self.data[timeStamp])
                        if len(xs) < length:
                            continue
                        for x, y in itertools.izip_longest(xs, ys):
                            if x in avg:
                                avg[x] = avg[x] + y / count
                            else:
                                avg[x] = y / count
                    xs, ys = split_spectrum(avg)
                    self.axes.plot(xs, ys, linewidth=0.4, gid="plot",
                                   color='b')
                else:
                    count = 1.0
                    for timeStamp in sorted(self.data):
                        if self.abort:
                            return
                        xs, ys = split_spectrum(self.data[timeStamp])
                        if self.fade:
                            alpha = count / total
                        else:
                            alpha = 1
                        self.axes.plot(xs, ys, linewidth=0.4, gid="plot",
                                       color='b', alpha=alpha)
                        count += 1

                if self.annotate:
                    self.annotate_plot()

        if total > 0:
            self.parent.scale_plot()
            self.parent.redraw_plot()

    def annotate_plot(self):
        self.clear_markers()

        plots = self.get_plots()
        if len(plots) == 1:
            plot = plots[0]
        else:
            plot = plots[len(plots) - 2]
        xData, yData = plot.get_data()
        if len(yData) == 0:
            return
        pos = numpy.argmax(yData)
        x = xData[pos]
        y = yData[pos]

        start, stop = self.axes.get_xlim()
        textX = ((stop - start) / 50.0) + x

        if(matplotlib.__version__ < '1.3'):
            self.axes.annotate('{0:.6f}MHz\n{1:.2f}dB'.format(x, y),
                               xy=(x, y), xytext=(textX, y),
                               ha='left', va='top', size='small',
                               gid='peak')
            self.axes.plot(x, y, marker='x', markersize=10, color='w',
                           mew=3, gid='peak')
            self.axes.plot(x, y, marker='x', markersize=10, color='r',
                           gid='peak')
        else:
            effect = patheffects.withStroke(linewidth=3, foreground="w",
                                            alpha=0.75)
            self.axes.annotate('{0:.6f}MHz\n{1:.2f}dB'.format(x, y),
                               xy=(x, y), xytext=(textX, y),
                               ha='left', va='top', size='small',
                               path_effects=[effect], gid='peak')
            self.axes.plot(x, y, marker='x', markersize=10, color='r',
                           path_effects=[effect], gid='peak')

    def get_plots(self):
        plots = []
        children = self.axes.get_children()
        for child in children:
            if child.get_gid() is not None:
                if child.get_gid() == "plot":
                    plots.append(child)

        return plots

    def clear_markers(self):
        children = self.axes.get_children()
        for child in children:
                if child.get_gid() is not None:
                    if child.get_gid() == 'peak':
                        child.remove()

    def cancel(self):
        self.abort = True


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)
