import pickle
import numpy

def send(socket, obj, flags=0, protocol=pickle.HIGHEST_PROTOCOL):
    """send pickled object"""
    return socket.send(pickle.dumps(obj, protocol), flags=flags)

def receive(socket, flags=0):
    """receive pickled object"""
    return pickle.loads(socket.recv(flags))


def send_array(socket, A, flags=0, copy=True, track=False):
    """send a numpy array with metadata"""
    md = dict(
        dtype=str(A.dtype),
        shape=A.shape,
    )
    socket.send_json(md, flags | zmq.SNDMORE)
    return socket.send(A, flags, copy=copy, track=track)


def receive_array(socket, flags=0, copy=True, track=False):
    """receive a numpy array"""
    md = socket.recv_json(flags=flags)
    msg = socket.recv(flags=flags, copy=copy, track=track)
    buf = memoryview(msg)
    A = numpy.frombuffer(buf, dtype=md["dtype"])
    return A.reshape(md["shape"])
