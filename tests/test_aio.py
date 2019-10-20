import os
import sys
import subprocess
import asyncio.subprocess

import pytest

from sockio.aio import Socket, main

from conftest import IDN_REQ, IDN_REP, WRONG_REQ, WRONG_REP


def test_socket_creation():
    sock = Socket('example.com', 34567)
    assert sock.host == 'example.com'
    assert sock.port == 34567
    assert sock.auto_reconnect == True
    assert not sock.connected
    assert sock.connection_counter == 0

@pytest.mark.asyncio
async def test_open_fail(unused_tcp_port):
    sock = Socket('0', unused_tcp_port)
    assert not sock.connected
    assert sock.connection_counter == 0

    with pytest.raises(ConnectionRefusedError):
        await sock.open()
    assert not sock.connected
    assert sock.connection_counter == 0

@pytest.mark.asyncio
async def test_write_fail(unused_tcp_port):
    sock = Socket('0', unused_tcp_port)
    assert not sock.connected
    assert sock.connection_counter == 0

    with pytest.raises(ConnectionRefusedError):
        await sock.write(IDN_REQ)
    assert not sock.connected
    assert sock.connection_counter == 0

@pytest.mark.asyncio
async def test_write_readline_fail(unused_tcp_port):
    sock = Socket('0', unused_tcp_port)
    assert not sock.connected
    assert sock.connection_counter == 0

    with pytest.raises(ConnectionRefusedError):
        await sock.write_readline(IDN_REQ)
    assert not sock.connected
    assert sock.connection_counter == 0


@pytest.mark.asyncio
async def test_open_close(aio_server, aio_sock):
    assert not aio_sock.connected
    assert aio_sock.connection_counter == 0
    assert aio_server.sockets[0].getsockname() == (aio_sock.host, aio_sock.port)

    await aio_sock.open()
    assert aio_sock.connected
    assert aio_sock.connection_counter == 1

    with pytest.raises(ConnectionError):
        await aio_sock.open()
    assert aio_sock.connected
    assert aio_sock.connection_counter == 1

    await aio_sock.close()
    assert not aio_sock.connected
    assert aio_sock.connection_counter == 1
    await aio_sock.open()
    assert aio_sock.connected
    assert aio_sock.connection_counter == 2
    await aio_sock.close()
    await aio_sock.close()
    assert not aio_sock.connected
    assert aio_sock.connection_counter == 2


@pytest.mark.asyncio
async def test_callbacks(aio_server):
    host, port = aio_server.sockets[0].getsockname()
    state = dict(made=0, lost=0, eof=0)

    def made(transport):
        state['made'] += 1

    def lost(exc):
        state['lost'] += 1

    def eof():
        state['eof'] += 1

    aio_sock = Socket(host, port, on_connection_made=made,
                      on_connection_lost=lost, on_eof_received=eof)
    assert not aio_sock.connected
    assert aio_sock.connection_counter == 0
    assert state['made'] == 0
    assert state['lost'] == 0
    assert state['eof'] == 0

    await aio_sock.open()
    assert aio_sock.connected
    assert aio_sock.connection_counter == 1
    assert state['made'] == 1
    assert state['lost'] == 0
    assert state['eof'] == 0

    with pytest.raises(ConnectionError):
        await aio_sock.open()
    assert aio_sock.connected
    assert aio_sock.connection_counter == 1
    assert state['made'] == 1
    assert state['lost'] == 0
    assert state['eof'] == 0

    await aio_sock.close()
    assert not aio_sock.connected
    assert aio_sock.connection_counter == 1
    assert state['made'] == 1
    assert state['lost'] == 1
    assert state['eof'] == 0

    await aio_sock.open()
    assert aio_sock.connected
    assert aio_sock.connection_counter == 2
    assert state['made'] == 2
    assert state['lost'] == 1
    assert state['eof'] == 0

    await aio_sock.close()
    assert not aio_sock.connected
    assert aio_sock.connection_counter == 2
    assert state['made'] == 2
    assert state['lost'] == 2
    assert state['eof'] == 0

    await aio_sock.close()
    assert not aio_sock.connected
    assert aio_sock.connection_counter == 2
    assert state['made'] == 2
    assert state['lost'] == 2
    assert state['eof'] == 0

