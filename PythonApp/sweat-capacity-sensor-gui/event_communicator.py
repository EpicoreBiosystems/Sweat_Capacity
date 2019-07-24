# using enum34
from enum import Enum
from multiprocessing import Pipe

class BLE_EVENT(Enum):
    STARTADVERTISE = 1
    STOPADVERTISE = 2
    CONNECT = 3
    DISCONECT = 4
    EXIT = 5

    STARTLOGGING = 6
    STOPLOGGING = 7
    MODE_CHANGE = 8
	
    CONFIGSENSING = 9	
    STARTSENSING = 10
    STOPSENSING = 11
     	

class QT_EVENT(Enum):
    UPDATE_HR = 11
    UPDATE_SPO2 = 12
    UPDATE_TEMP = 13
    UPDATE_PTT = 14
    UPDATE_RR = 30

    UPDATE_BUTTON_STATUS = 15
    UPDATE_M_LIST = 16
    UPDATE_S_LIST = 17
    DISCONNECT = 18

    INTERNAL_CLOSE_EVENT = 19

    EXIT = 20
    BT_CONNECTED = 21
	
    UPDATE_GRAPH = 22

class PROCESS(Enum):
    QT = 1
    BLUETOOTH = 2

class EventCommunicator():

    def __init__(self):
        self.ble_s_conn, self.ble_e_conn = Pipe()
        self.qt_s_conn, self.qt_e_conn = Pipe()

        # Initalize events to None
        self.event_handler_dict = {}
        for event in QT_EVENT:
            self.event_handler_dict[event.value] = []
        for event in BLE_EVENT:
            self.event_handler_dict[event.value] = []

    def add_event(self, event, handler):
        self.event_handler_dict[event.value].append(handler)

    def post_event(self, event, args = None):
        try:
            if event in BLE_EVENT:
                self.ble_s_conn.send((event.value,args))
            elif event in QT_EVENT:
                self.qt_s_conn.send((event.value,args))
            else:
                raise ValueError
        except ValueError:
            logging.error("Not a valid event event: {} args: {}".format(event,args))

    def start_event_handler(self, process):
        try:
            if process == PROCESS.QT:
                conn = self.qt_e_conn
                exit_event = QT_EVENT.INTERNAL_CLOSE_EVENT
            elif process == PROCESS.BLUETOOTH:
                conn = self.ble_e_conn
                exit_event = BLE_EVENT.EXIT
            else:
                raise ValueError
        except ValueError:
            logging.error("Not a valid process: {}".format(process))

        while True:
            try:
                obj = conn.recv()
                event, args = obj

                if event == exit_event.value:
                    if event == BLE_EVENT.EXIT.value:
                        events = self.event_handler_dict[event]
                        if events:
                            for action in events:
                                action(args)
                        self.qt_s_conn.send((QT_EVENT.INTERNAL_CLOSE_EVENT.value, ()))
                    break 

                events = self.event_handler_dict[event]
                if events:
                    for event in events:
                        event(args)
                else:
                    raise ValueError
            except EOFError:
                logging.warning("EOF Error")
                break
        
def main():
    comm = EventCommunicator()

    def printhello(args):
        print("Hello")
        print("You entered connect function")

    comm.add_event(BLE_EVENT.CONNECT, printhello)
    comm.post_event(BLE_EVENT.CONNECT)
    comm.start_event_handler(PROCESS.BLUETOOTH)

if __name__ == "__main__":
    main()