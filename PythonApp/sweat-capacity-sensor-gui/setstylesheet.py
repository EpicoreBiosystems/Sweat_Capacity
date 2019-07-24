"""=================================================================
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
====================================================================
"""

__author__ = "Jong Yoon Lee"
__license__ = "Apache"
__version__ = "0.1.0"
__email__ = "jongyoon.lee@sibelhealth.com"

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)


def setmainwindowStyle(MainWindow):
    MainWindow.setStyleSheet(_fromUtf8("background-color: rgb(d3,d3,d3);\n"
    "color: rgb(255, 255, 255);\n"
    "border-color: rgb(255, 255, 255);\n"
    "\n"
    ""))
def setLabelStyle(label, fontsize):
    label.setStyleSheet("color: #000000; \
                    background-color: rgb(d3, d3, d3);\
                    font-size:"+ str(fontsize) +"px;")
def setbuttonStyle(label, color):
    """set the botton style with color given"""
    label.setStyleSheet("background-color:" +color+"; text-align: center; \
    width:50px;\
    height:80px;\
    border-radius: 10%; \
    color: white; \
    font-size: 20px;")