@pytest.mark.asyncio
async def test_coroutine_callbacks(aio_server):
    host, port = aio_server.sockets[0].getsockname()

    state = dict(made=0, lost=0, eof=0)

    async def made(transport):
        await asyncio.sleep(0.1)
        state['made'] += 1

    async def lost(exc):
        await asyncio.sleep(0.1)
        state['lost'] += 1

    async def eof():
        await asyncio.sleep(0.1)
        state['eof'] += 1

    aio_sock = Socket(host, port, on_connection_made=made,
                      on_connection_lost=lost, on_eof_received=eof)

    assert not aio_sock.connected
    assert aio_sock.connection_counter == 0
    assert state['made'] == 0
    assert state['lost'] == 0
    assert state['eof'] == 0

    await aio_sock.open()
    assert aio_sock.connected
    assert aio_sock.connection_counter == 1
    assert state['made'] == 0
    assert state['lost'] == 0
    assert state['eof'] == 0
    await asyncio.sleep(0.11)
    assert state['made'] == 1
    assert state['lost'] == 0
    assert state['eof'] == 0

    with pytest.raises(ConnectionError):
        await aio_sock.open()
    assert aio_sock.connected
    assert aio_sock.connection_counter == 1
    assert state['made'] == 1
    assert state['lost'] == 0
    assert state['eof'] == 0

    await aio_sock.close()
    assert not aio_sock.connected
    assert aio_sock.connection_counter == 1
    assert state['made'] == 1
    assert state['lost'] == 0
    assert state['eof'] == 0
    await asyncio.sleep(0.11)
    assert state['made'] == 1
    assert state['lost'] == 1
    assert state['eof'] == 0

    await aio_sock.open()
    assert aio_sock.connected
    assert aio_sock.connection_counter == 2
    assert state['made'] == 1
    assert state['lost'] == 1
    assert state['eof'] == 0
    await asyncio.sleep(0.11)
    assert state['made'] == 2
    assert state['lost'] == 1
    assert state['eof'] == 0

    await aio_sock.close()
    assert not aio_sock.connected
    assert aio_sock.connection_counter == 2
    assert state['made'] == 2
    assert state['lost'] == 1
    assert state['eof'] == 0
    await asyncio.sleep(0.11)
    assert state['made'] == 2
    assert state['lost'] == 2
    assert state['eof'] == 0

    await aio_sock.close()
    assert not aio_sock.connected
    assert aio_sock.connection_counter == 2
    assert state['made'] == 2
    assert state['lost'] == 2
    assert state['eof'] == 0
    await asyncio.sleep(0.11)
    assert state['made'] == 2
    assert state['lost'] == 2
    assert state['eof'] == 0

@pytest.mark.asyncio
async def test_error_callback(aio_server):
    host, port = aio_server.sockets[0].getsockname()

    state = dict(made=0)

    def error_callback(transport):
        state['made'] += 1
        raise RuntimeError('cannot handle this')

    aio_sock = Socket(host, port, on_connection_made=error_callback)

    assert not aio_sock.connected
    assert aio_sock.connection_counter == 0
    assert state['made'] == 0

    await aio_sock.open()
    assert aio_sock.connected
    assert aio_sock.connection_counter == 1
    assert state['made'] == 1


@pytest.mark.skip('bug in python server.close() ?')
# @pytest.mark.asyncio
async def test_eof_callback(aio_server):
    host, port = aio_server.sockets[0].getsockname()
    state = dict(made=0, lost=0, eof=0)

    def made(transport):
        state['made'] += 1

    def lost(exc):
        state['lost'] += 1

    def eof():
        state['eof'] += 1

    aio_sock = Socket(host, port, on_connection_made=made,
                      on_connection_lost=lost, on_eof_received=eof)
    assert not aio_sock.connected
    assert aio_sock.connection_counter == 0
    assert state['made'] == 0
    assert state['lost'] == 0
    assert state['eof'] == 0

    await aio_sock.open()
    assert aio_sock.connected
    assert aio_sock.connection_counter == 1
    assert state['made'] == 1
    assert state['lost'] == 0
    assert state['eof'] == 0

    aio_server.close()
    await aio_server.wait_closed()
    assert not aio_server.is_serving()

    assert state['made'] == 1
    assert state['lost'] == 0
    assert state['eof'] == 1


@pytest.mark.asyncio
async def test_write_readline(aio_sock):
    for request, expected in [(IDN_REQ,  IDN_REP),
                              (WRONG_REQ,  WRONG_REP)]:
        coro = aio_sock.write_readline(request)
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert aio_sock.connected
        assert aio_sock.connection_counter == 1
        assert expected == reply


@pytest.mark.asyncio
async def test_write_readlines(aio_sock):
    for request, expected in [(IDN_REQ,  [IDN_REP]), (2*IDN_REQ,  2*[IDN_REP]),
                              (IDN_REQ + WRONG_REQ,  [IDN_REP, WRONG_REP])]:
        coro = aio_sock.write_readlines(request, len(expected))
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert aio_sock.connected
        assert aio_sock.connection_counter == 1
        assert expected == reply


