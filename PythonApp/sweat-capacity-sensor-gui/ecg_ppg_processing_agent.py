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

import numpy as np
from time import localtime, strftime, time
from threading import Lock, Thread, Timer
from multiprocessing import Process
import logging

from hmon.HR import HR_agent
from hmon.SPO2 import SPO2_agent
from hmon.PTT import PTT_agent
from hmon.butter_filter import ButterBandpassFilter
from hmon.tools.ampd import PPD_agent
from sp_wrapper import SP_WRAPPER

from event_communicator import *


ECG_SAMPLING_RATE = 504 # Hz
ECG_SAMPLING_INTERVAL = 1.98358074885
PPG_SAMPLING_RATE = 100 # Hz
PPG_SAMPLING_INTERVAL = 9.99734861561
BATCH_SIZE = 5 #in seconds

class PeriodicTask(object):
    def __init__(self, interval, callback, daemon=True, **kwargs):
        self.interval = interval
        self.callback = callback
        self.daemon   = daemon
        self.kwargs   = kwargs

    def run(self):
        self.callback(**self.kwargs)
        t = Timer(self.interval, self.run)
        t.daemon = self.daemon
        t.start()

class ECG_PPG_ProcessingAgent(object):

    def __init__(self, ecg_queue,ppg_queue, event_comm, graph_comm, data_logger):
        super(ECG_PPG_ProcessingAgent, self).__init__()
        #initalize variables
        self.___buffer = np.zeros(shape=(2, 200), dtype=np.float32)
        self.update_freq = 5
        self.__mas_buf_cnt = 0
        self.__mas_graph_buf_cnt = 0
        self.__mas_counter  = 0

        self.event_comm = event_comm
        self.graph_comm = graph_comm
        self.data_logger = data_logger
        self.ecg_queue = ecg_queue
        self.ppg_queue = ppg_queue

        self.ecg = []
        self.red = []
        self.ir = []
        self.index = -1

        self.peak_s_conn , self.peak_e_conn = Pipe()

        # Create signal processing agents
        logging.info("HR Signal Processing Agent Spawning")
        self.hr_agent = SP_WRAPPER(HR_agent(peak_conn = self.peak_s_conn))
        self.hr_agent_process = Process(target=self.hr_agent.start)
        self.hr_agent_process.start()

        logging.info("SPO2 Signal Processing Agent Spawning")
        self.spo2_agent = SP_WRAPPER(SPO2_agent())
        self.spo2_agent_process = Process(target=self.spo2_agent.start)
        self.spo2_agent_process.start()

        logging.info("PTT Signal Processing Agent Spawning")
        self.ptt_agent = SP_WRAPPER(PTT_agent(self.peak_e_conn))
        self.ptt_agent_process = Process(target=self.ptt_agent.start)
        self.ptt_agent_process.start()

        # Create threads to listen to value updates
        self.hr_thread = Thread(target= self.hr_agent.listen_vital_signal_updates, args=(self.hr_value_update,))
        self.hr_thread.start()
        self.spo2_thread = Thread(target= self.spo2_agent.listen_vital_signal_updates, args=(self.spo2_value_update,))
        self.spo2_thread.start()
        self.ptt_thread = Thread(target= self.ptt_agent.listen_vital_signal_updates, args=(self.ptt_value_update,))
        self.ptt_thread.start()

        self.ecg_filter = ButterBandpassFilter(8,60,504)
        self.ppg_filter = ButterBandpassFilter(.5,8,100)

    def hr_value_update(self, value):
        logging.info("HR Value Update with {}".format(value))
        self.data_logger.write_hr(value)
        self.event_comm.post_event(QT_EVENT.UPDATE_HR, (int(value),))

    def spo2_value_update(self, value):
        logging.info("HR Value Update with {}".format(value))
        self.data_logger.write_spo2(value)
        if value > 70:
            self.event_comm.post_event(QT_EVENT.UPDATE_SPO2, (int(round(value)),))
        else:
            self.event_comm.post_event(QT_EVENT.UPDATE_SPO2, (-1,))

    def ptt_value_update(self, value):
        logging.info("HR Value Update with {}".format(value))
        self.event_comm.post_event(QT_EVENT.UPDATE_PTT, (str(int(value)),))
        self.graph_comm.update_graph( 4, ((value,),1))  
        self.data_logger.write_pat(value)


    def ecg_loop(self):
        self.__process_ecg()
    def ppg_loop(self):
        self.__process_ppg()

    def __process_ecg(self):
        while True: 
            ecg = self.ecg_queue.get()

            if len(ecg) == 0:
                return
            processed = self.ecg_filter.filter(ecg)
            #update graph buffer
            ecg_graph_1 = max(processed[:5])
            ecg_graph_2 = max(processed[5:])
            self.graph_comm.update_graph( 1, ((ecg_graph_1,ecg_graph_2,),2))             

            self.hr_agent.feed_data(ecg)

    def __process_ppg(self):
        while True:
            red_buf, ir_buf = self.ppg_queue.get()

            if len(red_buf) == 0:
                return

            #update graph, Only Update red

            processed = self.ppg_filter.filter(ir_buf)
            inverted  = 2**16 - processed
            self.graph_comm.update_graph( 2, (inverted, 5))

            ppg = (red_buf, ir_buf)
            self.spo2_agent.feed_data(ppg)
            self.ptt_agent.feed_data(ir_buf)