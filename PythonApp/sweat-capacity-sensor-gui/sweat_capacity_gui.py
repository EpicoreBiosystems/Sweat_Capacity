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

# -*- coding: utf-8 -*-

import logging
import sys, time
import os, csv
from multiprocessing import Process
from threading import Thread
from functools import partial

import numpy as np
# Form implementation generated from reading ui file 'prosthetic_gui.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!
import pyqtgraph as pg
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from connectWindow import ConnectWindow
from event_communicator import *
from graph import Graph
from graph_communicator import GraphCommunicator
from setstylesheet import *

DATA_FILE_PATH = 'Datafiles'

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

class NICU_GUI(QtGui.QMainWindow):

    disconnect_signal = QtCore.pyqtSignal(tuple)
    bt_connect_signal = QtCore.pyqtSignal(tuple)
    exit_bt = QtCore.pyqtSignal(tuple)

    update_graph_signal = QtCore.pyqtSignal(tuple)	

    def __init__(self, event_comm, graph_comm):
        super(NICU_GUI, self).__init__()

        self.event_comm = event_comm
        self.graph_comm = graph_comm

        #Get current screen resolution
        geometry = QtGui.QDesktopWidget().screenGeometry()

        #connection window object
        self.connect_window = ConnectWindow(event_comm, self)
        self.setupUi()

        #initalize signals
        self.disconnect_signal.connect(self.on_bt_disconnect)
        self.bt_connect_signal.connect(self.bt_connect_func)
        self.exit_bt.connect(self.exit_button_func)
        
        self.update_graph_signal.connect(self.update_graph_func) 		

        # Add necessary events to communicator
        self.event_comm.add_event(QT_EVENT.UPDATE_BUTTON_STATUS, self.connect_window.button_status_signal.emit)
        self.event_comm.add_event(QT_EVENT.UPDATE_M_LIST, self.connect_window.master_item_add_signal.emit)
        self.event_comm.add_event(QT_EVENT.UPDATE_S_LIST, self.connect_window.slave_item_add_signal.emit)
        self.event_comm.add_event(QT_EVENT.DISCONNECT, self.disconnect_signal.emit)
        self.event_comm.add_event(QT_EVENT.EXIT, self.exit_bt.emit)
        self.event_comm.add_event(QT_EVENT.BT_CONNECTED, self.bt_connect_signal.emit)
		
        self.event_comm.add_event(QT_EVENT.UPDATE_GRAPH, self.update_graph_signal.emit)		
        self.graph_comm.add_graph(1, self.graph_1.updateData)

        self.event_thread = Thread(target=self.event_comm.start_event_handler, args=(PROCESS.QT,))
        self.event_thread.start()

        self.graph_event_thread = Thread(target=self.graph_comm.listen_graph_updates)
        self.graph_event_thread.start()

        # self.logger = logger()

        self.hrqueue = []
        self.spo2queue = []
		
        self.sensor_channel1_enabled = 0
        self.sensor_channel1_channel = 0		
        self.sensor_channel1_capdac_value = 0
        self.sensor_channel1_fine_offset_value = 0
		
        self.sensor_channel2_enabled = 0
        self.sensor_channel2_channel = 1
        self.sensor_channel2_capdac_value = 12
        self.sensor_channel2_fine_offset_value = 0
		
        # Sampling rate of 100Hz, fixed for highest ADC resolution
        self.sampling_rate = 1 
		
        self.sensing_interval = 10
		
        self.data_storage_file = None
        self.csvwriter = None
		
        self.logging = False
        self.graph_reset_timer = 0

        self.graph_timer = QtCore.QTimer()
        self.graph_timer.timeout.connect(self.timer_func)
        self.graph_timer.start(1000)

    def setupUi(self):

        # Remove title bar
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint )

        #Main window setting
        self.setObjectName(_fromUtf8("MainWindow"))
        setmainwindowStyle(self)

        #central widget init
        self.centralwidget = QtGui.QWidget(self)
        self.centralwidget.setContentsMargins(0,0,0,0)
        self.centralwidget.setEnabled(True)
        self.centralwidget.setWindowFlags(QtCore.Qt.CustomizeWindowHint)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))

        #Set title of the application
        self.title = QtGui.QLabel(self.centralwidget)
        self.title.setObjectName(_fromUtf8("label"))
        self.title.setText(_translate("MainWindow", "Sweat Capactiy Sensor BLE Interface", None))
        setLabelStyle(self.title, 30) 

        self.GraphLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.GraphLayout.setSpacing(5)
        self.GraphLayout.setObjectName(_fromUtf8("verticalLayout_2"))
        self.GraphLayout.addWidget(self.title)

        # Add the graph objects
        self.graph_1 = Graph(self.centralwidget, 'Sweat Capacity', '#24a54f', 100, False)
        self.GraphLayout.addWidget(self.graph_1.getGraph())

        # Add buttons 
        self.ButtonLayout = QtGui.QGridLayout()
        self.frame = QFrame()
        self.frame.setLayout(self.ButtonLayout)
        
        # Configure button
        self.sensing_cfg_button = QtGui.QPushButton()
        self.ButtonLayout.addWidget(self.sensing_cfg_button, *(0,0))
        self.sensing_cfg_button.clicked.connect(self.sensing_cfg_button_func)		
        self.sensing_cfg_button.setText(_translate("MainWindow", "Configure", None))
        setbuttonStyle(self.sensing_cfg_button, "#008CBA")
		
        # Start button
        self.sensing_start_button = QtGui.QPushButton()
        self.ButtonLayout.addWidget(self.sensing_start_button, *(0,1))
        self.sensing_start_button.clicked.connect(self.sensing_start_button_func)        		
        self.sensing_start_button.setText(_translate("MainWindow", "Start", None))		
        setbuttonStyle(self.sensing_start_button, "#008CBA")
		
        # Stop button
        self.sensing_stop_button = QtGui.QPushButton()
        self.ButtonLayout.addWidget(self.sensing_stop_button, *(0,2))
        self.sensing_stop_button.clicked.connect(self.sensing_stop_button_func)		
        self.sensing_stop_button.setText(_translate("MainWindow", "Stop", None))
        setbuttonStyle(self.sensing_stop_button, "#008CBA")
		
        #init connect Button
        self.connect_button = QtGui.QPushButton()
        self.ButtonLayout.addWidget(self.connect_button, *(0,3))
        self.connect_button.setText(_translate("MainWindow", "Initializing", None))
        setbuttonStyle(self.connect_button, "#FFB90F")

        #init exit Button
        self.exit_button = QtGui.QPushButton()
        self.ButtonLayout.addWidget(self.exit_button, *(0,4))
        self.exit_button.clicked.connect(self.exit_button_func)
        self.exit_button.setText(_translate("MainWindow", "Exit", None))
        setbuttonStyle(self.exit_button, "#F08080")

        # Add pull down menus
        self.interval_label = QtGui.QLabel()
        self.interval_label.setText("Sampling Interval (Seconds)")		
        self.interval_label.setStyleSheet("color:black")
        self.interval_list = QtGui.QComboBox()
        self.interval_list.setMaximumWidth(100)		
        self.interval_list.addItems(["10", "20", "30", "60"])
        self.interval_list.currentIndexChanged.connect(self.intervalSelectionchange)
        self.interval_list.setStyleSheet("color:white; background-color:grey; selection-color:white; selection-background-color:blue")		
