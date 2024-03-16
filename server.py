import sys
import os.path as path
module_path = path.abspath("./modules")
if not module_path in sys.path:
    sys.path.append(module_path)

import smvp_srv.server as server

if __name__ == '__main__':
    server.run()
