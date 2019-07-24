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
__license__ = "MIT"
__version__ = "1"
__email__ = "jongyoon.lee@sibelhealth.com"

import logging
import Queue
import sys
import time
from multiprocessing import Process, freeze_support
from threading import Lock, Thread, Timer

import numpy as np
from pc_ble_driver_py import exceptions as e
from pc_ble_driver_py import config
from pc_ble_driver_py.observers import *
import ctypes as c

from event_communicator import *
from graph_communicator import GraphCommunicator

CONNECTIONS = 1

# Command list
CMD_CONFIG_SENSOR       = 0x41 # Config sensor sampling parameters
CMD_START_DATA_STREAM   = 0x42 # Start sending sweat data stream to host
CMD_STOP_DATA_STREAM    = 0x43 # Stop sending sweat data stream to host
CMD_SET_TIME            = 0x44 # Set sensor date/time
CMD_GET_TIME            = 0x45 # Get sensor date/time
CMD_GET_FW_INFO         = 0x58 # Get sensor firmware

# Message List
MSG_CMD_ACK         = 0x00 # Command acknowledgment
MSG_SWEAT_STREAM    = 0x62 # Sensor data stream message
MSG_SYS_TIME        = 0x65 # Current system time
MSG_FW_INFO         = 0x78 # Sensor firmware version