#        self.interval_list.setGeometry(QtCore.QRect(5, 5, 30, 20))

        # self.channel1_capdac_label = QtGui.QLabel()
        # self.channel1_capdac_label.setText("Channel 1 CAPDAC (0-31)")
        # self.channel1_capdac_label.setStyleSheet("color:black")
        # self.channel1_capdac_text = QtGui.QTextEdit()
        # self.channel1_capdac_text.setText("0")

        self.channel1_enabled_label = QtGui.QLabel()
        self.channel1_enabled_label.setText("Channel 1")		
        self.channel1_enabled_label.setStyleSheet("color:black")
        self.channel1_enabled_list = QtGui.QComboBox()
        self.channel1_enabled_list.addItems(["Disabled", "Enabled"])
        self.channel1_enabled_list.currentIndexChanged.connect(self.channel1_enable_selection_changed)
        self.channel1_enabled_list.setStyleSheet("color:white; background-color:grey; selection-color:white; selection-background-color:blue")		
		
        self.channel1_capdac_label = QtGui.QLabel()
        self.channel1_capdac_label.setText("     Channel 1 CAPDAC (0-31)")
        self.channel1_capdac_label.setStyleSheet("color:black")
		
        self.channel1_capdac = QtGui.QLineEdit("0")
        self.channel1_capdac.setValidator(QIntValidator(0, 31))
        self.channel1_capdac.setMaxLength(2)
        self.channel1_capdac.setAlignment(Qt.AlignRight)
        self.channel1_capdac.setStyleSheet("color:white; background-color:grey; selection-color:white; selection-background-color:blue")		
        self.channel1_capdac.textChanged.connect(self.channel1_capdac_changed)	
				
        self.channel2_enabled_label = QtGui.QLabel()
        self.channel2_enabled_label.setText("Channel 2")		
        self.channel2_enabled_label.setStyleSheet("color:black")
        self.channel2_enabled_list = QtGui.QComboBox()
        self.channel2_enabled_list.addItems(["Disabled", "Enabled"])
        self.channel2_enabled_list.currentIndexChanged.connect(self.channel2_enable_selection_changed)
        self.channel2_enabled_list.setStyleSheet("color:white; background-color:grey; selection-color:white; selection-background-color:blue")		

        self.channel2_capdac_label = QtGui.QLabel()		
        self.channel2_capdac_label.setText("     Channel 2 CAPDAC (0-31)")
        self.channel2_capdac_label.setStyleSheet("color:black")
		
        self.channel2_capdac = QtGui.QLineEdit("12")
        self.channel2_capdac.setValidator(QIntValidator(0, 31))
        self.channel2_capdac.setMaxLength(2)
        self.channel2_capdac.setAlignment(Qt.AlignRight)
        self.channel2_capdac.setStyleSheet("color:white; background-color:grey; selection-color:white; selection-background-color:blue")		
        self.channel2_capdac.textChanged.connect(self.channel2_capdac_changed)	

        self.channel1_fine_offset_label = QtGui.QLabel()
        self.channel1_fine_offset_label.setText("     Channel 1 Fine Offset (0-5)")
        self.channel1_fine_offset_label.setStyleSheet("color:black")

        self.channel1_fine_offset = QtGui.QLineEdit("0")
        self.channel1_fine_offset.setValidator(QIntValidator(0, 5))
        self.channel1_fine_offset.setMaxLength(1)
        self.channel1_fine_offset.setAlignment(Qt.AlignRight)
        self.channel1_fine_offset.setStyleSheet("color:white; background-color:grey; selection-color:white; selection-background-color:blue")		
        self.channel1_fine_offset.textChanged.connect(self.channel1_fine_offset_changed)	

        self.channel2_fine_offset_label = QtGui.QLabel()
        self.channel2_fine_offset_label.setText("     Channel 2 Fine Offset (0-5)")
        self.channel2_fine_offset_label.setStyleSheet("color:black")
		
        self.channel2_fine_offset = QtGui.QLineEdit("0")
        self.channel2_fine_offset.setValidator(QIntValidator(0, 5))
        self.channel2_fine_offset.setMaxLength(1)
        self.channel2_fine_offset.setAlignment(Qt.AlignRight)
        self.channel2_fine_offset.setStyleSheet("color:white; background-color:grey; selection-color:white; selection-background-color:blue")		
        self.channel2_fine_offset.textChanged.connect(self.channel2_fine_offset_changed)	
		
        self.interval_layout = QtGui.QHBoxLayout()
        self.interval_layout.setAlignment(Qt.AlignLeft)		
        self.interval_frame = QFrame()		
        self.interval_frame.setLayout(self.interval_layout)		
		
        self.sensor_channel1_cfg_layout = QtGui.QHBoxLayout()
        self.sensor_channel1_cfg_frame = QFrame()		
        self.sensor_channel1_cfg_frame.setLayout(self.sensor_channel1_cfg_layout)		
        self.sensor_channel2_cfg_layout = QtGui.QHBoxLayout()
        self.sensor_channel2_cfg_frame = QFrame()		
        self.sensor_channel2_cfg_frame.setLayout(self.sensor_channel2_cfg_layout)		

        self.interval_layout.addWidget(self.interval_label) 		
        self.interval_layout.addWidget(self.interval_list)   

        self.sensor_channel1_cfg_layout.addWidget(self.channel1_enabled_label)
        self.sensor_channel1_cfg_layout.addWidget(self.channel1_enabled_list)
        self.sensor_channel1_cfg_layout.addWidget(self.channel1_capdac_label)
        self.sensor_channel1_cfg_layout.addWidget(self.channel1_capdac)
        self.sensor_channel1_cfg_layout.addWidget(self.channel1_fine_offset_label)
        self.sensor_channel1_cfg_layout.addWidget(self.channel1_fine_offset)
		
        self.sensor_channel2_cfg_layout.addWidget(self.channel2_enabled_label)
        self.sensor_channel2_cfg_layout.addWidget(self.channel2_enabled_list)
        self.sensor_channel2_cfg_layout.addWidget(self.channel2_capdac_label)
        self.sensor_channel2_cfg_layout.addWidget(self.channel2_capdac)
        self.sensor_channel2_cfg_layout.addWidget(self.channel2_fine_offset_label)
        self.sensor_channel2_cfg_layout.addWidget(self.channel2_fine_offset)
				
        self.GraphLayout.addWidget(self.interval_frame)
        self.GraphLayout.addWidget(self.sensor_channel1_cfg_frame)		
        self.GraphLayout.addWidget(self.sensor_channel2_cfg_frame)
        self.GraphLayout.addWidget(self.frame)

        self.setCentralWidget(self.centralwidget)

        self.resize(800, 500)
        self.show()
		
    def open_data_storage_file(self):
        if not os.path.exists(DATA_FILE_PATH):
            os.makedirs(DATA_FILE_PATH)
		        
        timestr = time.strftime('%Y-%m-%dT%H-%M-%S', time.localtime())
        recording_file_name = 'Sweat_Capacity_' + timestr + '.csv'
        recording_dir = os.path.join(os.getcwd(), DATA_FILE_PATH)

        recording_file_fullname = os.path.join(recording_dir, recording_file_name)
