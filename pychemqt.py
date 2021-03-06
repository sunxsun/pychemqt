#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""pychemqt, Chemical Engineering Process simulator
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
along with this program.  If not, see <http://www.gnu.org/licenses/>."""


import argparse
import logging
import os
import shutil
import sys
import urllib.error


# Parse command line options
desc = """pychemqt intended as a free software tool for calculation and \
design of chemical engineering unit operations."""
further = """For any suggestions, comments, bug ... you can contact me at \
https://github.com/jjgomera/pychemqt or by email jjgomera@gmail.com."""

parser = argparse.ArgumentParser(description=desc, epilog=further)
parser.add_argument("-l", "--log", dest="loglevel", default="INFO",
                    help="Set level of report in log file")
parser.add_argument("--debug", action="store_true",
                    help="Enable loglevel to debug, the more verbose option")
parser.add_argument("-n", "--nosplash", action="store_true",
                    help="Don't show the splash screen at start")
parser.add_argument("projectFile", nargs="*",
                    help="Optional pychemqt project files to load at startup")
args = parser.parse_args()


# Add pychemqt folder to python path
path = os.path.dirname(os.path.realpath(sys.argv[0]))
sys.path.append(path)

# Define pychemqt environment
os.environ["pychemqt"] = path + os.sep
conf_dir = os.path.expanduser("~") + os.sep + ".pychemqt" + os.sep

# Check mandatory external dependences
# PyQt5
try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError as err:
    print("PyQt5 could not be found, you must install it.")
    raise err

# Qt application definition
app = QtWidgets.QApplication(sys.argv)
app.setOrganizationName("pychemqt")
app.setOrganizationDomain("pychemqt")
app.setApplicationName("pychemqt")

# Translation
locale = QtCore.QLocale.system().name()
myTranslator = QtCore.QTranslator()
if myTranslator.load("pychemqt_" + locale, os.environ["pychemqt"] + "i18n"):
    app.installTranslator(myTranslator)
qtTranslator = QtCore.QTranslator()
if qtTranslator.load("qt_" + locale,
   QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.TranslationsPath)):
    app.installTranslator(qtTranslator)


# scipy
try:
    import scipy
except ImportError as err:
    msg = QtWidgets.QApplication.translate(
        "pychemqt", "scipy could not be found, you must install it.")
    print(msg)
    raise err
else:
    mayor, minor, corr = map(int, scipy.version.version.split("."))
    if minor < 14:
        msg = QtWidgets.QApplication.translate(
            "pychemqt",
            "Your version of scipy is too old, you must update it.")
        raise ImportError(msg)

# numpy
try:
    import numpy
except ImportError as err:
    msg = QtWidgets.QApplication.translate(
        "pychemqt", "numpy could not be found, you must install it.")
    print(msg)
    raise err
else:
    mayor, minor, corr = map(int, numpy.version.version.split("."))
    if mayor < 1 or minor < 8:
        msg = QtWidgets.QApplication.translate(
            "pychemqt",
            "Your version of numpy is too old, you must update it.")
        raise ImportError(msg)

# matplotlib
try:
    import matplotlib
except ImportError as err:
    msg = QtWidgets.QApplication.translate(
        "pychemqt", "matplotlib could not be found, you must install it.")
    print(msg)
    raise err
else:
    mayor, minor, corr = map(int, matplotlib.__version__.split("."))
    if mayor < 1 or minor < 4:
        msg = QtWidgets.QApplication.translate(
            "pychemqt",
            "Your version of matplotlib is too old, you must update it.")
        raise ImportError(msg)

# TODO: Disable python-graph external dependence, functional mock up in
# project yet useless
# python-graph
# try:
    # from pygraph.classes.graph import graph  # noqa
    # from pygraph.algorithms.cycles import find_cycle  # noqa
# except ImportError as err:
    # msg = QtWidgets.QApplication.translate(
        # "pychemqt", "Python-graph don't found, you need install it")
    # print(msg)
    # raise err


# Check external optional modules
from tools.dependences import optional_modules  # noqa
for module, use in optional_modules:
    try:
        __import__(module)
        os.environ[module] = "True"
    except ImportError:
        print("%s could not be found, %s" % (module, use))
        os.environ[module] = ""
    else:
        # Check required version
        if module == "CoolProp":
            import CoolProp.CoolProp as CP
            version = CP.get_global_param_string("version")
            mayor, minor, rev = map(int, version.split("."))
            if mayor < 6:
                print("Find CoolProp %s but CoolProp 6 required" % version)
                os.environ[module] = ""


# Logging configuration
if args.debug:
    loglevel = "DEBUG"
else:
    loglevel = args.loglevel
loglevel = getattr(logging, loglevel.upper())

# Checking config folder
if not os.path.isdir(conf_dir):
    os.mkdir(conf_dir)

