import ctypes
import collections
import heapq
import os.path
import time
from sys import platform
from consts import MAX_LABEL_COST

if platform.startswith('win32'):
    _dll_file = os.path.join(os.path.dirname(__file__), 'bin/path_engine.dll')
else:
    raise Exception('Please build the shared library compatible to your OS\
                       using source files in engine_cpp!')

_cdll = ctypes.cdll.LoadLibrary(_dll_file)

# set up the argument types for the shortest path function in dll.
_cdll.shortest_path.argtypes = [
    ctypes.c_int,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_wchar_p),
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
    ctypes.c_wchar_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int
]



def single_source_shortest_path(G, origin_node_id,
                                engine_type='c', sp_algm='deque'):
    origin_node_no = G.get_node_no(origin_node_id)

    if engine_type.lower() == 'c':
        G.allocate_for_CAPI()
        #time_start = time.time()
        _optimal_label_correcting_CAPI(G, origin_node_no)
        #time_end = time.time()
    else:
        # just in case user uses C++ and Python path engines in a mixed way
        G.has_capi_allocated = False

        # Initialization for all nodes
        G.node_label_cost = [MAX_LABEL_COST] * G.node_size
        # pointer to previous node index from the current label at current node
        G.node_predecessor = [-1] * G.node_size
        # pointer to previous node index from the current label at current node
        G.link_predecessor = [-1] * G.node_size

        # make sure node_label_cost, node_predecessor, and link_predecessor
        # are initialized even the source node has no outgoing links
        if not G.node_list[origin_node_no].outgoing_link_list:
            return

def _get_path_cost(G, to_node_id):
    to_node_no = G.node_id_to_no_dict[to_node_id]

    return G.node_label_cost[to_node_no]


def _optimal_label_correcting_CAPI(G,
                                   origin_node_no,
                                   departure_time=0):
    """ call the deque implementation of MLC written in cpp

    node_label_cost, node_predecessor, and link_predecessor are still
    initialized in shortest_path() even the source node has no outgoing links.
    """
    _cdll.shortest_path_n(origin_node_no,
                          G.get_node_size(),
                          G.get_from_node_no_arr(),
                          G.get_to_node_no_arr(),
                          G.get_first_links(),
                          G.get_last_links(),
                          G.get_sorted_link_no_arr(),
                          G.get_allowed_uses(),
                          G.get_link_costs(),
                          G.get_node_label_costs(),
                          G.get_node_preds(),
                          G.get_link_preds(),
                          G.get_queue_next(),
                          G.get_agent_type_name(),
                          MAX_LABEL_COST,
                          G.get_last_thru_node(),
                          departure_time)


