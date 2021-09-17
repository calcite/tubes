import asyncio
import zmq

from helpers import run_test_tasks
from tube import Tube, TubeNode

ADDR = 'ipc:///tmp/req_resp.pipe'
TOPIC = 'req'


def test_req_resp():

    async def request_task(node, topic, name, number=2, timeout=30):
        asyncio.current_task().set_name(name)
        for it in range(0, number):
            resp = await node.request(topic, f"request-{name}-{it}",
                                      timeout=timeout)
            assert resp.payload == f"response-{name}-{it}"

    async def response_task(node, topic):
        async def __process(message):
            assert message.payload[0:8] == 'request-'
            return f'response-{message.payload[8:]}'
        asyncio.current_task().set_name('RESP')
        node.register_handler(topic, __process)
        await node.start()

    tube_req1 = Tube(
        name='REQ1',
        addr=ADDR,
        tube_type=zmq.REQ
    )
    tube_req2 = Tube(
        name='REQ2',
        addr=ADDR,
        tube_type=zmq.REQ
    )
    tube_resp = Tube(
        name='RESP',
        addr=ADDR,
        type='server',
        tube_type=zmq.REP
    )
    node_req1 = TubeNode()
    node_req1.register_tube(tube_req1, f"{TOPIC}/#")

    node_req2 = TubeNode()
    node_req2.register_tube(tube_req2, f"{TOPIC}/#")

    node_resp = TubeNode()
    node_resp.register_tube(tube_resp, f"{TOPIC}/#")
    node_resp.connect()

    asyncio.run(
        run_test_tasks(
            [request_task(node_req1, f'{TOPIC}/aaa', 'REQ1'),
             request_task(node_req2, TOPIC, 'REQ2')],
            [response_task(node_resp, f'{TOPIC}/#')]
        )
    )
