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

#pylint: disable=E1101
import sys
import os.path as osp
import logging
from PyQt4 import QtCore, QtGui
from event_communicator import BLE_EVENT

#setting the path variable for icon
titleicon = osp.join(osp.dirname(sys.modules[__name__].__file__), 'img/heart.jpg')
itemicon = osp.join(osp.dirname(sys.modules[__name__].__file__), 'img/pulse2.png')


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


class ConnectWindow(QtGui.QDialog):

    button_status_signal = QtCore.pyqtSignal(object)
    master_item_add_signal = QtCore.pyqtSignal(object)
    slave_item_add_signal = QtCore.pyqtSignal(object)
    def __init__(self, event_comm, parent=None):
        super(ConnectWindow, self).__init__(parent)

        self.event_comm = event_comm
        self.parent = parent

        self.button_status_signal.connect(self.ChangebuttonStatus)
        self.master_item_add_signal.connect(self.append_to_master_list)

        self.master_device = QtGui.QListWidgetItem("")

        self.master_device_text = ""

        self.windowopen = False
        #get the window size control object
        self.setWindowTitle('Bluetooth Connect')
        self.setWindowIcon(QtGui.QIcon(titleicon))
        self.resize(400, 300)
        listfont = QtGui.QFont("Helvetica", 15)
        itemfont = QtGui.QFont("Arial Narrow", 15)

        #initialize list for the device to show up
        self.master_list = QtGui.QListWidget(self)
        self.master_list.itemClicked.connect(self.master_select_func)
        self.master_list.setFont(itemfont)

        self.master_connect_button = False

        #Add devicename text
        self.mastertext = QtGui.QLabel("<center>Sensor</center>")
        self.mastertext.setFont(listfont)
        self.mastertext.setStyleSheet("color:#000000")

        #Add buttons
        self.master_connect = QtGui.QPushButton()
        self.master_connect.clicked.connect(self.master_connect_func)

        self.master_connect.setText(_translate("MainWindow", "Connect", None))
        self.master_connect.setStyleSheet("background-color: #008CBA; text-align: center; \
        width:50px;\
        height:50px;\
        border-radius: 10%; \
        color: white; \
        font-size: 15px;")

        self.master_button_status = 0

        #Add to boxes
        self.master_window = QtGui.QVBoxLayout(self)

        self.master_window.addWidget(self.mastertext)
        self.master_window.addWidget(self.master_list)
        self.master_window.addWidget(self.master_connect)

    def closeEvent(self, event):
        logging.debug("Close Event")
        self.windowopen = False

        self.parent.log_func()
        self.event_comm.post_event(BLE_EVENT.STOPADVERTISE, (None,))

    def append_to_master_list(self, device):
        """append to the current list of advertisint master device list"""
        item = QtGui.QListWidgetItem(device)
        item.setIcon(QtGui.QIcon(itemicon))
        item.setTextAlignment(QtCore.Qt.AlignHCenter)
        item.setTextColor(QtGui.QColor(0, 0, 0))
        self.master_list.addItem(item)

    def master_select_func(self, item):
        """set the selected device to interal variable"""
        try:
            self.master_device.setTextColor(QtGui.QColor(0, 0, 0))
        except:
            pass
        item.setTextColor(QtGui.QColor(255, 87, 51))
        logging.info("Chest Select Func Device: {}".format(str(item.text())))
        self.master_device = item

    def master_connect_func(self):

        """connect to the currely selected master device"""
        if self.master_connect.text() == "Connected" :
            self.event_comm.post_event(BLE_EVENT.DISCONECT,(0,))
            self.master_device_text = ""

            #change the to disconnect mode
            self.button_status_signal.emit((0,0))
        elif self.master_button_status == 0:
            logging.debug("Connecting button pressed for: {} with the connection status: {}".format(self.master_device.text(),self.master_connect.text()))
            if self.master_device.text() != "":
                self.event_comm.post_event(BLE_EVENT.CONNECT, (0, self.master_device.text()))

                #change the to connection mode
                self.button_status_signal.emit((0,1))

    def ChangebuttonStatus(self, data):
        """
            input: button_num:  master = 0
                                slave  = 1

                   status:      disconnected = 0
                                connecting   = 1
                                connected    = 2
        """
        text = ""
        color = ""
        button_num = data[0]
        status = data[1]
        logging.info("Change button %d to status %d", button_num, status)

        if button_num == 0:
            if status == 0:
                #change status
                self.master_button_status = 0
                text = "Connect"
                color = "#008CBA"
                try:
                     self.master_device.setTextColor(QtGui.QColor(255, 255, 255))
                except:
                    pass
            elif status == 1:
                #change status
                self.master_button_status = 1
                text = "Connecting"
                color = "#ffb366"
            elif status == 2 and self.master_button_status == 1:
                #change status
                self.master_button_status = 2
                text = "Connected"
                color = "#16A085"
            if text != "":
                self.master_connect.setText(_translate("MainWindow", text, None))
                self.master_connect.setStyleSheet("background-color: "+color+"; text-align: center; \
                width:100px;\
                height:100px;\
                border-radius: 10%; \
                color: white; \
                font-size: 40px;")

    def clear_master(self):
        """clear the master list"""
        self.master_list.clear()
