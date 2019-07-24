import argparse
import logging
import os
import sys
import time
from multiprocessing import Process, freeze_support

from PyQt4 import QtGui

from event_communicator import EventCommunicator
from graph_communicator import GraphCommunicator
from sweat_capacity_bt import fork_bt_process
from sweat_capacity_gui import NICU_GUI

from tendo import singleton

def check_logging_dir(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    
    return dir_name
#Configures default logger

_LOG_LEVEL_STRINGS = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']
logging.basicConfig(format = '%(asctime)s [%(filename)s:%(lineno)s-%(funcName)s] %(message)s',
                    datefmt = '%I:%M:%S',
                    filename = os.path.join(check_logging_dir(os.path.join(os.getcwd(), 'logs')), 
                                            'log-file-{}.log'.format(time.strftime("%Y_%m_%d", time.localtime()))),
                    level=logging.INFO)



def _log_level_string_to_int(log_level_string):
    if not log_level_string in _LOG_LEVEL_STRINGS:
        message = 'invalid choice: {0} (choose from {1})'.format(log_level_string, _LOG_LEVEL_STRINGS)
        raise argparse.ArgumentTypeError(message)

    log_level_int = getattr(logging, log_level_string, logging.INFO)
    # check the logging log_level_choices have not changed from our expected values
    assert isinstance(log_level_int, int)

    return log_level_int

class NICU(object):
    def __init__(self, test = False, mac = False):

        logging.debug('In main. Starting Application')

        self.__app = QtGui.QApplication(sys.argv)

        # Intializeing communicators
        self.event_comm = EventCommunicator()
        self.graph_comm = GraphCommunicator()

        # Start Bluetooth Process
        self.bt_process = fork_bt_process(self.event_comm, self.graph_comm)
        self.bt_process.start()

        # Initalize UI
        self.ui = NICU_GUI(self.event_comm, self.graph_comm)

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--log-level',
                        default='INFO',
                        dest='log_level',
                        type=_log_level_string_to_int,
                        nargs='?',
                        help='Set the logging output level. {0}'.format(_LOG_LEVEL_STRINGS))
    parser.add_argument('-o', action='store_true')
    parser.add_argument('--mac', action='store_true')
    parser.add_argument('--test', action='store_true')


    parsed_args = parser.parse_args()
    logging.getLogger().setLevel(parsed_args.log_level)
    #flag to output log to console
    if parsed_args.o == True:
        logging.getLogger().addHandler(logging.StreamHandler())

    # Check if this is the only Instance
    # single_instance_obj = singleton.SingleInstance()

    logging.info('In main. Starting Application')
    app = QtGui.QApplication(sys.argv)
    nicu_app = NICU(parsed_args.test, parsed_args.mac)
    sys.exit(app.exec_())

if __name__ == "__main__":
    freeze_support()
    main()