#        print(recording_file_fullname)		 
        self.data_storage_file = open(recording_file_fullname, 'w')

        columns = ['timestamp (sec)', 'channel_1_capacitance (pF)', 'channel_1_capacitance_raw', 'channel_2_capacitance (pF)', 'channel_2_capacitance_raw']
        self.csvwriter = csv.DictWriter(self.data_storage_file, columns, lineterminator='\n') 
        self.csvwriter.writeheader()
		
    def channel1_capdac_changed(self, i):
        self.sensor_channel1_capdac_value = int(i) 	
#        print "Current channel 1 CAPDAC: ", self.sensor_channel1_capdac_value
		
    def channel2_capdac_changed(self, i):
        self.sensor_channel2_capdac_value = int(i) 	
#        print "Current channel 2 CAPDAC: ", self.sensor_channel2_capdac_value

    def channel1_fine_offset_changed(self, i):
        self.sensor_channel1_fine_offset_value = int(i) 	
#        print "Current channel 1 fine offset: ", self.sensor_channel1_fine_offset_value

    def channel2_fine_offset_changed(self, i):
        self.sensor_channel2_fine_offset_value = int(i) 	
#        print "Current channel 2 fine offset: ", self.sensor_channel2_fine_offset_value
		
    def intervalSelectionchange(self, i):
        self.sensing_interval = int(self.interval_list.currentText()) 	
