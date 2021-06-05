import time
import asyncio.subprocess

import pytest

from sockio.socket import (
    TCP,
    ConnectionTimeoutError,
    ConnectionEOFError,
)

from conftest import IDN_REQ, IDN_REP, WRONG_REQ, WRONG_REP


def test_socket_creation():
    sock = TCP("example.com", 34567)
    assert sock.host == "example.com"
    assert sock.port == 34567
    assert sock.connection_timeout is None
    assert sock.timeout is None
    assert sock.auto_reconnect
    assert not sock.connected()
    assert sock.in_waiting() == 0
    assert sock.connection_counter == 0


@pytest.mark.asyncio
async def test_open_fail(unused_tcp_port):
    sock = TCP("0", unused_tcp_port)
    assert not sock.connected()
    assert sock.connection_counter == 0

    with pytest.raises(ConnectionRefusedError):
        await sock.open()
    assert not sock.connected()
    assert sock.connection_counter == 0


@pytest.mark.asyncio
async def test_open_timeout():
    timeout = 0.1
    # TODO: Not cool to use an external connection
    aio_socket = TCP("www.google.com", 81, connection_timeout=timeout)
    with pytest.raises(ConnectionTimeoutError):
        start = time.time()
        try:
            await aio_socket.open()
        finally:
            dt = time.time() - start
            assert dt > timeout and dt < (timeout + 0.05)

    # TODO: Not cool to use an external connection
    aio_socket = TCP("www.google.com", 82)
    with pytest.raises(ConnectionTimeoutError):
        start = time.time()
        try:
            await aio_socket.open(timeout=timeout)
        finally:
            dt = time.time() - start
            assert dt > timeout and dt < (timeout + 0.05)


@pytest.mark.asyncio
async def test_write_fail(unused_tcp_port):
    sock = TCP("0", unused_tcp_port)
    assert not sock.connected()
    assert sock.connection_counter == 0

    with pytest.raises(ConnectionRefusedError):
        await sock.write(IDN_REQ)
    assert not sock.connected()
    assert sock.in_waiting() == 0
    assert sock.connection_counter == 0


@pytest.mark.asyncio
async def test_write_readline_fail(unused_tcp_port):
    sock = TCP("0", unused_tcp_port)
    assert not sock.connected()
    assert sock.connection_counter == 0

    with pytest.raises(ConnectionRefusedError):
        await sock.write_readline(IDN_REQ)
    assert not sock.connected()
    assert sock.in_waiting() == 0
    assert sock.connection_counter == 0


@pytest.mark.asyncio
async def test_write_readline_error(aio_server, aio_socket):
    with pytest.raises(ConnectionEOFError):
        await aio_socket.write_readline(b"kill\n")


@pytest.mark.asyncio
async def test_open_close(aio_server, aio_socket):
    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 0
    assert aio_server.sockets[0].getsockname() == (aio_socket.host, aio_socket.port)

    await aio_socket.open()
    assert aio_socket.connected()
    assert aio_socket.connection_counter == 1

    with pytest.raises(ConnectionError):
        await aio_socket.open()
    assert aio_socket.connected()
    assert aio_socket.connection_counter == 1

    await aio_socket.close()
    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 1
    await aio_socket.open()
    assert aio_socket.connected()
    assert aio_socket.connection_counter == 2
    await aio_socket.close()
    await aio_socket.close()
    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 2


