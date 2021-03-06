#!/usr/bin/python3
# -*- coding: utf-8 -*-

'''Pychemqt, Chemical Engineering Process simulator
Copyright (C) 2016, Juan José Gómez Romera <jjgomera@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.'''



###############################################################################
# Psychrometric graphic tools
#   - PsychroPlot: Plot widget for psychrometric chart
#   - PsychroInput: Widget with input for psychrometric state
#   - UI_Psychrometry: Psychrometric chart
###############################################################################

import os
import pickle
from configparser import ConfigParser
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets

from scipy import pi, arctan

from lib.psycrometry import PsyState, PsychroState
from lib.psycrometry import _Pbar, _height, _tdp, _Psat, _W, _Tdb, _Tdb_V, _W_V
from lib import unidades, config
from lib.plot import mpl
from UI.widgets import Entrada_con_unidades


class PsychroPlot(mpl):
    """
    Plot widget for psychrometric chart
        Add custom margins
        Define a pointer to text state properties, to remove and redraw
    """
    def __init__(self, *args, **kwargs):
        mpl.__init__(self, *args, **kwargs)
        self.axes2D.figure.subplots_adjust(left=0.01, right=0.92,
                                           bottom=0.05, top=0.98)
        self.notes = []

    def config(self):
        self.axes2D.set_autoscale_on(False)
        self.axes2D.set_xlabel("Tdb, "+unidades.Temperature(None).text())
        self.axes2D.set_ylabel(QtWidgets.QApplication.translate("pychemqt", "Absolute humidity")+", "+unidades.Mass(None).text()+"/"+unidades.Mass(None).text())
        self.axes2D.yaxis.set_ticks_position("right")
        self.axes2D.yaxis.set_label_position("right")

        self.lx = self.axes2D.axhline(color='b')  # the horiz line
        self.ly = self.axes2D.axvline(color='b')  # the vert line

        tmin = unidades.Temperature(274).config()
        tmax = unidades.Temperature(329).config()

        self.axes2D.set_xlim(tmin, tmax)
        self.axes2D.set_ylim(0, 0.04)

    def showPointData(self, state):
        self.clearPointData()

        yi = 0.99
        for key in ("tdb", "tdp", "twb", "HR", "w", "h", "v", "rho"):
            self.notes.append(self.axes2D.annotate(
                "%s: %s" % (key, state.__getattribute__(key).str), (0.01, yi),
                xycoords='axes fraction', size="small", va="center"))
            yi -= 0.025
        self.draw()

    def clearPointData(self):
        while self.notes:
            anotation = self.notes.pop()
            anotation.remove()
        self.draw()


