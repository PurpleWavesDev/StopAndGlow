import sys
import os.path as path
# Additional modulepaths
module_path = path.abspath("./modules")
if not module_path in sys.path:
    sys.path.append(module_path)

import logging as log

import smvp_srv.server as server

if __name__ == '__main__':
    log.basicConfig(level='DEBUG', format='[%(levelname)s] %(message)s')
    server.run()
