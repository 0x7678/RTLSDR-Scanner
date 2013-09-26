import itertools


import matplotlib
from matplotlib.backends.backend_wx import _load_bitmap
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas, \
    NavigationToolbar2WxAgg
from matplotlib.ticker import AutoMinorLocator, ScalarFormatter
import numpy
import rtlsdr
import wx

from constants import *
from misc import split_spectrum, open_plot
import wx.grid as grid
import wx.lib.masked as masked


matplotlib.interactive(True)
matplotlib.use('WXAgg')


class CellRenderer(grid.PyGridCellRenderer):
    def __init__(self):
        grid.PyGridCellRenderer.__init__(self)

    def Draw(self, grid, attr, dc, rect, row, col, _isSelected):
        dc.SetBrush(wx.Brush(attr.GetBackgroundColour()))
        dc.DrawRectangleRect(rect)
        if grid.GetCellValue(row, col) == "1":
            dc.SetBrush(wx.Brush(attr.GetTextColour()))
            dc.DrawCircle(rect.x + (rect.width / 2),
                          rect.y + (rect.height / 2),
                          rect.height / 4)


class NavigationToolbar(NavigationToolbar2WxAgg):
    def __init__(self, canvas, main):
        self.main = main

        navId = wx.NewId()
        NavigationToolbar2WxAgg.__init__(self, canvas)
        self.DeleteTool(self.wx_ids['Back'])
        self.DeleteTool(self.wx_ids['Forward'])
        self.DeleteTool(self.wx_ids['Subplots'])
        self.AddSimpleTool(navId, _load_bitmap('subplots.png'),
                           'Range', 'Set plot range')
        wx.EVT_TOOL(self, navId, self.on_range)

    def on_range(self, _event):
        dlg = DialogRange(self, self.main)
        if dlg.ShowModal() == wx.ID_OK:
            self.main.draw_plot(True, True)
        dlg.Destroy()


class NavigationToolbarCompare(NavigationToolbar2WxAgg):
    def __init__(self, canvas):
        NavigationToolbar2WxAgg.__init__(self, canvas)


class PanelGraph(wx.Panel):
    def __init__(self, parent, main):
        self.main = main

        wx.Panel.__init__(self, parent)

        self.figure = matplotlib.figure.Figure(facecolor='white')
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
        self.toolbar = NavigationToolbar(self.canvas, self.main)
        self.toolbar.Realize()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        vbox.Add(self.toolbar, 0, wx.EXPAND)

        self.SetSizer(vbox)
        vbox.Fit(self)

    def on_motion(self, event):
        xpos = event.xdata
        ypos = event.ydata
        text = ""
        if xpos is not None and ypos is not None:
            spectrum = self.main.spectrum
            if len(spectrum) > 0:
                x = min(spectrum.keys(), key=lambda freq: abs(freq - xpos))
                if(xpos <= max(spectrum.keys(), key=float)):
                    y = spectrum[x]
                    text = "f = {0:.3f}MHz, p = {1:.2f}dB".format(x, y)
                else:
                    text = "f = {0:.3f}MHz".format(xpos)

        self.main.status.SetStatusText(text, 1)

    def on_enter(self, _event):
        self.canvas.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))

    def get_canvas(self):
        return self.canvas

    def get_axes(self):
        return self.axes

    def get_toolbar(self):
        return self.toolbar