try:
    open(conf_dir + "pychemqt.log", 'x')
except FileExistsError:  # noqa
    pass

fmt = "[%(asctime)s.%(msecs)d] %(levelname)s: %(message)s"
logging.basicConfig(filename=conf_dir+"pychemqt.log", filemode="w",
                    level=loglevel, datefmt="%d-%b-%Y %H:%M:%S", format=fmt)
logging.info(
    QtWidgets.QApplication.translate("pychemqt", "Starting pychemqt"))


class SplashScreen(QtWidgets.QSplashScreen):
    """Class to define a splash screen to show loading progress"""
    def __init__(self):
        QtWidgets.QSplashScreen.__init__(
            self,
            QtGui.QPixmap(os.environ["pychemqt"] + "/images/splash.jpg"))
        QtWidgets.QApplication.flush()

    def showMessage(self, msg):
        """Método para mostrar mensajes en la parte inferior de la ventana de
        splash"""
        align = QtCore.Qt.Alignment(QtCore.Qt.AlignBottom |
                                    QtCore.Qt.AlignRight |
                                    QtCore.Qt.AlignAbsolute)
        color = QtGui.QColor(QtCore.Qt.white)
        QtWidgets.QSplashScreen.showMessage(self, msg, align, color)
        QtWidgets.QApplication.processEvents()

    def clearMessage(self):
        QtWidgets.QSplashScreen.clearMessage(self)
        QtWidgets.QApplication.processEvents()

splash = SplashScreen()
if not args.nosplash:
    splash.show()


# Checking config files
from lib import firstrun  # noqa
splash.showMessage(QtWidgets.QApplication.translate(
    "pychemqt", "Checking config files..."))

# Checking config file
if not os.path.isfile(conf_dir + "pychemqtrc"):
    Preferences = firstrun.Preferences()
    Preferences.write(open(conf_dir + "pychemqtrc", "w"))

# FIXME: Hasta que no sepa como prescindir de este archivo sera necesario
if not os.path.isfile(conf_dir + "pychemqtrc_temporal"):
    Config = firstrun.config()
    Config.write(open(conf_dir + "pychemqtrc_temporal", "w"))

# Checking costindex
splash.showMessage(QtWidgets.QApplication.translate(
    "pychemqt", "Checking cost index..."))
if not os.path.isfile(conf_dir + "CostIndex.dat"):
        orig = os.path.join(os.environ["pychemqt"], "dat", "costindex.dat")
        with open(orig) as cost_index:
            lista = cost_index.readlines()[-1].split(" ")
            with open(conf_dir + "CostIndex.dat", "w") as archivo:
                for data in lista:
                    archivo.write(data.replace(os.linesep, "") + os.linesep)

# Checking currency rates
splash.showMessage(QtWidgets.QApplication.translate(
    "pychemqt", "Checking currency data"))
if not os.path.isfile(conf_dir + "moneda.dat"):
    try:
        firstrun.getrates(conf_dir + "moneda.dat")
    except urllib.error.URLError:
        origen = os.path.join(os.environ["pychemqt"], "dat", "moneda.dat")
        shutil.copy(origen, conf_dir + "moneda.dat")
        print(QtWidgets.QApplication.translate("pychemqt",
              "Internet connection error, using archived currency rates"))

# Checkin database with custom components
splash.showMessage(QtWidgets.QApplication.translate(
    "pychemqt", "Checking custom database..."))
from lib.sql import createDatabase  # noqa
if not os.path.isfile(conf_dir + "databank.db"):
    createDatabase(conf_dir + "databank.db")


# Import internal libraries
splash.showMessage(QtWidgets.QApplication.translate(
    "pychemqt", "Importing libraries..."))
from lib import *  # noqa
from UI import *  # noqa
from equipment import UI_equipments, equipments  # noqa
from tools import *  # noqa
from plots import *  # noqa


splash.showMessage(QtWidgets.QApplication.translate(
    "pychemqt", "Loading main window..."))
from UI.mainWindow import UI_pychemqt  # noqa
pychemqt = UI_pychemqt()

msg = QtWidgets.QApplication.translate("pychemqt", "Loading project files")
splash.showMessage(msg + "...")
logging.info(msg)

filename = []
if pychemqt.Preferences.getboolean("General", "Load_Last_Project"):
    filename = pychemqt.lastFile
    if filename is None:
        filename = []
for file in args.projectFile:
    filename.append(file)
for fname in filename:
    if fname and QtCore.QFile.exists(fname):
        msg = QtWidgets.QApplication.translate("pychemqt",
                                               "Loading project files...")
        splash.showMessage(msg + "\n" + fname)
        logging.info(msg + ": " + fname)
        pychemqt.fileOpen(fname)

pychemqt.show()
splash.finish(pychemqt)

sys.exit(app.exec_())
