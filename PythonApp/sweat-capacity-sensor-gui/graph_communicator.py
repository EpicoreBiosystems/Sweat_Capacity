from multiprocessing import Pipe

class GraphCommunicator():

    def __init__(self):
        self.graph_s_conn, self.graph_e_conn = Pipe()

        # Initalize events to None
        self.graph_update_dict = {-1: None}

    def add_graph(self, graph_num, handler):
        self.graph_update_dict[graph_num] = handler

    def get_running(self):
        with self.running_lock:
            return self.runing

    def update_graph(self, graph_num, array):
        self.graph_s_conn.send((graph_num, array))

    def listen_graph_updates(self):
        #I can't pickle the lock this is not safe.
        while True:
            try:
                obj = self.graph_e_conn.recv()
                graph_num, data = obj

                if graph_num == -1:
                    return

                if graph_num in self.graph_update_dict:
                    graph_update_func = self.graph_update_dict[graph_num]
                    graph_update_func(*data)
                else:
                    raise ValueError

            except EOFError:
                print("EOF Error")
                break