class PanelGraphCompare(wx.Panel):
    def __init__(self, parent):

        self.spectrum1 = None
        self.spectrum2 = None

        formatter = ScalarFormatter(useOffset=False)

        wx.Panel.__init__(self, parent)

        figure = matplotlib.figure.Figure(facecolor='white')

        self.axesScan = figure.add_subplot(111)
        self.axesScan.xaxis.set_minor_locator(AutoMinorLocator(10))
        self.axesScan.yaxis.set_minor_locator(AutoMinorLocator(10))
        self.axesScan.xaxis.set_major_formatter(formatter)
        self.axesScan.yaxis.set_major_formatter(formatter)
        self.axesDiff = self.axesScan.twinx()
        self.axesDiff.yaxis.set_minor_locator(AutoMinorLocator(10))
        self.plotScan1, = self.axesScan.plot([], [], 'b-',
                                                     linewidth=0.4)
        self.plotScan2, = self.axesScan.plot([], [], 'g-',
                                                     linewidth=0.4)
        self.plotDiff, = self.axesDiff.plot([], [], 'r-', linewidth=0.4)
        self.axesScan.set_ylim(auto=True)
        self.axesDiff.set_ylim(auto=True)

        self.axesScan.set_title("Level Comparison")
        self.axesScan.set_xlabel("Frequency (MHz)")
        self.axesScan.set_ylabel('Level (dB)')
        self.axesDiff.set_ylabel('Difference (db)')

        self.canvas = FigureCanvas(self, -1, figure)
        self.canvas.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)

        self.check1 = wx.CheckBox(self, wx.ID_ANY, "Scan 1")
        self.check2 = wx.CheckBox(self, wx.ID_ANY, "Scan 2")
        self.checkDiff = wx.CheckBox(self, wx.ID_ANY, "Difference")
        self.checkGrid = wx.CheckBox(self, wx.ID_ANY, "Grid")
        self.check1.SetValue(True)
        self.check2.SetValue(True)
        self.checkDiff.SetValue(True)
        self.checkGrid.SetValue(True)
        self.on_check_grid(None)
        self.Bind(wx.EVT_CHECKBOX, self.on_check1, self.check1)
        self.Bind(wx.EVT_CHECKBOX, self.on_check2, self.check2)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_diff, self.checkDiff)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_grid, self.checkGrid)

        grid = wx.GridBagSizer(5, 5)
        grid.Add(self.check1, pos=(0, 0), flag=wx.ALIGN_CENTER)
        grid.Add(self.check2, pos=(0, 1), flag=wx.ALIGN_CENTER)
        grid.Add((20, 1), pos=(0, 2))
        grid.Add(self.checkDiff, pos=(0, 3), flag=wx.ALIGN_CENTER)
        grid.Add((20, 1), pos=(0, 4))
        grid.Add(self.checkGrid, pos=(0, 5), flag=wx.ALIGN_CENTER)

        toolbar = NavigationToolbarCompare(self.canvas)
        toolbar.Realize()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        vbox.Add(grid, 0, wx.ALIGN_CENTRE | wx.ALL, border=5)
        vbox.Add(toolbar, 0, wx.EXPAND)

        self.SetSizer(vbox)
        vbox.Fit(self)

    def on_enter(self, _event):
        self.canvas.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))

    def on_check1(self, _event):
        self.plotScan1.set_visible(self.check1.GetValue())
        self.canvas.draw()

    def on_check2(self, _event):
        self.plotScan2.set_visible(self.check2.GetValue())
        self.canvas.draw()

    def on_check_diff(self, _event):
        self.plotDiff.set_visible(self.checkDiff.GetValue())
        self.canvas.draw()

    def on_check_grid(self, _event):
        self.axesDiff.grid(self.checkGrid.GetValue())
        self.canvas.draw()

    def plot_diff(self):
        diff = {}

        if self.spectrum1 is not None and self.spectrum2 is not None:
            set1 = set(self.spectrum1)
            set2 = set(self.spectrum2)
            intersect = set1.intersection(set2)
            for freq in intersect:
                diff[freq] = self.spectrum1[freq] - self.spectrum2[freq]
            freqs, powers = split_spectrum(diff)
            self.plotDiff.set_xdata(freqs)
            self.plotDiff.set_ydata(powers)
        elif self.spectrum1 is None:
            freqs, powers = split_spectrum(self.spectrum2)
            self.plotDiff.set_xdata(freqs)
            self.plotDiff.set_ydata([0] * len(freqs))
        else:
            freqs, powers = split_spectrum(self.spectrum1)
            self.plotDiff.set_xdata(freqs)
            self.plotDiff.set_ydata([0] * len(freqs))

        self.axesDiff.relim()
        self.axesDiff.autoscale_view()

    def set_spectrum1(self, spectrum):
        self.spectrum1 = spectrum
        freqs, powers = split_spectrum(spectrum)
        self.plotScan1.set_xdata(freqs)
        self.plotScan1.set_ydata(powers)
        self.plot_diff()
        self.axesScan.relim()
        self.axesScan.autoscale_view()
        self.canvas.draw()

    def set_spectrum2(self, spectrum):
        self.spectrum2 = spectrum
        freqs, powers = split_spectrum(spectrum)
        self.plotScan2.set_xdata(freqs)
        self.plotScan2.set_ydata(powers)
        self.plot_diff()
        self.axesScan.relim()
        self.axesScan.autoscale_view()
        self.canvas.draw()


