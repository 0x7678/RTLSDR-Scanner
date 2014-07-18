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
from wx.grid import PyGridCellRenderer


class MultiButton(wx.PyControl):
    PADDING = 5
    ARROW_SIZE = 6

    def __init__(self, parent, options, tips=None, selected=0):
        wx.PyControl.__init__(self, parent=parent, size=wx.DefaultSize,
                              style=wx.NO_BORDER)
        self.options = options
        self.tips = tips
        self.selected = selected
        self.isOverArrow = False

        self.__set_text()

        self.menu = wx.Menu()
        for option in options:
            item = self.menu.Append(wx.ID_ANY, option)
            self.Bind(wx.EVT_MENU, self.__on_menu, item)

        self.Bind(wx.EVT_PAINT, self.__on_paint)
        self.Bind(wx.EVT_SIZE, self.__on_size)
        self.Bind(wx.EVT_LEFT_UP, self.__on_left_up)
        self.Bind(wx.EVT_MOTION, self.__on_motion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)

    def __on_paint(self, _event):
        dc = wx.GCDC(wx.PaintDC(self))
        self.__draw(dc)

    def __on_size(self, _event):
        self.Refresh()

    def __on_left_up(self, event):
        if self.__is_over_arrow(event):
            self.__show_menu()
        else:
            event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED,
                                    self.GetId())
            event.SetEventObject(self)
            event.SetInt(self.selected)
            event.SetString(self.GetLabel())
            self.GetEventHandler().ProcessEvent(event)

    def __on_motion(self, event):
        if self.isOverArrow != self.__is_over_arrow(event):
            self.isOverArrow = self.__is_over_arrow(event)
            self.Refresh()

    def __on_leave(self, _event):
        self.isOverArrow = False
        self.Refresh()

    def __on_menu(self, event):
        item = self.menu.FindItemById(event.Id)
        label = item.GetLabel()
        self.selected = self.options.index(label)
        self.__set_text()

    def __show_menu(self):
        self.PopupMenu(self.menu)

    def __set_text(self):
        self.SetLabel(self.options[self.selected])
        if self.tips is not None:
            self.SetToolTip(wx.ToolTip(self.tips[self.selected]))
        self.Refresh()

    def __is_over_arrow(self, event):
        x = event.GetPosition()[0]
        y = event.GetPosition()[1]
        width = event.GetEventObject().GetSize()[0]
        height = event.GetEventObject().GetSize()[1]

        top = (height / 2) - (MultiButton.ARROW_SIZE / 4) - MultiButton.PADDING
        bottom = top + MultiButton.ARROW_SIZE / 2 + MultiButton.PADDING * 2
        right = width - MultiButton.PADDING
        left = right - MultiButton.ARROW_SIZE - MultiButton.PADDING * 2

        if (right >= x >= left) and (bottom >= y >= top):
            return True
        return False

    def __draw(self, dc):
        renderer = wx.RendererNative.Get()
        rect = self.GetClientRect()
        renderer.DrawPushButton(self, dc, rect)

        dc.SetFont(self.GetFont())

        if self.IsEnabled():
            colour = self.GetForegroundColour()
        else:
            colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        if not self.isOverArrow:
            brush = wx.Brush(colour, wx.SOLID)
            dc.SetBrush(brush)
        pen = wx.Pen(colour)
        dc.SetPen(pen)
        dc.SetTextForeground(colour)

        label = self.GetLabel()
        _textWidth, textHeight = dc.GetTextExtent(label)

        dc.DrawText(self.GetLabel(),
                    MultiButton.PADDING,
                    (rect.height - textHeight) / 2)

        top = (rect.height / 2) - (MultiButton.ARROW_SIZE / 4)
        bottom = top + MultiButton.ARROW_SIZE / 2
        right = rect.width - MultiButton.PADDING * 2
        left = right - MultiButton.ARROW_SIZE
        dc.DrawPolygon([(right, top),
                        (left, top),
                        (left + MultiButton.ARROW_SIZE / 2, bottom)])

    def DoGetBestSize(self):
        label = max(self.options, key=len)
        font = self.GetFont()
        dc = wx.ClientDC(self)
        dc.SetFont(font)
        textWidth, textHeight = dc.GetTextExtent(label)
        width = textWidth + MultiButton.ARROW_SIZE + MultiButton.PADDING * 4
        height = textHeight + MultiButton.PADDING * 2

        return wx.Size(width, height)

    def Enable(self, enabled):
        self.Enabled = enabled
        self.Refresh()

    def SetSelected(self, selected):
        self.selected = selected
        self.__set_text()

    def GetSelected(self):
        return self.selected