class NICUCollect(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, event_comm, graph_comm, baud_rate=1000000):

        super(NICUCollect, self).__init__()
        self.conn_q  = Queue.Queue()

        self.event_comm = event_comm
        self.graph_comm = graph_comm

        self.connection_thread = None

        #initalize Data Logger
        # self.data_logger = DataLogger()

        self.master_handle = -1

        self.connection_tuple = None
        self.connection_tuple_lock = Lock()

        self.conn_q.put(-1)
        self.advertising = False

        self.set_connectivity_id("NRF52")

        global SENSOR_DATA_COMM_BASE_UUID, SENSOR_DATA_COMM_RX_UUID, SENSOR_DATA_COMM_TX_UUID
        SENSOR_DATA_COMM_BASE_UUID   = BLEUUIDBase([0x52, 0x4A, 0x00, 0x00, 0x4E, 0x52, 0x45, 0x54, 
                                                   0x53, 0x45, 0x57, 0x48, 0x54, 0x52, 0x4F, 0x4E], 0x02)												
        SENSOR_DATA_COMM_RX_UUID = BLEUUID(0x0002, SENSOR_DATA_COMM_BASE_UUID)
        SENSOR_DATA_COMM_TX_UUID = BLEUUID(0x0003, SENSOR_DATA_COMM_BASE_UUID)

        """
        Below are user function callback, we attach these callbacks to the event communicator. The callbacks,
        within the NICU BLE driver's process, when the user interacts with the GUI frontend in such a way that
        it sends a message to the event comm which is then handled by the BLE driver's event comm and invokes 
        one of the correct functions below.
        """
        self.event_comm.add_event(BLE_EVENT.STARTADVERTISE, self.launch_advertise_thread)
        self.event_comm.add_event(BLE_EVENT.STOPADVERTISE, self.stop_advertise_thread)
        self.event_comm.add_event(BLE_EVENT.CONNECT, self.set_connection_tuple)
        self.event_comm.add_event(BLE_EVENT.DISCONECT, self.handle_user_disconnect)
        self.event_comm.add_event(BLE_EVENT.EXIT, self.handle_user_exit)
        self.event_comm.add_event(BLE_EVENT.STARTLOGGING, self.start_logging)
        self.event_comm.add_event(BLE_EVENT.STOPLOGGING, self.stop_logging)
		
        self.event_comm.add_event(BLE_EVENT.CONFIGSENSING, self.config_sensing)
        self.event_comm.add_event(BLE_EVENT.STARTSENSING, self.start_sensing)			
        self.event_comm.add_event(BLE_EVENT.STOPSENSING, self.stop_sensing)	

        # Start the bluetooth driver or start the simulated signal
        try:
            ret_val = self.setup_bluetooth_driver()
            if ret_val == False:
                self.event_comm.post_event(QT_EVENT.EXIT, ())
            else:
                self.adapter.observer_register(self)
                self.adapter.driver.observer_register(self)
                self.event_comm.post_event(QT_EVENT.BT_CONNECTED, (True,))
        except Exception as e:
            logging.error("Error While initalizing the BLE Dongle with {}", e)
            self.event_comm.post_event(QT_EVENT.EXIT, ())
											
    def start_logging(self, args):
        pass
        # self.data_logger.open()
    
    def stop_logging(self, args):
        pass
        # self.data_logger.close()

    def send_host_cmd(self, cmd, params=[]):
        if self.master_handle != -1:
            cmd_len = len(params) + 2
            check_sum = (cmd_len + cmd + sum(params) ) % 256
            self.adapter.write_req(self.master_handle, SENSOR_DATA_COMM_RX_UUID, [cmd_len] + [cmd] + params + [check_sum])

    def config_sensing(self, args):
        params = list(args)
        self.send_host_cmd(CMD_CONFIG_SENSOR, params)
			
    def start_sensing(self, args):
        params = list(args)		
        self.send_host_cmd(CMD_START_DATA_STREAM, params)
	
    def stop_sensing(self, args):
        self.send_host_cmd(CMD_STOP_DATA_STREAM, [])

	"""
    This function is triggered when the user requests to disconnect from the current device. 
    The disconnect_num is the device with which we wish to disconnect from.
    """
    def handle_user_disconnect(self, disconnect_tuple):
        disconnect_num = disconnect_tuple[0]

        if disconnect_num == 0:
            self.adapter.disconnect(self.master_handle)
            self.master_handle = -1

    """
    This function is triggered when the user exits the program. The BLE dongle connection must be closed 
    otherwise a manual turn off and then back on is required in order to get a BLE device to connect to 
    the dongle.
    """
    def handle_user_exit(self, args):
        try:
            self.adapter.driver.close()

            logging.info("Done handling user exit")
			
        except:
            pass
        logging.info("Handling user exit in nicu_bt")
        
    """
    This function is triggered on instantiation of the class, and prepares the BLE dongle for the running
    of the program. The number of connection is how many BLE devices we wish to connect to the dongle.
    """   
    def open(self):
        logging.info("Opening Device")
        try:
            self.adapter.driver.open()
        except Exception as e:
            self.event_comm.post_event(QT_EVENT.EXIT, ())
            logging.exception("Error opening the Driver")
            return

        ble_enable_params = BLEEnableParams(vs_uuid_count      = 1,
                                            service_changed    = False,
                                            periph_conn_count  = 0,
                                            central_conn_count = CONNECTIONS,
                                            central_sec_count  = CONNECTIONS)
        if nrf_sd_ble_api_ver >= 3:
            logging.info("Enabling larger ATT MTUs")
            ble_enable_params.att_mtu = 50											
											
        try:
            self.adapter.driver.ble_enable(ble_enable_params)
            self.adapter.driver.ble_vs_uuid_add(SENSOR_DATA_COMM_BASE_UUID)
        except Exception as e:
            self.event_comm.post_event(QT_EVENT.EXIT, ())
            logging.exception("Error Enabling BLE")
            return
			
    def close(self):
        self.adapter.driver.close()

    """
    This is the starting point for the BLE connection process. 
    """
    def connect_and_discover(self):
        #While we have not connected to anything loop forever until either we connect to the desired device or
        #until the user exits the connection process.
        while self.master_handle == -1:
            try:
                self.adapter.driver.ble_gap_scan_start()
                logging.info("Start scanning...")
            except Exception as e:
                logging.warning("Connect and Discover Exception: %s", e)
                return

            try:
                #Wait until we have selected a device to connect to, this will return either after a timeout or we have 
                #selected a device to connect to. This block and is dependent upon on_gap_evt_adv_report to select a 
                #connection handle from the various devices available.
                new_conn = self.conn_q.get(timeout = 180)
            except Exception as e:
                logging.debug("conn queue threw error %s", e)
                return

            if new_conn == -1:
                logging.info("No new connection request, return...")
                return

            if nrf_sd_ble_api_ver >= 3:
                try:
                    logging.info("Exchange MTU size...")				
                    att_mtu = self.adapter.att_mtu_exchange(new_conn)
                except KeyError, e:
                    logging.warning("MTU exchange failed: %s", e)
                    # device_type, _name = self.connection_tuple
                    #This resets the GUI's button to NOT connected.
                    # self.event_comm.post_event(QT_EVENT.UPDATE_BUTTON_STATUS, (device_type,0,))
                    continue

            try:
                #After we have connected with a device we request, from the connected device, what are the various 
                #services that you offer, currently the callback for this is NOT implemented.
                logging.info("Discovering service...")
                self.adapter.service_discovery(new_conn)
            except Exception as e:
                logging.warning("adapter service discovery failed: %s", e)
                # with self.connection_tuple_lock:
                #     device_type, _name = self.connection_tuple
                #     #This resets the GUI's button to NOT connected.
                #     self.event_comm.post_event(QT_EVENT.UPDATE_BUTTON_STATUS, (device_type,0,))
                continue

            with self.connection_tuple_lock:
                device_type, _name = self.connection_tuple
                #This sets the GUI's button to connected.
                self.event_comm.post_event(QT_EVENT.UPDATE_BUTTON_STATUS, (device_type,2,))

                if device_type == 0:
                    self.master_handle = new_conn

                self.connection_tuple = None
            logging.info("Device connected")

        self.advertising = False

    """
    This method connects to the passed in handle. The handle that is passed comes from the
    self.adapter.connect call in the on_gap_evt_adv_report method.
    """ 
    def on_gap_evt_connected(self, ble_driver, conn_handle, peer_addr, role, conn_params):
        logging.info('New Connection: {}'.format(conn_handle))
        self.conn_q.put(conn_handle)

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        logging.info('Disconnected: {} {} {}'.format(conn_handle, reason, reason.value))

        # time out or failed to be established
        if reason.value == 8:
            if(conn_handle == self.master_handle):
                self.event_comm.post_event(QT_EVENT.DISCONNECT, (0,))
                self.master_handle = -1
            else:
                logging.info("Device disconnected while trying to connect")
                with self.connection_tuple_lock:
                    device_type, _name = self.connection_tuple
                    self.event_comm.post_event(QT_EVENT.DISCONNECT, (device_type,))
            with self.connection_tuple_lock:
                self.connection_tuple = None
        if reason.value == 62:
            device_type, _name = self.connection_tuple
            logging.info("Disconnect with failed to be established Device type: {}".format(device_type))

            if device_type == 0:
                self.event_comm.post_event(QT_EVENT.DISCONNECT, (0,))

            with self.connection_tuple_lock:
                self.connection_tuple = None
    def on_gap_evt_timeout(self, ble_driver, conn_handle, src):
        if src == BLEGapTimeoutSrc.scan:
            ble_driver.ble_gap_scan_start()

    def on_gap_evt_adv_report(self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data):
        dev_name_list = None
        if BLEAdvData.Types.complete_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.complete_local_name]
        elif BLEAdvData.Types.short_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.short_local_name]
        else:
            return

        uuid = None 
        try:
            uuid = adv_data.records[BLEAdvData.Types.complete_local_name]
        except:	
            return
			
        dev_name        = "".join(chr(e) for e in dev_name_list)
        address_string  = "".join("{0:02X}".format(b) for b in peer_addr.addr)
        logging.info('Received advertisment report, address: 0x{}, device_name: {}'.format(address_string,
                                                                                    dev_name))
        if dev_name not in self.master_list and len(dev_name) > 1:
            logging.info('Added {} to master list'.format(dev_name))
            self.event_comm.post_event(QT_EVENT.UPDATE_M_LIST, (dev_name))
            self.master_list.append(dev_name)

        with self.connection_tuple_lock:
            if not self.connection_tuple:
                return

            device_type, name = self.connection_tuple
            if device_type == 0 and name == dev_name:
                logging.info('The selected master is: %s', dev_name)
                self.adapter.connect(peer_addr)
				
    def on_notification(self, ble_adapter, conn_handle, uuid, data):
        if conn_handle == self.master_handle:
            if uuid.value == SENSOR_DATA_COMM_TX_UUID.value:
			
                package_num = data[0]
                message_id = data[1] 

                #TODO Add behaivors when data is recived
                if message_id == MSG_CMD_ACK:
                    pass
                elif message_id == MSG_SWEAT_STREAM:
#                    logging.info("Sweat capacity stream data received...")				   				
                    timeStamp = data[2] + (data[3] << 8) + (data[4] << 16) + (data[5] << 24)
                    dataType = data[6]
                    dataLen = data[7]
                    channel1_capacity_data_raw = data[8] + (data[9] << 8) + (data[10] << 16) + (data[11] << 24)
                    if (data[11] & 0x80):
                        channel1_capacity_data_raw -= (1 << 32)					
                    
                    channel1_capacity_data_raw /= (1<<8)
					
                    channel2_capacity_data_raw = data[12] + (data[13] << 8) + (data[14] << 16) + (data[15] << 24)
                    if (data[15] & 0x80):
                        channel2_capacity_data_raw -= (1 <<32)
					
                    channel2_capacity_data_raw /= (1<<8)
															
					# Update graph with new data from sensor
                    self.event_comm.post_event(QT_EVENT.UPDATE_GRAPH, (1, timeStamp, [channel1_capacity_data_raw, channel2_capacity_data_raw], ))

                    pass
                elif message_id == MSG_SYS_TIME:
                    pass
                elif message_id == MSG_FW_INFO:
                    pass


    def set_connectivity_id(self, connectivity_device):
        global BLEDriver, BLEAdvData, BLEEvtID, BLEAdapter, BLEEnableParams, BLEGapTimeoutSrc, BLEUUID, BLEUUIDBase
        config.__conn_ic_id__ = connectivity_device

        from pc_ble_driver_py.ble_driver    import BLEDriver, BLEAdvData, BLEEvtID, BLEEnableParams, BLEGapTimeoutSrc, BLEUUID, BLEUUIDBase
        from pc_ble_driver_py.ble_adapter   import BLEAdapter

        global nrf_sd_ble_api_ver
        nrf_sd_ble_api_ver = config.sd_api_ver_get()
        self.nrf_sd_ble_api_ver = config.sd_api_ver_get()

    def launch_advertise_thread(self, args):
        if not self.connection_thread or not self.connection_thread.isAlive():
            with self.conn_q.mutex:
                self.conn_q.queue.clear()
            self.master_list = []
            
            self.advertising = True
            self.connection_thread = Thread(target=self.connect_and_discover)
            self.connection_thread.start()

    def on_gattc_evt_exchange_mtu_rsp(self, ble_driver, conn_handle, **kwargs):
        logging.info('ATT MTU exchange response: conn_handle={}'.format(conn_handle))    

    def on_att_mtu_exchanged(self, ble_driver, conn_handle, att_mtu):
        logging.info('ATT MTU exchanged: conn_handle={} att_mtu={}'.format(conn_handle, att_mtu))

    def set_connection_tuple(self, connection_tuple):
        with self.connection_tuple_lock:
            self.connection_tuple = connection_tuple

    def setup_bluetooth_driver(self):
        descs       = BLEDriver.enum_serial_ports()
        if len(descs) == 0:
            logging.info('BLE Dongle not found')
            return False
        serial_port = descs[0].port
        logging.info("Connecting to {}".format(serial_port))
        driver    = BLEDriver(serial_port=serial_port, auto_flash=True)
        self.adapter   = BLEAdapter(driver)
        self.open()
        return True

    def stop_advertise_thread(self, args):
        if self.connection_thread.isAlive():
            try:
                logging.info("Stop scanning...")			
                self.adapter.driver.ble_gap_scan_stop()
            except:
                self.event_comm.post_event(QT_EVENT.EXIT, ())
                logging.exception("Error opening the Driver")
                return

            self.conn_q.put(-1)
            self.advertising = False

        start_time = time.time()
        if self.master_handle != -1:
#            self.adapter.enable_notification(new_conn, NUS_TX_UUID)
            self.adapter.enable_notification(self.master_handle, SENSOR_DATA_COMM_TX_UUID)

    def on_att_mtu_exchanged(self, ble_driver, conn_handle, att_mtu):
        logging.info('ATT MTU exchanged: conn_handle={} att_mtu={}'.format(conn_handle, att_mtu))
	
    def run(self):
        self.event_comm.start_event_handler(PROCESS.BLUETOOTH)

def launch(event_comm, graph_comm):
    BT = NICUCollect(event_comm, graph_comm)
    BT.run()

def fork_bt_process(event_comm, graph_comm):
    bt_process = Process(target=launch, args=(event_comm, graph_comm))
    return bt_process

def main():

    # Intializing communicators
    event_comm = EventCommunicator()
    graph_comm = GraphCommunicator()

    ble_process = Process(target=launch, args=(event_comm, graph_comm,))
    ble_process.start()

    while True:
        pass

if __name__ == "__main__":
    freeze_support()
    main()