@pytest.mark.asyncio
async def test_callbacks(aio_server):
    host, port = aio_server.sockets[0].getsockname()
    state = dict(made=0, lost=0, eof=0)

    def made():
        state["made"] += 1

    def lost():
        state["lost"] += 1

    def eof():
        state["eof"] += 1

    aio_socket = TCP(
        host,
        port,
        on_connection_made=made,
        on_connection_lost=lost,
        on_eof_received=eof,
    )
    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 0
    assert state["made"] == 0
    assert state["lost"] == 0
    assert state["eof"] == 0

    await aio_socket.open()
    assert aio_socket.connected()
    assert aio_socket.connection_counter == 1
    assert state["made"] == 1
    assert state["lost"] == 0
    assert state["eof"] == 0

    with pytest.raises(ConnectionError):
        await aio_socket.open()
    assert aio_socket.connected()
    assert aio_socket.connection_counter == 1
    assert state["made"] == 1
    assert state["lost"] == 0
    assert state["eof"] == 0

    await aio_socket.close()
    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 1
    assert state["made"] == 1
    await asyncio.sleep(0.1)
    assert state["lost"] == 1
    assert state["eof"] == 0

    await aio_socket.open()
    assert aio_socket.connected()
    assert aio_socket.connection_counter == 2
    assert state["made"] == 2
    assert state["lost"] == 1
    assert state["eof"] == 0

    await aio_socket.close()
    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 2
    assert state["made"] == 2
    assert state["lost"] == 2
    assert state["eof"] == 0

    await aio_socket.close()
    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 2
    assert state["made"] == 2
    assert state["lost"] == 2
    assert state["eof"] == 0


@pytest.mark.asyncio
async def test_coroutine_callbacks(aio_server):
    host, port = aio_server.sockets[0].getsockname()
    RESP_TIME = 0.02
    state = dict(made=0, lost=0, eof=0)

    async def made():
        await asyncio.sleep(RESP_TIME)
        state["made"] += 1

    async def lost(exc):
        await asyncio.sleep(RESP_TIME)
        state["lost"] += 1

    async def eof():
        await asyncio.sleep(RESP_TIME)
        state["eof"] += 1

    aio_socket = TCP(
        host,
        port,
        on_connection_made=made,
#        on_connection_lost=lost,
#        on_eof_received=eof,
    )

    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 0
    assert state["made"] == 0
    assert state["lost"] == 0
    assert state["eof"] == 0

    await aio_socket.open()
    assert aio_socket.connected()
    assert aio_socket.connection_counter == 1
    assert state["made"] == 1
    assert state["lost"] == 0
    assert state["eof"] == 0

    with pytest.raises(ConnectionError):
        await aio_socket.open()
    assert aio_socket.connected()
    assert aio_socket.connection_counter == 1
    assert state["made"] == 1
    assert state["lost"] == 0
    assert state["eof"] == 0

    await aio_socket.close()
    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 1
    assert state["made"] == 1
    assert state["lost"] == 0
    assert state["eof"] == 0
    await asyncio.sleep(RESP_TIME + 0.01)
    assert state["made"] == 1
    assert state["lost"] == 1
    assert state["eof"] == 0

    await aio_socket.open()
    assert aio_socket.connected()
    assert aio_socket.connection_counter == 2
    assert state["made"] == 2
    assert state["lost"] == 1
    assert state["eof"] == 0

    await aio_socket.close()
    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 2
    assert state["made"] == 2
    assert state["lost"] == 1
    assert state["eof"] == 0
    await asyncio.sleep(RESP_TIME + 0.01)
    assert state["made"] == 2
    assert state["lost"] == 2
    assert state["eof"] == 0

    await aio_socket.close()
    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 2
    assert state["made"] == 2
    assert state["lost"] == 2
    assert state["eof"] == 0
    await asyncio.sleep(RESP_TIME + 0.01)
    assert state["made"] == 2
    assert state["lost"] == 2
    assert state["eof"] == 0


@pytest.mark.asyncio
async def test_error_callback(aio_server):
    host, port = aio_server.sockets[0].getsockname()

    state = dict(made=0)

    def error_callback():
        state["made"] += 1
        raise RuntimeError("cannot handle this")

    aio_socket = TCP(host, port, on_connection_made=error_callback)

    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 0
    assert state["made"] == 0

    await aio_socket.open()
    assert aio_socket.connected()
    assert aio_socket.connection_counter == 1
    assert state["made"] == 1