@pytest.mark.asyncio
async def test_writelines_readlines(aio_sock):
    for request, expected in [([IDN_REQ],  [IDN_REP]), (2*[IDN_REQ],  2*[IDN_REP]),
                              ([IDN_REQ, WRONG_REQ],  [IDN_REP, WRONG_REP])]:
        coro = aio_sock.writelines_readlines(request)
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert aio_sock.connected
        assert aio_sock.connection_counter == 1
        assert expected == reply


@pytest.mark.asyncio
async def test_writelines(aio_sock):
    for request, expected in [([IDN_REQ],  [IDN_REP]), (2*[IDN_REQ],  2*[IDN_REP]),
                              ([IDN_REQ, WRONG_REQ],  [IDN_REP, WRONG_REP])]:
        coro = aio_sock.writelines(request)
        assert asyncio.iscoroutine(coro)
        answer = await coro
        assert aio_sock.connected
        assert aio_sock.connection_counter == 1
        assert answer is None

        coro = aio_sock.readlines(len(expected))
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert aio_sock.connected
        assert aio_sock.connection_counter == 1
        assert expected == reply


@pytest.mark.asyncio
async def test_readline(aio_sock):
    for request, expected in [(IDN_REQ,  IDN_REP),
                              (WRONG_REQ,  WRONG_REP)]:
        coro = aio_sock.write(request)
        assert asyncio.iscoroutine(coro)
        answer = await coro
        assert aio_sock.connected
        assert aio_sock.connection_counter == 1
        assert answer is None
        coro = aio_sock.readline()
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert expected == reply


@pytest.mark.asyncio
async def test_readuntil(aio_sock):
    for request, expected in [(IDN_REQ,  IDN_REP),
                              (WRONG_REQ,  WRONG_REP)]:
        coro = aio_sock.write(request)
        assert asyncio.iscoroutine(coro)
        answer = await coro
        assert aio_sock.connected
        assert aio_sock.connection_counter == 1
        assert answer is None
        coro = aio_sock.readuntil(b'\n')
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert expected == reply


@pytest.mark.asyncio
async def test_readexactly(aio_sock):
    for request, expected in [(IDN_REQ,  IDN_REP),
                              (WRONG_REQ,  WRONG_REP)]:
        coro = aio_sock.write(request)
        assert asyncio.iscoroutine(coro)
        answer = await coro
        assert aio_sock.connected
        assert aio_sock.connection_counter == 1
        assert answer is None
        coro = aio_sock.readexactly(len(expected) - 5)
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert expected[:-5] == reply
        coro = aio_sock.readexactly(5)
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert expected[-5:] == reply


@pytest.mark.asyncio
async def test_readlines(aio_sock):
    for request, expected in [(IDN_REQ,  [IDN_REP]), (2*IDN_REQ,  2*[IDN_REP]),
                              (IDN_REQ + WRONG_REQ,  [IDN_REP, WRONG_REP])]:
        coro = aio_sock.write(request)
        assert asyncio.iscoroutine(coro)
        answer = await coro
        assert aio_sock.connected
        assert aio_sock.connection_counter == 1
        assert answer is None
        coro = aio_sock.readlines(len(expected))
        assert asyncio.iscoroutine(coro)
        reply = await coro
        assert expected == reply


@pytest.mark.asyncio
async def test_read(aio_sock):
    for request, expected in [(IDN_REQ,  IDN_REP),
                              (WRONG_REQ,  WRONG_REP)]:
        coro = aio_sock.write(request)
        assert asyncio.iscoroutine(coro)
        answer = await coro
        assert aio_sock.connected
        assert aio_sock.connection_counter == 1
        assert answer is None
        reply, n = b'', 0
        while len(reply) < len(expected) and n < 2:
            coro = aio_sock.read(1024)
            assert asyncio.iscoroutine(coro)
            reply += await coro
            n += 1
        assert expected == reply


@pytest.mark.asyncio
async def test_stream(aio_sock):
    request = b'data? 2\n'
    await aio_sock.write(request)
    i = 0
    async for line in aio_sock:
        assert line == b'1.2345 5.4321 12345.54321\n'
        i += 1
    assert i == 2
    assert aio_sock.connection_counter == 1
    assert not aio_sock.connected


# @pytest.mark.skipif(os.environ.get('CONDA_SHLVL', '0') != '0', reason='Inside conda environment')
@pytest.mark.asyncio
async def test_cli(aio_server, capsys):
    _, port = aio_server.sockets[0].getsockname()
    await main(['--port', str(port)])
    captured = capsys.readouterr()
    assert captured.out == repr(IDN_REP) + '\n'