class DialogCompare(wx.Dialog):
    def __init__(self, parent, dirname, filename):

        self.dirname = dirname
        self.filename = filename

        wx.Dialog.__init__(self, parent=parent, title="Compare plots",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)

        self.graph = PanelGraphCompare(self)

        self.buttonPlot1 = wx.Button(self, wx.ID_ANY, 'Load plot #1')
        self.buttonPlot2 = wx.Button(self, wx.ID_ANY, 'Load plot #2')
        self.Bind(wx.EVT_BUTTON, self.on_load_plot, self.buttonPlot1)
        self.Bind(wx.EVT_BUTTON, self.on_load_plot, self.buttonPlot2)
        self.textPlot1 = wx.StaticText(self, label="<None>")
        self.textPlot2 = wx.StaticText(self, label="<None>")

        buttonClose = wx.Button(self, wx.ID_CLOSE, 'Close')
        self.Bind(wx.EVT_BUTTON, self.on_close, buttonClose)

        grid = wx.GridBagSizer(5, 5)
        grid.AddGrowableCol(2, 0)
        grid.Add(self.buttonPlot1, pos=(0, 0), flag=wx.ALIGN_CENTER)
        grid.Add(self.textPlot1, pos=(0, 1), span=(1, 2))
        grid.Add(self.buttonPlot2, pos=(1, 0), flag=wx.ALIGN_CENTER)
        grid.Add(self.textPlot2, pos=(1, 1), span=(1, 2))
        grid.Add(buttonClose, pos=(2, 3), flag=wx.ALIGN_RIGHT)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.graph, 1, wx.EXPAND)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, border=5)
        self.SetSizerAndFit(sizer)

    def on_load_plot(self, event):
        dlg = wx.FileDialog(self, "Open a scan", self.dirname, self.filename,
                            FILE_RFS, wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            _start, _stop, spectrum = open_plot(dlg.GetDirectory(),
                                                dlg.GetFilename())
            if(event.EventObject == self.buttonPlot1):
                self.textPlot1.SetLabel(dlg.GetFilename())
                self.graph.set_spectrum1(spectrum)
            else:
                self.textPlot2.SetLabel(dlg.GetFilename())
                self.graph.set_spectrum2(spectrum)
        dlg.Destroy()

    def on_close(self, _event):
        self.EndModal(wx.ID_CLOSE)
        return


class DialogAutoCal(wx.Dialog):
    def __init__(self, parent, freq, callback):
        self.callback = callback
        self.cal = 0

        wx.Dialog.__init__(self, parent=parent, title="Auto Calibration",
                           style=wx.CAPTION)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        title = wx.StaticText(self, label="Calibrate to a known stable signal")
        font = title.GetFont()
        font.SetPointSize(font.GetPointSize() + 2)
        title.SetFont(font)
        text = wx.StaticText(self, label="Frequency (MHz)")
        self.textFreq = masked.NumCtrl(self, value=freq, fractionWidth=3,
                                        min=F_MIN, max=F_MAX)

        self.buttonCal = wx.Button(self, label="Calibrate")
        if len(parent.devices) == 0:
            self.buttonCal.Disable()
        self.buttonCal.Bind(wx.EVT_BUTTON, self.on_cal)
        self.textResult = wx.StaticText(self)

        self.buttonOk = wx.Button(self, wx.ID_OK, 'OK')
        self.buttonOk.Disable()
        self.buttonCancel = wx.Button(self, wx.ID_CANCEL, 'Cancel')

        self.buttonOk.Bind(wx.EVT_BUTTON, self.on_close)
        self.buttonCancel.Bind(wx.EVT_BUTTON, self.on_close)

        buttons = wx.StdDialogButtonSizer()
        buttons.AddButton(self.buttonOk)
        buttons.AddButton(self.buttonCancel)
        buttons.Realize()

        sizer = wx.GridBagSizer(10, 10)
        sizer.Add(title, pos=(0, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        sizer.Add(text, pos=(1, 0), flag=wx.ALL | wx.EXPAND, border=10)
        sizer.Add(self.textFreq, pos=(1, 1), flag=wx.ALL | wx.EXPAND,
                  border=5)
        sizer.Add(self.buttonCal, pos=(2, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, border=10)
        sizer.Add(self.textResult, pos=(3, 0), span=(1, 2),
                  flag=wx.ALL | wx.EXPAND, border=10)
        sizer.Add(buttons, pos=(4, 0), span=(1, 2),
                  flag=wx.ALL | wx.EXPAND, border=10)

        self.SetSizerAndFit(sizer)

    def on_cal(self, _event):
        self.buttonCal.Disable()
        self.buttonOk.Disable()
        self.buttonCancel.Disable()
        self.textFreq.Disable()
        self.textResult.SetLabel("Calibrating...")
        self.callback(CAL_START)

    def on_close(self, event):
        status = [CAL_CANCEL, CAL_OK][event.GetId() == wx.ID_OK]
        self.callback(status)
        self.EndModal(event.GetId())
        return

    def enable_controls(self):
        self.buttonCal.Enable(True)
        self.buttonOk.Enable(True)
        self.buttonCancel.Enable(True)
        self.textFreq.Enable()

    def set_cal(self, cal):
        self.cal = cal
        self.enable_controls()
        self.textResult.SetLabel("Correction (ppm): {0:.3f}".format(cal))

    def get_cal(self):
        return self.cal

    def reset_cal(self):
        self.set_cal(self.cal)

    def get_freq(self):
        return self.textFreq.GetValue()


class DialogOffset(wx.Dialog):
    def __init__(self, parent, index, offset):
        self.index = index
        self.offset = offset
        self.band1 = None
        self.band2 = None

        wx.Dialog.__init__(self, parent=parent, title="Scan Offset")

        figure = matplotlib.figure.Figure(facecolor='white')
        self.axes = figure.add_subplot(111)
        self.canvas = FigureCanvas(self, -1, figure)
        self.canvas.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)

        textHelp = wx.StaticText(self,
            label="Remove the aerial and press refresh, "
            "adjust the offset so the shaded areas overlay the flattest parts "
            "of the plot.")

        textFreq = wx.StaticText(self, label="Test frequency (MHz)")
        self.spinFreq = wx.SpinCtrl(self)
        self.spinFreq.SetRange(F_MIN, F_MAX)
        self.spinFreq.SetValue(200)

        textGain = wx.StaticText(self, label="Test gain (dB)")
        self.spinGain = wx.SpinCtrl(self)
        self.spinGain.SetRange(-100, 200)
        self.spinGain.SetValue(200)

        refresh = wx.Button(self, wx.ID_ANY, 'Refresh')
        self.Bind(wx.EVT_BUTTON, self.on_refresh, refresh)

        textOffset = wx.StaticText(self, label="Offset (kHz)")
        self.spinOffset = wx.SpinCtrl(self)
        self.spinOffset.SetRange(0, ((SAMPLE_RATE / 2) - BANDWIDTH) / 1e3)
        self.spinOffset.SetValue(offset)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin, self.spinOffset)

        sizerButtons = wx.StdDialogButtonSizer()
        buttonOk = wx.Button(self, wx.ID_OK)
        buttonCancel = wx.Button(self, wx.ID_CANCEL)
        sizerButtons.AddButton(buttonOk)
        sizerButtons.AddButton(buttonCancel)
        sizerButtons.Realize()
        self.Bind(wx.EVT_BUTTON, self.on_ok, buttonOk)

        boxSizer1 = wx.BoxSizer(wx.HORIZONTAL)
        boxSizer1.Add(textFreq, border=5)
        boxSizer1.Add(self.spinFreq, border=5)
        boxSizer1.Add(textGain, border=5)
        boxSizer1.Add(self.spinGain, border=5)

        boxSizer2 = wx.BoxSizer(wx.HORIZONTAL)
        boxSizer2.Add(textOffset, border=5)
        boxSizer2.Add(self.spinOffset, border=5)

        gridSizer = wx.GridBagSizer(5, 5)
        gridSizer.Add(self.canvas, pos=(0, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTER | wx.ALL)
        gridSizer.Add(textHelp, pos=(1, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTER | wx.ALL)
        gridSizer.Add(boxSizer1, pos=(2, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTER | wx.ALL)
        gridSizer.Add(refresh, pos=(3, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTER | wx.ALL)
        gridSizer.Add(boxSizer2, pos=(4, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTER | wx.ALL)
        gridSizer.Add(sizerButtons, pos=(5, 1), span=(1, 1),
                  flag=wx.ALIGN_RIGHT | wx.ALL)

        self.SetSizerAndFit(gridSizer)
        self.draw_limits()

    def on_enter(self, _event):
        self.canvas.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))

    def on_ok(self, _event):

        self.EndModal(wx.ID_OK)

    def on_refresh(self, _event):
        plot = []

        dlg = wx.BusyInfo('Please wait...')

        try:
            sdr = rtlsdr.RtlSdr(int(self.index))
            sdr.set_sample_rate(SAMPLE_RATE)
            sdr.set_center_freq(self.spinFreq.GetValue() * 1e6)
            sdr.set_gain(self.spinGain.GetValue())
            capture = sdr.read_samples(2 ** 18)
        except IOError as error:
            dlg.Destroy()
            dlg = wx.MessageDialog(self,
                                   'Capture failed:\n{0}'.format(error.message),
                                   'Error',
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            return

        powers, freqs = matplotlib.mlab.psd(capture,
                         NFFT=1024,
                         Fs=SAMPLE_RATE / 1e6,
                         window=matplotlib.numpy.hamming(1024))

        for x, y in itertools.izip(freqs, powers):
            x = x * SAMPLE_RATE / 2e6
            plot.append((x, y))
        plot.sort()
        x, y = numpy.transpose(plot)

        self.axes.clear()
        self.band1 = None
        self.band2 = None
        self.axes.set_xlabel("Frequency (MHz)")
        self.axes.set_ylabel('Level (dB)')
        self.axes.set_yscale('log')
        self.axes.plot(x, y, linewidth=0.4)
        self.axes.grid(True)
        self.draw_limits()

        dlg.Destroy()

    def on_spin(self, _event):
        self.offset = self.spinOffset.GetValue()
        self.draw_limits()

    def draw_limits(self):
        limit1 = self.offset / 1e3
        limit2 = limit1 + BANDWIDTH / 1e6
        if(self.band1 is not None):
            self.band1.remove()
        if(self.band2 is not None):
            self.band2.remove()
        self.band1 = self.axes.axvspan(limit1, limit2, color='g', alpha=0.25)
        self.band2 = self.axes.axvspan(-limit1, -limit2, color='g', alpha=0.25)
        self.canvas.draw()

    def get_offset(self):
        return self.offset


class DialogPrefs(wx.Dialog):
    def __init__(self, parent, devices, settings):
        self.settings = settings
        self.index = 0

        wx.Dialog.__init__(self, parent=parent, title="Preferences")

        self.checkSaved = wx.CheckBox(self, wx.ID_ANY,
                                      "Save warning")
        self.checkSaved.SetValue(self.settings.saveWarn)
        self.checkSaved.SetToolTip(wx.ToolTip('Prompt to save scan on exit'))
        self.checkAnnotate = wx.CheckBox(self, wx.ID_ANY,
                                      "Label peak level")
        self.checkAnnotate.SetValue(self.settings.annotate)
        self.checkAnnotate.SetToolTip(wx.ToolTip('Annotate scan peak value'))

        self.checkRetain = wx.CheckBox(self, wx.ID_ANY,
                                      "Display previous scans")
        self.checkRetain.SetToolTip(wx.ToolTip('Can be slow'))
        self.checkRetain.SetValue(self.settings.retainScans)
        self.Bind(wx.EVT_CHECKBOX, self.on_check, self.checkRetain)
        self.checkFade = wx.CheckBox(self, wx.ID_ANY,
                                      "Fade previous scans")
        self.checkFade.SetValue(self.settings.fadeScans)
        textMaxScans = wx.StaticText(self,
                                 label="Max scans")
        self.spinCtrlMaxScans = wx.SpinCtrl(self)
        self.spinCtrlMaxScans.SetRange(2, 500)
        self.spinCtrlMaxScans.SetValue(self.settings.maxScans)
        self.spinCtrlMaxScans.SetToolTip(wx.ToolTip('Maximum previous scans to display'))

        self.on_check(None)
        textWarn = wx.StaticText(self,
                                 label="(Only the most recent scan is saved)")

        self.devices = devices
        self.gridDev = grid.Grid(self)
        self.gridDev.CreateGrid(len(self.devices), 7)
        self.gridDev.SetRowLabelSize(0)
        self.gridDev.SetColLabelValue(0, "Select")
        self.gridDev.SetColLabelValue(1, "Device")
        self.gridDev.SetColLabelValue(2, "Index")
        self.gridDev.SetColLabelValue(3, "Gain\n(dB)")
        self.gridDev.SetColLabelValue(4, "Calibration\n(ppm)")
        self.gridDev.SetColLabelValue(5, "LO\n(MHz)")
        self.gridDev.SetColLabelValue(6, "Band Offset\n(kHz)")
        self.gridDev.SetColFormatFloat(3, -1, 1)
        self.gridDev.SetColFormatFloat(4, -1, 3)
        self.gridDev.SetColFormatFloat(5, -1, 3)
        self.gridDev.SetColFormatFloat(6, -1, 0)

        attributes = grid.GridCellAttr()
        attributes.SetBackgroundColour(self.gridDev.GetLabelBackgroundColour())
        self.gridDev.SetColAttr(1, attributes)
        self.gridDev.SetColAttr(2, attributes)

        i = 0
        for device in self.devices:
            self.gridDev.SetReadOnly(i, 0, True)
            self.gridDev.SetReadOnly(i, 1, True)
            self.gridDev.SetReadOnly(i, 2, True)
            self.gridDev.SetCellRenderer(i, 0, CellRenderer())
            self.gridDev.SetCellEditor(i, 3, grid.GridCellFloatEditor(-1, 1))
            self.gridDev.SetCellEditor(i, 4, grid.GridCellFloatEditor(-1, 3))
            self.gridDev.SetCellEditor(i, 5, grid.GridCellFloatEditor(-1, 3))
            self.gridDev.SetCellValue(i, 1, device.name)
            self.gridDev.SetCellValue(i, 2, str(i))
            self.gridDev.SetCellValue(i, 3, str(device.gain))
            self.gridDev.SetCellValue(i, 4, str(device.calibration))
            self.gridDev.SetCellValue(i, 5, str(device.lo))
            self.gridDev.SetCellValue(i, 6, str(device.offset / 1e3))
            i += 1

        if settings.index > len(self.devices):
            settings.index = len(self.devices)
        self.select_row(settings.index)

        self.gridDev.AutoSize()

        self.Bind(grid.EVT_GRID_CELL_LEFT_CLICK, self.on_click)

        sizerButtons = wx.StdDialogButtonSizer()
        buttonOk = wx.Button(self, wx.ID_OK)
        buttonCancel = wx.Button(self, wx.ID_CANCEL)
        sizerButtons.AddButton(buttonOk)
        sizerButtons.AddButton(buttonCancel)
        sizerButtons.Realize()
        self.Bind(wx.EVT_BUTTON, self.on_ok, buttonOk)

        optbox = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "General"),
                                     wx.VERTICAL)
        optbox.Add(self.checkSaved, 0, wx.ALL | wx.EXPAND, 10)
        optbox.Add(self.checkAnnotate, 0, wx.ALL | wx.EXPAND, 10)

        congrid = wx.GridBagSizer(10, 10)
        congrid.Add(self.checkRetain, pos=(0, 0), flag=wx.ALL)
        congrid.Add(textWarn, pos=(0, 1), flag=wx.ALL)
        congrid.Add(self.checkFade, pos=(1, 0), flag=wx.ALL)
        congrid.Add(textMaxScans, pos=(2, 0), flag=wx.ALL)
        congrid.Add(self.spinCtrlMaxScans, pos=(2, 1), flag=wx.ALL)

        conbox = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY,
                                                "Continuous scans"),
                                   wx.VERTICAL)
        conbox.Add(congrid, 0, wx.ALL | wx.EXPAND, 10)

        devbox = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Devices"),
                                     wx.VERTICAL)
        devbox.Add(self.gridDev, 0, wx.ALL | wx.EXPAND, 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(optbox, 0, wx.ALL | wx.EXPAND, 10)
        vbox.Add(conbox, 0, wx.ALL | wx.EXPAND, 10)
        vbox.Add(devbox, 0, wx.ALL | wx.EXPAND, 10)
        vbox.Add(sizerButtons, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizerAndFit(vbox)

    def on_check(self, _event):
        enabled = self.checkRetain.GetValue()
        self.checkFade.Enable(enabled)
        self.spinCtrlMaxScans.Enable(enabled)

    def on_click(self, event):
        col = event.GetCol()
        index = event.GetRow()
        if(col == 0):
            self.index = event.GetRow()
            self.select_row(index)
        elif(col == 6):
            dlg = DialogOffset(self, index,
                               float(self.gridDev.GetCellValue(index, 6)))
            if dlg.ShowModal() == wx.ID_OK:
                self.gridDev.SetCellValue(index, 6, str(dlg.get_offset()))
            dlg.Destroy()
        event.Skip()

    def on_ok(self, _event):
        self.settings.saveWarn = self.checkSaved.GetValue()
        self.settings.annotate = self.checkAnnotate.GetValue()
        self.settings.retainScans = self.checkRetain.GetValue()
        self.settings.fadeScans = self.checkFade.GetValue()
        self.settings.maxScans = self.spinCtrlMaxScans.GetValue()
        for i in range(0, self.gridDev.GetNumberRows()):
            self.devices[i].gain = float(self.gridDev.GetCellValue(i, 3))
            self.devices[i].calibration = float(self.gridDev.GetCellValue(i, 4))
            self.devices[i].lo = float(self.gridDev.GetCellValue(i, 5))
            self.devices[i].offset = float(self.gridDev.GetCellValue(i, 6)) * 1e3

        self.EndModal(wx.ID_OK)

    def select_row(self, index):
        for i in range(0, self.gridDev.GetNumberRows()):
            tick = "0"
            if i == index:
                tick = "1"
            self.gridDev.SetCellValue(i, 0, tick)

    def get_index(self):
        return self.index

    def get_devices(self):
        return self.devices


class DialogSaveWarn(wx.Dialog):
    def __init__(self, parent, warnType):
        self.code = -1

        wx.Dialog.__init__(self, parent=parent, title="Warning",
                           style=wx.ICON_EXCLAMATION)

        prompt = ["scanning again", "opening a file", "exiting"][warnType]
        text = wx.StaticText(self, label="Save plot before {0}?".format(prompt))
        icon = wx.StaticBitmap(self, wx.ID_ANY,
                               wx.ArtProvider.GetBitmap(wx.ART_INFORMATION,
                                                        wx.ART_MESSAGE_BOX))

        tbox = wx.BoxSizer(wx.HORIZONTAL)
        tbox.Add(text)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(icon, 0, wx.ALL, 5)
        hbox.Add(tbox, 0, wx.ALL, 5)

        buttonYes = wx.Button(self, wx.ID_YES, 'Yes')
        buttonNo = wx.Button(self, wx.ID_NO, 'No')
        buttonCancel = wx.Button(self, wx.ID_CANCEL, 'Cancel')

        buttonYes.Bind(wx.EVT_BUTTON, self.on_close)
        buttonNo.Bind(wx.EVT_BUTTON, self.on_close)

        buttons = wx.StdDialogButtonSizer()
        buttons.AddButton(buttonYes)
        buttons.AddButton(buttonNo)
        buttons.AddButton(buttonCancel)
        buttons.Realize()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 1, wx.ALL | wx.EXPAND, 10)
        vbox.Add(buttons, 1, wx.ALL | wx.EXPAND, 10)

        self.SetSizerAndFit(vbox)

    def on_close(self, event):
        self.EndModal(event.GetId())
        return

    def get_code(self):
        return self.code


class DialogRange(wx.Dialog):
    def __init__(self, parent, main):
        self.main = main

        wx.Dialog.__init__(self, parent=parent, title="Plot Range")

        self.checkAuto = wx.CheckBox(self, wx.ID_ANY, "Auto range")
        self.checkAuto.SetValue(self.main.settings.autoScale)
        self.Bind(wx.EVT_CHECKBOX, self.on_auto, self.checkAuto)

        textMax = wx.StaticText(self, label="Maximum (dB)")
        self.yMax = masked.NumCtrl(self, value=int(self.main.settings.yMax),
                                    fractionWidth=0, min=-100, max=20)
        textMin = wx.StaticText(self, label="Minimum (dB)")
        self.yMin = masked.NumCtrl(self, value=int(self.main.settings.yMin),
                                    fractionWidth=0, min=-100, max=20)
        self.set_enabled(not self.main.settings.autoScale)

        sizerButtons = wx.StdDialogButtonSizer()
        buttonOk = wx.Button(self, wx.ID_OK)
        buttonCancel = wx.Button(self, wx.ID_CANCEL)
        sizerButtons.AddButton(buttonOk)
        sizerButtons.AddButton(buttonCancel)
        sizerButtons.Realize()
        self.Bind(wx.EVT_BUTTON, self.on_ok, buttonOk)

        sizer = wx.GridBagSizer(10, 10)
        sizer.Add(self.checkAuto, pos=(0, 0), span=(1, 1),
                  flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        sizer.Add(textMax, pos=(1, 0), span=(1, 1),
                  flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        sizer.Add(self.yMax, pos=(1, 1), span=(1, 1),
                  flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        sizer.Add(textMin, pos=(2, 0), span=(1, 1),
                  flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        sizer.Add(self.yMin, pos=(2, 1), span=(1, 1),
                  flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        sizer.Add(sizerButtons, pos=(3, 0), span=(1, 2),
                  flag=wx.ALIGN_CENTER | wx.ALL, border=10)

        self.SetSizerAndFit(sizer)

    def on_auto(self, _event):
        state = self.checkAuto.GetValue()
        self.set_enabled(not state)
        self.main.checkAuto.SetValue(state)

    def on_ok(self, _event):
        self.main.settings.autoScale = self.checkAuto.GetValue()
        self.main.settings.yMin = self.yMin.GetValue()
        self.main.settings.yMax = self.yMax.GetValue()
        self.EndModal(wx.ID_OK)

    def set_enabled(self, isEnabled):
        self.yMax.Enable(isEnabled)
        self.yMin.Enable(isEnabled)


class DialogRefresh(wx.Dialog):
    def __init__(self, parent):

        wx.Dialog.__init__(self, parent=parent, style=0)

        text = wx.StaticText(self, label="Refreshing plot, please wait...")
        icon = wx.StaticBitmap(self, wx.ID_ANY,
                               wx.ArtProvider.GetBitmap(wx.ART_INFORMATION,
                                                        wx.ART_MESSAGE_BOX))

        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(icon, flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        box.Add(text, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

        self.SetSizerAndFit(box)
        self.Centre()
