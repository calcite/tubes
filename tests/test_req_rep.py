import asyncio
import zmq

from helpers import run_test_tasks
from tube.manager import Tube, TubeNode

ADDR = 'ipc:///tmp/req_resp.pipe'
TOPIC = 'req'


def test_req():

    async def request_task(tube, topic, name, number=2, timeout=30):
        for it in range(0, number):
            resp = await tube.request(topic, f"request-{name}-{it}",
                                      timeout=timeout)
            assert resp == f"response-{name}-{it}"

    async def response_task(tube, topic):
        async def __process(payload):
            assert payload[0:8] == 'request-'
            return f'response-{payload[8:]}'
        tube.register_handler(topic, __process)
        await tube.start()

    req_socket1 = Tube(
        name='REQ',
        addr=ADDR,
        socket_type=zmq.REQ
    )
    req_socket2 = Tube(
        name='REQ',
        addr=ADDR,
        socket_type=zmq.REQ
    )
    resp_socket = Tube(
        name='RESP',
        addr=ADDR,
        type='server',
        socket_type=zmq.REP
    )
    req_tube1 = TubeNode()
    req_tube1.register_socket(req_socket1, f"{TOPIC}/#")

    req_tube2 = TubeNode()
    req_tube2.register_socket(req_socket2, f"{TOPIC}/#")

    resp_tube = TubeNode()
    resp_tube.register_socket(resp_socket, f"{TOPIC}/#")
    resp_tube.connect()

    asyncio.run(
        run_test_tasks(
            [request_task(req_tube1, f'{TOPIC}/aaa', 'REQ1'),
             request_task(req_tube1, TOPIC, 'REQ2')],
            [response_task(resp_tube, f'{TOPIC}/#')]
        )
    )
