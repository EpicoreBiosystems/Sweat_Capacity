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

import logging
import sys
from multiprocessing import Process
from threading import Lock, Thread, Timer

# import matplotlib.pyplot as plt
import numpy as np
import scipy as sp
import scipy.signal

from hmon.butter_filter import ButterBandpassFilter
from hmon.RR_accl import RR_agent
from sp_wrapper import SP_WRAPPER
from event_communicator import *


class SCGProcessingAgent(object):

    def __init__(self, data_queue, event_comm, graph_comm, data_logger):
        super(SCGProcessingAgent, self).__init__()

        #initalize variables
        self.event_comm = event_comm
        self.graph_comm = graph_comm
        self.data_logger = data_logger
        self.queue = data_queue

        self.update_freq = 5
        self.rr_agent = SP_WRAPPER(RR_agent())
        self.rr_agent_process = Process(target=self.rr_agent.start)
        self.rr_agent_process.start()

        self.rr_thread = Thread(target= self.rr_agent.listen_vital_signal_updates, args=(self.rr_value_update,))
        self.rr_thread.start()

        #initialize the data structure
        #the buffer is double buffered
        self.___buffer = np.zeros(shape=(2, 200), dtype=np.float32)

        self.___graph_buf = np.zeros(self.update_freq, dtype=np.float32)

        self.__mas_buf_cnt = 0
        self.__mas_graph_buf_cnt = 0

        self.__mas_counter  = 0
      
        self.scg_accum_graph = 0

        self.queue = data_queue

        # Real time filter
        self.rr_filter = ButterBandpassFilter(.1,1,100, order =2)

        self.clean_cnt = 0

    def rr_value_update(self, value):
        logging.info("RR Value Update with {}".format(value))
        # self.data_logger.write_hr(value)
        if value < 35 and value > 10:
            self.event_comm.post_event(QT_EVENT.UPDATE_RR, (int(value),))

    def loop(self):
        self.__process_data()    

    def __process_data(self):

        while True:
            scg = self.queue.get()
            #set output buffer
            if len(scg) == 0:
                return


            processed = self.rr_filter.filter(scg)

            averaged_rr = [np.average(processed)]
            self.clean_cnt +=1
            if self.clean_cnt > 120:
                self.graph_comm.update_graph( 3, (averaged_rr, 1))


            self.rr_agent.feed_data(averaged_rr)
            # output_buf_cnt = 1 - self.__mas_buf_cnt

            # #processed data init
            # scg_processed = self.___buffer[output_buf_cnt][self.__mas_counter:self.__mas_counter+5]

            # #update graph buffer
            # self.___graph_buf[self.__mas_graph_buf_cnt] = 0
            # for i in range(0, 3):
            #     self.___graph_buf[self.__mas_graph_buf_cnt] = scg_processed[i]
            # self.__mas_graph_buf_cnt += 1
            #     # self.scg_accum_graph += scg_processed[i]

            # if self.__mas_graph_buf_cnt == self.update_freq:
            #     self.__mas_graph_buf_cnt = 0

            #     # self.graph_update_func( [self.scg_accum_graph], 1)
            #     # self.graph_update_func( self.___graph_buf, self.update_freq)
            #     self.graph_comm.update_graph( 2, (self.___graph_buf, self.update_freq))
            #     self.scg_accum_graph = 0

            # # for signal processings
            # for index in range(0, 3):
            #     self.___buffer[self.__mas_buf_cnt][index+ self.__mas_counter] = scg[index]

            # #update local time
            # self.__mas_counter += 3

            # #apply sg filter
            # if self.__mas_counter == 200:
            #     self.___buffer[self.__mas_buf_cnt] = sp.signal.savgol_filter(self.___buffer[self.__mas_buf_cnt], 31, 5)
            #     self.__mas_buf_cnt = output_buf_cnt
            #     self.__mas_counter = 0
