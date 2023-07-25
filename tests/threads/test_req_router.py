import pytest
import time

import zmq

from tests.helpers import wait_for_result2 as wait_for_result, \
    run_test_threads, wrapp
from zmq_tubes.threads import Tube, TubeNode

ADDR = 'ipc:///tmp/req_router.pipe'
TOPIC = 'req'


@pytest.fixture
def data():
    return ['REQ10', 'REQ11'].copy()


@pytest.fixture
def data2():
    return ['REQ20', 'REQ21'].copy()


@pytest.fixture
def result():
    return []


@pytest.fixture(params=[{'server': True, 'utf8_decoding': True}])
def router_node(result, request):
    def __process(req):
        result.append(req.payload)
        if isinstance(req.payload, str) and 'REQ10' in req.payload:
            time.sleep(.1)
        return req.create_response(
            f'RESP1{req.payload[-2:]}' if request.param['utf8_decoding']
            else b'RESP1' + req.payload[-2:])

    tube = Tube(
        name='ROUTER',
        addr=ADDR,
        server=request.param['server'],
        tube_type=zmq.ROUTER,
        utf8_decoding=request.param['utf8_decoding']
    )

    node = TubeNode()
    node.register_tube(tube, f"{TOPIC}/#")
    node.register_handler(f"{TOPIC}/#", __process)
    return node


@pytest.fixture(params=[{'server': False, 'utf8_decoding': True}])
def req_node1(request):
    tube = Tube(
        name='REQ1',
        addr=ADDR,
        server=request.param['server'],
        tube_type=zmq.REQ,
        utf8_decoding=request.param['utf8_decoding']
    )

    node = TubeNode()
    node.register_tube(tube, f"{TOPIC}/#")
    return node


@pytest.fixture(params=[{'server': False, 'utf8_decoding': True}])
def req_node2(request):
    tube = Tube(
        name='REQ2',
        addr=ADDR,
        server=request.param['server'],
        tube_type=zmq.REQ,
        utf8_decoding=request.param['utf8_decoding']
    )

    node = TubeNode()
    node.register_tube(tube, f"{TOPIC}/#")
    return node


################################################################################
#   Tests
################################################################################

def test_resp_router(router_node, req_node1, req_node2, data, data2,
                     result):

    res = []

    @wrapp
    def __process(node, d, p):
        while d:
            resp = node.request(f"{TOPIC}/{p}", d.pop(), timeout=1)
            res.append('RESP' in resp.payload)
    result.clear()
    with router_node:
        run_test_threads(
            __process(req_node1, data, 'A'),
            __process(req_node2, data2, 'B'),
        )
        assert wait_for_result(
            lambda: len(res) == 4 and len(result) == 4,
            timeout=1
        )


def test_resp_router_on_same_node(router_node, data, result):
    """
        The REQ/ROUTER and client on the same node.
    """
    res = []
    tube = Tube(
        name='REQ',
        addr=ADDR,
        server=False,
        tube_type=zmq.REQ
    )
    router_node.register_tube(tube, f"{TOPIC}/#")
    result.clear()
    with router_node:
        while data:
            resp = router_node.request(f"{TOPIC}/A", data.pop(), timeout=1)
            res.append('RESP' in resp.payload)
        assert wait_for_result(
            lambda: len(res) == 2 and len(result) == 2,
            timeout=1
        )


@pytest.mark.parametrize("router_node,req_node1",
                         [({'server': True, 'utf8_decoding': False},
                           {'server': False, 'utf8_decoding': False})],
                         indirect=["router_node", "req_node1"])
def test_req_router_bytes(router_node, req_node1, result):
    result.clear()
    with router_node:
        res = req_node1.request(f"{TOPIC}/A", 'XXX1')
        assert isinstance(res.payload, bytes)
        res = req_node1.request(f"{TOPIC}/A", 'XXX2', utf8_decoding=True)
        assert not isinstance(res.payload, bytes)
        assert wait_for_result(
            lambda: len(result) == 2 and isinstance(result[0], bytes),
            timeout=1
        )