@pytest.mark.asyncio
async def test_eof_callback(aio_server):
    host, port = aio_server.sockets[0].getsockname()
    state = dict(made=0, lost=0, eof=0)

    def made():
        state["made"] += 1

    def lost(exc):
        state["lost"] += 1

    def eof():
        state["eof"] += 1

    aio_socket = TCP(
        host,
        port,
        on_connection_made=made,
        on_connection_lost=lost,
        on_eof_received=eof,
    )
    assert not aio_socket.connected()
    assert aio_socket.connection_counter == 0
    assert state["made"] == 0
    assert state["lost"] == 0
    assert state["eof"] == 0

    await aio_socket.open()
    assert aio_socket.connected()
    assert aio_socket.connection_counter == 1
    assert state["made"] == 1
    assert state["lost"] == 0
    assert state["eof"] == 0

    await aio_server.stop()
    await asyncio.sleep(0.05)  # give time for connection to be closed

    assert state["made"] == 1
    assert state["lost"] == 0
    assert state["eof"] == 1


@pytest.mark.asyncio
async def test_write_readline(aio_socket):
    for request, expected in [(IDN_REQ, IDN_REP), (WRONG_REQ, WRONG_REP)]:
        coro = aio_socket.write_readline(request)
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert aio_socket.connected()
        assert aio_socket.connection_counter == 1
        assert expected == reply


@pytest.mark.asyncio
async def test_write_readlines(aio_socket):
    for request, expected in [
        (IDN_REQ, [IDN_REP]),
        (2 * IDN_REQ, 2 * [IDN_REP]),
        (IDN_REQ + WRONG_REQ, [IDN_REP, WRONG_REP]),
    ]:
        coro = aio_socket.write_readlines(request, len(expected))
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert aio_socket.connected()
        assert aio_socket.connection_counter == 1
        assert expected == reply


@pytest.mark.asyncio
async def test_writelines_readlines(aio_socket):
    for request, expected in [
        ([IDN_REQ], [IDN_REP]),
        (2 * [IDN_REQ], 2 * [IDN_REP]),
        ([IDN_REQ, WRONG_REQ], [IDN_REP, WRONG_REP]),
    ]:
        coro = aio_socket.writelines_readlines(request)
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert aio_socket.connected()
        assert aio_socket.connection_counter == 1
        assert expected == reply


@pytest.mark.asyncio
async def test_writelines(aio_socket):
    for request, expected in [
        ([IDN_REQ], [IDN_REP]),
        (2 * [IDN_REQ], 2 * [IDN_REP]),
        ([IDN_REQ, WRONG_REQ], [IDN_REP, WRONG_REP]),
    ]:
        coro = aio_socket.writelines(request)
        assert asyncio.iscoroutine(coro)
        answer = await coro
        assert aio_socket.connected()
        assert aio_socket.connection_counter == 1
        assert answer is None

        coro = aio_socket.readlines(len(expected))
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert aio_socket.connected()
        assert aio_socket.connection_counter == 1
        assert expected == reply


@pytest.mark.asyncio
async def test_readline(aio_socket):
    for request, expected in [(IDN_REQ, IDN_REP), (WRONG_REQ, WRONG_REP)]:
        coro = aio_socket.write(request)
        assert asyncio.iscoroutine(coro)
        answer = await coro
        assert aio_socket.connected()
        assert aio_socket.connection_counter == 1
        assert answer is None
        await asyncio.sleep(0.05)
        assert aio_socket.in_waiting() > 0
        coro = aio_socket.readline()
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert expected == reply


@pytest.mark.asyncio
async def test_readuntil(aio_socket):
    for request, expected in [(IDN_REQ, IDN_REP), (WRONG_REQ, WRONG_REP)]:
        coro = aio_socket.write(request)
        assert asyncio.iscoroutine(coro)
        answer = await coro
        assert aio_socket.connected()
        assert aio_socket.connection_counter == 1
        assert answer is None
        coro = aio_socket.readuntil(b"\n")
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert expected == reply


@pytest.mark.asyncio
async def test_readexactly(aio_socket):
    for request, expected in [(IDN_REQ, IDN_REP), (WRONG_REQ, WRONG_REP)]:
        coro = aio_socket.write(request)
        assert asyncio.iscoroutine(coro)
        answer = await coro
        assert aio_socket.connected()
        assert aio_socket.connection_counter == 1
        assert answer is None
        coro = aio_socket.readexactly(len(expected) - 5)
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert expected[:-5] == reply
        coro = aio_socket.readexactly(5)
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert expected[-5:] == reply


