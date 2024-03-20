import pickle
import numpy
import zmq
from typing import Any
from numpy.typing import ArrayLike

def send(socket: zmq.Socket, obj, flags=0, protocol=pickle.HIGHEST_PROTOCOL):
    """send pickled object, throws exception on failure"""
    socket.send(pickle.dumps(obj, protocol), flags=flags)

def receive(socket: zmq.Socket, flags=0) -> Any:
    """receive pickled object, throws exception on failure"""
    return pickle.loads(socket.recv(flags))


def send_array(socket, A, id=0, flags=0, copy=True, track=False):
    """send a numpy array with metadata, throws exception on failure"""
    md = dict(
        dtype=str(A.dtype),
        shape=A.shape,
        id=id,
    )
    socket.send_json(md, flags | zmq.SNDMORE)
    socket.send(A, flags, copy=copy, track=track)


def receive_array(socket, flags=0, copy=True, track=False) -> (int, ArrayLike):
    """receive a numpy array, throws exception on failure"""
    md = socket.recv_json(flags=flags)
    msg = socket.recv(flags=flags, copy=copy, track=track)
    buf = memoryview(msg)
    A = numpy.frombuffer(buf, dtype=md['dtype'])
    return (md['id'], A.reshape(md['shape']))
