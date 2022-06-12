from unittest import TestCase
from comps import Comps
import multiprocessing

class TestComps(TestCase):
    message_queue = multiprocessing.Queue()
    comps = Comps(message_queue=message_queue, compsFile='../comps/meta-comps.json')
    comps.check_stop_rolling()

    pass