class PsychroInput(QtWidgets.QWidget):
    """Widget with parameter for psychrometric state"""
    parameters = ["tdb", "twb", "tdp", "w", "HR", "v", "h"]
    stateChanged = QtCore.pyqtSignal(PsyState)
    pressureChanged = QtCore.pyqtSignal()

    def __init__(self, state=None, readOnly=False, parent=None):
        """
        constructor
        optional state parameter to assign initial psychrometric state"""
        super(PsychroInput, self).__init__(parent)

        self.state = PsychroState(P=101325)
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)

        layout = QtWidgets.QGridLayout(self)
        self.checkPresion = QtWidgets.QRadioButton(
                QtWidgets.QApplication.translate("pychemqt", "Pressure"))
        layout.addWidget(self.checkPresion, 1, 1, 1, 1)
        self.P = Entrada_con_unidades(unidades.Pressure, value=101325)
        self.P.valueChanged.connect(self.changePressure)
        layout.addWidget(self.P, 1, 2, 1, 1)
        self.checkAltitud = QtWidgets.QRadioButton(
                QtWidgets.QApplication.translate("pychemqt", "Altitude"))
        layout.addWidget(self.checkAltitud, 2, 1, 1, 1)
        self.z = Entrada_con_unidades(unidades.Length, value=0)
        self.checkPresion.toggled.connect(self.P.setEnabled)
        self.checkAltitud.toggled.connect(self.z.setEnabled)
        self.z.valueChanged.connect(self.changeAltitude)
        self.checkPresion.setChecked(True)
        self.z.setEnabled(False)
        layout.addWidget(self.z, 2, 2, 1, 1)
        layout.addItem(QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Fixed,
                                         QtWidgets.QSizePolicy.Fixed), 3, 1, 1, 2)

        layout.addWidget(QtWidgets.QLabel(QtWidgets.QApplication.translate(
            "pychemqt", "Select point")), 4, 1, 1, 2)
        self.variables = QtWidgets.QComboBox()
        for txt in PsyState.TEXT_MODE:
            self.variables.addItem(txt)
        self.variables.currentIndexChanged.connect(self.updateInputs)
        layout.addWidget(self.variables, 5, 1, 1, 2)

        layout.addWidget(QtWidgets.QLabel("Tdb:"), 6, 1, 1, 1)
        self.tdb = Entrada_con_unidades(unidades.Temperature)
        self.tdb.valueChanged.connect(partial(self.updateKwargs, "tdb"))
        layout.addWidget(self.tdb, 6, 2, 1, 1)
        layout.addWidget(QtWidgets.QLabel("Twb:"), 7, 1, 1, 1)
        self.twb = Entrada_con_unidades(unidades.Temperature)
        self.twb.valueChanged.connect(partial(self.updateKwargs, "twb"))
        layout.addWidget(self.twb, 7, 2, 1, 1)
        layout.addWidget(QtWidgets.QLabel("Tdp:"), 8, 1, 1, 1)
        self.tdp = Entrada_con_unidades(unidades.Temperature)
        self.tdp.valueChanged.connect(partial(self.updateKwargs, "tdp"))
        layout.addWidget(self.tdp, 8, 2, 1, 1)
        layout.addWidget(QtWidgets.QLabel(QtWidgets.QApplication.translate(
            "pychemqt", "Humidity Ratio:")), 9, 1, 1, 1)
        self.w = Entrada_con_unidades(float, textounidad="kgw/kgda")
        self.w.valueChanged.connect(partial(self.updateKwargs, "w"))
        layout.addWidget(self.w, 9, 2, 1, 1)
        layout.addWidget(QtWidgets.QLabel(QtWidgets.QApplication.translate(
            "pychemqt", "Relative humidity:")), 10, 1, 1, 1)
        self.HR = Entrada_con_unidades(float, textounidad="%")
        self.HR.valueChanged.connect(partial(self.updateKwargs, "HR"))
        layout.addWidget(self.HR, 10, 2, 1, 1)
        layout.addWidget(QtWidgets.QLabel(QtWidgets.QApplication.translate(
            "pychemqt", "Volume")), 11, 1, 1, 1)
        self.v = Entrada_con_unidades(unidades.SpecificVolume)
        self.v.valueChanged.connect(partial(self.updateKwargs, "v"))
        layout.addWidget(self.v, 11, 2, 1, 1)
        layout.addWidget(QtWidgets.QLabel(QtWidgets.QApplication.translate(
            "pychemqt", "Enthalpy")), 12, 1, 1, 1)
        self.h = Entrada_con_unidades(unidades.Enthalpy)
        self.h.valueChanged.connect(partial(self.updateKwargs, "h"))
        layout.addWidget(self.h, 12, 2, 1, 1)
        layout.addItem(QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Fixed,
                                         QtWidgets.QSizePolicy.Fixed),13,1,1,2)

        self.setReadOnly(readOnly)
        self.updateInputs(0)
        if state:
            self.setState(state)

    def updateInputs(self, index):
        """Update inputs appearance to highlight active"""
        for par in self.parameters:
            self.__getattribute__(par).setReadOnly(True)
            self.__getattribute__(par).setResaltado(False)
        for par in PsyState.VAR_NAME[index]:
            self.__getattribute__(par).setReadOnly(False)
            self.__getattribute__(par).setResaltado(True)

        index = self.variables.currentIndex()
        kwargs = {"P": self.P.value}
        for par in PsyState.VAR_NAME[index]:
            if self.__getattribute__(par).value:
                kwargs[par] = self.state.__getattribute__(par)
        self.state = PsychroState(**kwargs)

    def setReadOnly(self, readOnly):
        self.checkPresion.setEnabled(not readOnly)
        self.checkAltitud.setEnabled(not readOnly)
        self.P.setReadOnly(readOnly)
        self.z.setReadOnly(readOnly)
        self.variables.setEnabled(not readOnly)
        for par in self.parameters:
            self.__getattribute__(par).setReadOnly(True)
            self.__getattribute__(par).setResaltado(False)

    def updateKwargs(self, key, value):
        """Update kwargs of state instance, if its correctly defined show it"""
        kwargs = {key: value}
        self.state(**kwargs)
        if self.state.status:
            self.setState(self.state)
            self.stateChanged.emit(self.state)

    def setState(self, state):
        """Fill data input with state properties"""
        self.state = state
        if state.w < state.ws:
            for par in self.parameters:
                self.__getattribute__(par).setValue(state.__getattribute__(par))

    def changePressure(self, value):
        """Change pressure to global plot and for states"""
        self.z.setValue(_height(value))
        self.state = PsychroState(P=value)
        self.pressureChanged.emit()

    def changeAltitude(self, value):
        """Change pressure through altitude and ICAO equation"""
        presion = _Pbar(value)
        self.P.setValue(presion)
        self.state = PsychroState(P=value)
        self.pressureChanged.emit()