#        print "Current sensing interval: ", self.sensing_interval		

    def channel1_enable_selection_changed(self, i):
        self.sensor_channel1_enabled = i 	
#        print "Current channel 1 status  ", self.sensor_channel1_enabled		
		
    def channel2_enable_selection_changed(self, i):
        self.sensor_channel2_enabled = i 	
#        print "Current channel 2 status  ", self.sensor_channel2_enabled
		
    @pyqtSlot(tuple)
    def bt_connect_func(self):
        self.connect_button.clicked.connect(self.ConnectButton)
        setbuttonStyle(self.connect_button, "#008CBA")
        self.connect_button.setText(_translate("MainWindow", "Bluetooth", None))

        # Only create the sensor data storage file after the dongle is connected
        self.open_data_storage_file()

    def exit_button_func(self):
        # self.showdialog()

        if self.data_storage_file is not None:
            self.data_storage_file.flush()		
            self.data_storage_file.close()

        self.event_comm.post_event(BLE_EVENT.EXIT)
        self.graph_comm.update_graph(-1, [])
        self.event_thread.join()
        self.graph_event_thread.join()

        sys.exit()

    def tag_event(self, name):
        self.event_comm.post_event(BLE_EVENT.TAG_EVENT,(name,))

    def log_func(self):
        logging.debug("Logging button pressed")
        if self.logging is False:
            self.logging = True

            self.event_comm.post_event(BLE_EVENT.STARTLOGGING,(None,))
        else:
            self.logging = False
            self.event_comm.post_event(BLE_EVENT.STOPLOGGING,(None,))

    @pyqtSlot(tuple)
    def on_bt_disconnect(self, args):

        logging.info("GUI disconnect func device_type: {}".format(args[0]))

        self.clear_graph(args[0])