class Led(wx.PyControl):
    PULSE_TIME = 250

    def __init__(self, parent, id=wx.ID_ANY, label=''):
        self.lit = False
        self.colour = wx.GREEN

        wx.PyControl.__init__(self, parent=parent, id=id, size=wx.DefaultSize,
                              style=wx.NO_BORDER)

        self.SetLabel(label)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.__on_timer, self.timer)

        self.Bind(wx.EVT_PAINT, self.__on_paint)
        self.Bind(wx.EVT_SIZE, self.__on_size)

    def __on_paint(self, _event):
        dc = wx.BufferedPaintDC(self)
        self.__draw(dc)

    def __on_size(self, _event):
        self.Refresh()

    def __on_timer(self, _event):
        self.timer.Stop()
        self.lit = False
        self.Refresh()

    def __draw(self, dc):
        colour = self.GetBackgroundColour()
        brush = wx.Brush(colour, wx.SOLID)
        dc.SetBackground(brush)
        dc.SetFont(self.GetFont())
        dc.Clear()

        label = self.GetLabel()
        _width, height = self.GetClientSize()
        ledRadius = height / 3
        _textWidth, textHeight = dc.GetTextExtent(label)

        gc = wx.GraphicsContext.Create(dc)
        gc.SetPen(wx.BLACK_PEN)

        if self.lit:
            brush = wx.Brush(self.colour, wx.SOLID)
            gc.SetBrush(brush)

        path = gc.CreatePath()
        path.AddCircle(height / 2, height / 2, ledRadius)
        path.CloseSubpath()

        gc.FillPath(path)
        gc.StrokePath(path)

        dc.DrawText(label, height + 10, (height - textHeight) / 2)

    def on(self, colour=wx.GREEN):
        self.timer.Stop()
        self.lit = True
        self.colour = colour
        self.Refresh()

    def pulse(self, colour=wx.GREEN):
        self.lit = True
        self.colour = colour
        self.Refresh()
        self.timer.Start(Led.PULSE_TIME)


class CheckCellRenderer(PyGridCellRenderer):
    SIZE = 10
    PADDING = 3

    def __init__(self, showBox=True):
        self.showBox = showBox

        PyGridCellRenderer.__init__(self)

    def GetBestSize(self, _grid, _attr, _dc, _row, _col):
        return wx.Size(CheckCellRenderer.SIZE * 2, CheckCellRenderer.SIZE)

    def Draw(self, grid, attr, dc, rect, row, col, _isSelected):
        dc.SetBrush(wx.Brush(attr.GetBackgroundColour()))
        dc.DrawRectangleRect(rect)

        gc = wx.GraphicsContext.Create(dc)
        gc.SetPen(wx.Pen(attr.GetTextColour()))

        pad = CheckCellRenderer.PADDING
        x = rect.x + pad
        y = rect.y + pad
        w = rect.height - pad * 2.0
        h = rect.height - pad * 2.0

        if self.showBox:
            pathBox = gc.CreatePath()
            pathBox.AddRectangle(x, y, w, h)
            gc.StrokePath(pathBox)

        if grid.GetCellValue(row, col) == "1":
            pathTick = gc.CreatePath()
            pathTick.MoveToPoint(1, 3)
            pathTick.AddLineToPoint(2, 4)
            pathTick.AddLineToPoint(4, 1)
            scale = w / 5.0
            transform = gc.CreateMatrix()
            transform.Set(a=scale, d=scale, tx=x, ty=y)
            pathTick.Transform(transform)
            gc.StrokePath(pathTick)


# Based on http://wiki.wxpython.org/wxGrid%20ToolTips
class GridToolTips(object):
    def __init__(self, grid, toolTips):
        self.lastPos = (None, None)
        self.grid = grid
        self.toolTips = toolTips

        grid.GetGridWindow().Bind(wx.EVT_MOTION, self.__on_motion)

    def __on_motion(self, event):
        x, y = self.grid.CalcUnscrolledPosition(event.GetPosition())
        row = self.grid.YToRow(y)
        col = self.grid.XToCol(x)

        if (row, col) != self.lastPos:
            if row >= 0 and col >= 0:
                self.lastPos = (row, col)
                if (row, col) in self.toolTips:
                    toolTip = self.toolTips[(row, col)]
                else:
                    toolTip = ''
                self.grid.GetGridWindow().SetToolTipString(toolTip)


if __name__ == '__main__':
    print 'Please run rtlsdr_scan.py'
    exit(1)