@pytest.mark.asyncio
async def test_readlines(aio_socket):
    for request, expected in [
        (IDN_REQ, [IDN_REP]),
        (2 * IDN_REQ, 2 * [IDN_REP]),
        (IDN_REQ + WRONG_REQ, [IDN_REP, WRONG_REP]),
    ]:
        coro = aio_socket.write(request)
        assert asyncio.iscoroutine(coro)
        answer = await coro
        assert aio_socket.connected()
        assert aio_socket.connection_counter == 1
        assert answer is None
        coro = aio_socket.readlines(len(expected))
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert expected == reply


@pytest.mark.asyncio
async def test_read(aio_socket):
    for request, expected in [(IDN_REQ, IDN_REP), (WRONG_REQ, WRONG_REP)]:
        coro = aio_socket.write(request)
        assert asyncio.iscoroutine(coro)
        answer = await coro
        assert aio_socket.connected()
        assert aio_socket.connection_counter == 1
        assert answer is None
        reply, n = b"", 0
        while len(reply) < len(expected) and n < 2:
            coro = aio_socket.read(1024)
            assert asyncio.iscoroutine(coro)
            reply += await coro
            n += 1
        assert expected == reply


@pytest.mark.asyncio
async def test_parallel_rw(aio_socket):
    async def wr(request, expected_reply):
        reply = await aio_socket.write_readline(request)
        return request, reply, expected_reply

    args = 10 * [(IDN_REQ, IDN_REP), (WRONG_REQ, WRONG_REP)]
    coros = [wr(*arg) for arg in args]
    result = await asyncio.gather(*coros)
    for req, reply, expected in result:
        assert reply == expected, "Failed request {}".format(req)


@pytest.mark.asyncio
async def test_parallel(aio_socket):
    async def wr(request, expected_reply):
        await aio_socket.write(request)
        reply = await aio_socket.readline()
        return request, reply, expected_reply

    args = 10 * [(IDN_REQ, IDN_REP), (WRONG_REQ, WRONG_REP)]
    coros = [wr(*arg) for arg in args]
    result = await asyncio.gather(*coros)
    for req, reply, expected in result:
        assert reply == expected, "Failed request {}".format(req)


@pytest.mark.asyncio
async def test_stream(aio_socket):
    request = b"data? 2\n"
    await aio_socket.write(request)
    i = 0
    async for line in aio_socket:
        assert line == b"1.2345 5.4321 12345.54321\n"
        i += 1
    assert i == 2
    assert aio_socket.connection_counter == 1
    assert not aio_socket.connected()


@pytest.mark.asyncio
async def test_timeout(aio_socket):
    timeout = 0.1
    reply = await aio_socket.write_readline(IDN_REQ, timeout=timeout)
    assert reply == IDN_REP

    start = time.time()
    reply = await aio_socket.write_readline(b"sleep 0.05\n")
    dt = time.time() - start
    assert dt > 0.05
    assert reply == b"OK\n"

    timeout = 0.1
    start = time.time()
    await aio_socket.write_readline(b"sleep 0.05\n", timeout=timeout)
    dt = time.time() - start
    assert dt < timeout

    timeout = 0.09
    with pytest.raises(ConnectionTimeoutError):
        start = time.time()
        try:
            await aio_socket.write_readline(b"sleep 1\n", timeout=timeout)
        finally:
            dt = time.time() - start
        assert dt > timeout and dt < (timeout + 0.05)

    await aio_socket.close()


@pytest.mark.asyncio
async def test_line_stream(aio_socket):
    request = b"data? 2\n"
    await aio_socket.write(request)
    i = 0
    async for line in LineStream(aio_socket):
        assert line == b"1.2345 5.4321 12345.54321\n"
        i += 1
    assert i == 2
    assert aio_socket.connection_counter == 1
    assert not aio_socket.connected()


@pytest.mark.asyncio
async def test_block_stream(aio_socket):
    request = b"data? -5\n"
    await aio_socket.write(request)
    i = 0
    async for line in BlockStream(aio_socket, 12):
        assert line == "message {:04d}".format(i).encode()
        i += 1
    assert i == 5
    assert aio_socket.connection_counter == 1
    assert not aio_socket.connected()