#        self.clear_vital_signals(args[0])
#        self.event_comm.post_event(QT_EVENT.UPDATE_BUTTON_STATUS, (args[0],0))

    def clear_graph(self, device_type):
        if device_type == 0:
            self.graph_1.clear_graph()
			
    def ConnectButton(self):
        if self.logging is True: 
            self.log_func()
        self.connect_window.clear_master()
        logging.debug("Connect button")

        self.event_comm.post_event(BLE_EVENT.STARTADVERTISE, None)
        logging.debug("Passed advertising")
        self.connect_window.windowopen = True
        self.connect_window.exec_()

    def sensing_start_button_func(self):
        self.event_comm.post_event(BLE_EVENT.STARTSENSING, (self.sensing_interval, ))
		
    def sensing_stop_button_func(self):
        self.event_comm.post_event(BLE_EVENT.STOPSENSING)
		
    def sensing_cfg_button_func(self):
        sensing_cfgs = (self.sampling_rate, 
                        self.sensor_channel1_enabled, self.sensor_channel1_channel, 
                        self.sensor_channel1_capdac_value, self.sensor_channel1_fine_offset_value,
                        self.sensor_channel2_enabled, self.sensor_channel2_channel, 
                        self.sensor_channel2_capdac_value, self.sensor_channel2_fine_offset_value, 						
						)
        self.event_comm.post_event(BLE_EVENT.CONFIGSENSING, sensing_cfgs)

    def capacitance_conversion(self, channel, capacitance_raw):
        if channel == 1:
            capacitance = (float(capacitance_raw))/(1<<19) + 3.125*self.sensor_channel1_capdac_value + self.sensor_channel1_fine_offset_value   	
        if channel == 2:
            capacitance = (float(capacitance_raw))/(1<<19) + 3.125*self.sensor_channel2_capdac_value + self.sensor_channel2_fine_offset_value
        
        return capacitance
		
    def update_graph_func(self, args):
        graph_num = args[0]
		
        timeStamp = args[1]
		
        capacitance_raw_array = args[2]
        print "Raw capacitance: ", capacitance_raw_array
		
        channel1_capacitance_converted = self.capacitance_conversion(1, capacitance_raw_array[0])
        channel2_capacitance_converted = self.capacitance_conversion(2, capacitance_raw_array[1])
		
        capacitance_converted_array = [channel1_capacitance_converted, channel2_capacitance_converted]		
        print "Converted capacitance: ", capacitance_converted_array
		
		# Store new data to local file
        capacity_row = {
            'timestamp (sec)': '%d' % timeStamp,
            'channel_1_capacitance (pF)': '%f' % capacitance_converted_array[0],
            'channel_1_capacitance_raw': '%d' % capacitance_raw_array[0],							
            'channel_2_capacitance (pF)': '%f' % capacitance_converted_array[1],
            'channel_2_capacitance_raw': '%d' % capacitance_raw_array[1]							
        } 
		
        if self.data_storage_file is not None and self.csvwriter is not None:
            self.csvwriter.writerow(capacity_row)
            self.data_storage_file.flush()
					
		# Update graph with new data samples		
        data_len = len(capacitance_converted_array)		
        self.graph_comm.update_graph(graph_num, [capacitance_converted_array, data_len])	
		
    def timer_func(self):		
        self.graph_1.updateGraph() 
        if (self.graph_1.cur_pos > self.graph_1.range):
                self.graph_1.cur_pos = 0
