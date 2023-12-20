import time
import threading

class Worker:
    def work(self) -> bool:
        return True

class Timer:
    def __init__(self, worker: Worker):
        self.worker = worker

    def start(self, interval=0):
        self.interval = interval
        self.running = True
        self.thread = threading.Thread(target=timer_fn, args=(self, self.worker, ))
        self.thread.start()

    def stop(self):
        self.running = False
        if wait:
            self.thread.join()

    def join(self):
        self.thread.join()


def timer_fn(timer, worker):
    next_call = time.time()
    while timer.running:
        # Work
        if not worker.work():
            timer.running = False
            break
        
        if timer.interval != 0:
            # Sleep until next frame
            next_call = next_call+timer.interval
            time_sleep = next_call - time.time()

            # Check for overruns or sleep remaining time
            if time_sleep < 0:
                print(f"Error: Overrun timer by {abs(time_sleep)}")
                next_call = time.time()
            else:
                time.sleep(time_sleep)