class UI_Psychrometry(QtWidgets.QDialog):
    """Psychrometric charts tool"""
    def __init__(self, parent=None):
        super(UI_Psychrometry, self).__init__(parent)
        self.showMaximized()
        self.setWindowIcon(QtGui.QIcon(QtGui.QPixmap(os.environ["pychemqt"] +
            "/images/button/psychrometric.png")))
        self.setWindowTitle(QtWidgets.QApplication.translate(
            "pychemqt", "Psychrometric chart"))

        layout = QtWidgets.QGridLayout(self)
        self.diagrama2D = PsychroPlot(self, dpi=90)
        self.diagrama2D.fig.canvas.mpl_connect('motion_notify_event', self.scroll)
        self.diagrama2D.fig.canvas.mpl_connect('button_press_event', self.click)
        layout.addWidget(self.diagrama2D, 1, 3, 2, 2)

        self.inputs = PsychroInput()
        self.inputs.stateChanged.connect(self.createCrux)
        self.inputs.pressureChanged.connect(self.plot)
        layout.addWidget(self.inputs, 1, 1, 1, 1)
        layout.addItem(QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Expanding,
                                         QtWidgets.QSizePolicy.Expanding), 2, 1)

        self.buttonShowToolbox = QtWidgets.QToolButton()
        self.buttonShowToolbox.setCheckable(True)
        self.buttonShowToolbox.toggled.connect(self.showToolBar)
        layout.addWidget(self.buttonShowToolbox, 1, 2, 2, 1)
        self.line = QtWidgets.QFrame()
        self.line.setFrameShape(QtWidgets.QFrame.VLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(self.line, 1, 3, 3, 1)

        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setVisible(False)
        layout.addWidget(self.progressBar, 3, 3)
        self.status = QtWidgets.QLabel()
        layout.addWidget(self.status, 3, 3)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        butonPNG = QtWidgets.QPushButton(QtGui.QIcon(os.environ["pychemqt"] +
            "images"+os.sep+"button"+os.sep+"image.png"),
            QtWidgets.QApplication.translate("pychemqt", "Save as PNG"))
        self.buttonBox.addButton(butonPNG, QtWidgets.QDialogButtonBox.AcceptRole)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.accepted.connect(self.savePNG)
        layout.addWidget(self.buttonBox, 3, 4)

        self.showToolBar(False)
        self.plot()

    def savePNG(self):
        """Save chart image to png file"""
        fname = str(QtWidgets.QFileDialog.getSaveFileName(
            self, QtWidgets.QApplication.translate("pychemqt", "Save chart to file"),
            "./", "Portable Network Graphics (*.png)"))
        self.diagrama2D.fig.savefig(fname, facecolor='#eeeeee')

    def showToolBar(self, checked):
        """Show/Hide left toolbar with additional funcionality"""
        self.inputs.setVisible(not checked)
        if checked:
            image = "arrow-right-double.png"
        else:
            image = "arrow-left-double.png"
        self.buttonShowToolbox.setIcon(QtGui.QIcon(os.environ["pychemqt"] +
            "images"+os.sep+"button"+os.sep+image))

    def drawlabel(self, name, Preferences, t, W, label, unit):
        """
        Draw annotation for isolines
            name: name of isoline
            Preferences: Configparse instance of pychemqt preferences
            t: x array of line
            W: y array of line
            label: text value to draw
            unit: text units to draw
        """
        if Preferences.getboolean("Psychr", name+"label"):
            tmin = unidades.Temperature(Preferences.getfloat("Psychr", "isotdbStart")).config()
            tmax = unidades.Temperature(Preferences.getfloat("Psychr", "isotdbEnd")).config()
            x = tmax-tmin
            wmin = Preferences.getfloat("Psychr", "isowStart")
            wmax = Preferences.getfloat("Psychr", "isowEnd")
            y = wmax-wmin

            i = 0
            for ti, wi in zip(t, W):
                if tmin <= ti <= tmax and wmin <= wi <= wmax:
                    i += 1
            label = str(label)
            if Preferences.getboolean("Psychr", name+"units"):
                label += unit
            pos = Preferences.getfloat("Psychr", name+"position")
            p = int(i*pos/100-1)
            rot = arctan((W[p]-W[p-1])/y/(t[p]-t[p-1])*x)*360/2/pi
            self.diagrama2D.axes2D.annotate(label, (t[p], W[p]),
                rotation=rot, size="small", ha="center", va="center")

    def plot(self):
        """Plot chart"""
        Preferences = ConfigParser()
        Preferences.read(config.conf_dir+"pychemqtrc")

        self.diagrama2D.axes2D.clear()
        self.diagrama2D.config()
        filename = config.conf_dir+"%s_%i.pkl" % (
            PsychroState().__class__.__name__, self.inputs.P.value)
        if os.path.isfile(filename):
            with open(filename, "rb") as archivo:
                data = pickle.load(archivo)
                self.status.setText(QtWidgets.QApplication.translate(
                    "pychemqt", "Loading cached data..."))
                QtWidgets.QApplication.processEvents()
        else:
            self.progressBar.setVisible(True)
            self.status.setText(QtWidgets.QApplication.translate(
                "pychemqt", "Calculating data, be patient..."))
            QtWidgets.QApplication.processEvents()
            data = PsychroState.calculatePlot(self)
            pickle.dump(data, open(filename, "wb"))
            self.progressBar.setVisible(False)
        self.status.setText(QtWidgets.QApplication.translate("pychemqt", "Plotting..."))
        QtWidgets.QApplication.processEvents()

        tmax = unidades.Temperature(Preferences.getfloat("Psychr", "isotdbEnd"))

        t = [unidades.Temperature(ti).config() for ti in data["t"]]
        Hs = data["Hs"]
        format = {}
        format["ls"] = Preferences.get("Psychr", "saturationlineStyle")
        format["lw"] = Preferences.getfloat("Psychr", "saturationlineWidth")
        format["color"] = Preferences.get("Psychr", "saturationColor")
        format["marker"] = Preferences.get("Psychr", "saturationmarker")
        format["markersize"] = 3
        self.diagrama2D.plot(t, Hs, **format)

        format = {}
        format["ls"] = Preferences.get("Psychr", "isotdblineStyle")
        format["lw"] = Preferences.getfloat("Psychr", "isotdblineWidth")
        format["color"] = Preferences.get("Psychr", "isotdbColor")
        format["marker"] = Preferences.get("Psychr", "isotdbmarker")
        format["markersize"] = 3
        for i, T in enumerate(t):
            self.diagrama2D.plot([T, T], [0, Hs[i]], **format)

        H = data["H"]
        th = data["th"]
        format = {}
        format["ls"] = Preferences.get("Psychr", "isowlineStyle")
        format["lw"] = Preferences.getfloat("Psychr", "isowlineWidth")
        format["color"] = Preferences.get("Psychr", "isowColor")
        format["marker"] = Preferences.get("Psychr", "isowmarker")
        format["markersize"] = 3
        for i, H in enumerate(H):
            self.diagrama2D.plot([th[i], tmax.config()], [H, H], **format)

        format = {}
        format["ls"] = Preferences.get("Psychr", "isohrlineStyle")
        format["lw"] = Preferences.getfloat("Psychr", "isohrlineWidth")
        format["color"] = Preferences.get("Psychr", "isohrColor")
        format["marker"] = Preferences.get("Psychr", "isohrmarker")
        format["markersize"] = 3
        for Hr, H0 in list(data["Hr"].items()):
            self.diagrama2D.plot(t, H0, **format)
            self.drawlabel("isohr", Preferences, t, H0, Hr, "%")

        format = {}
        format["ls"] = Preferences.get("Psychr", "isotwblineStyle")
        format["lw"] = Preferences.getfloat("Psychr", "isotwblineWidth")
        format["color"] = Preferences.get("Psychr", "isotwbColor")
        format["marker"] = Preferences.get("Psychr", "isotwbmarker")
        format["markersize"] = 3
        for T, (H, Tw) in list(data["Twb"].items()):
            self.diagrama2D.plot(Tw, H, **format)
            value = unidades.Temperature(T).config()
            txt = unidades.Temperature.text()
            self.drawlabel("isotwb", Preferences, Tw, H, value, txt)

        format = {}
        format["ls"] = Preferences.get("Psychr", "isochorlineStyle")
        format["lw"] = Preferences.getfloat("Psychr", "isochorlineWidth")
        format["color"] = Preferences.get("Psychr", "isochorColor")
        format["marker"] = Preferences.get("Psychr", "isochormarker")
        format["markersize"] = 3
        for v, (Td, H) in list(data["v"].items()):
            self.diagrama2D.plot(Td, H, **format)
            value = unidades.SpecificVolume(v).config()
            txt = unidades.SpecificVolume.text()
            self.drawlabel("isochor", Preferences, Td, H, value, txt)

        self.diagrama2D.draw()
        self.status.setText(QtWidgets.QApplication.translate("pychemqt", "Using") +
                            " " + PsychroState().__class__.__name__[3:])

    def scroll(self, event):
        """Update graph annotate when mouse scroll over chart"""
        if event.xdata and event.ydata:
            punto = self.createState(event.xdata, event.ydata)
            if event.ydata < punto.ws:
                self.diagrama2D.showPointData(punto)
            else:
                self.diagrama2D.clearPointData()

    def click(self, event):
        """Update input and graph annotate when mouse click over chart"""
        if event.xdata and event.ydata:
            state = self.createState(event.xdata, event.ydata)
            if state.w <= state.ws:
                self.inputs.setState(state)
                self.createCrux(state)

    def createState(self, x, y):
        """Create psychrometric state from click or mouse position"""
        tdb = unidades.Temperature(x, "conf")
        punto = PsychroState(P=self.inputs.P.value, tdb=tdb, w=y)
        return punto

    def createCrux(self, state):
        """Update horizontal and vertical lines to show click point"""
        self.diagrama2D.lx.set_ydata(state.w)
        self.diagrama2D.ly.set_xdata(state.tdb.config())
        self.diagrama2D.draw()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    aireHumedo = UI_Psychrometry()
    aireHumedo.show()
    sys.exit(app.exec_())
