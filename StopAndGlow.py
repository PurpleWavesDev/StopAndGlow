# Imports and module path additions
import sys
import os.path as path
module_path = path.abspath("./modules")
if not module_path in sys.path:
    sys.path.append(module_path)

# General imports
from collections import namedtuple
# Logging
from importlib import reload
import logging as log

# Stop Lighting imports
from stopandglow.commands import *
import stopandglow.server as server


## Type-defs
Cmd = namedtuple('Cmd', ['command', 'arg', 'settings'])

## Classes
class ArgParser:
    def __init__(self, name='Stop Lighting', cmd_name=''):
        self.print_help = False
        self.name = name
        self.cmd_name = cmd_name
        
        self.initLogging('INFO')
        
    def parse(self, args):
        self.commands = []
        is_arg = False
        for arg in args:
            if arg[0:2] == '--' or arg[0:1] == '-':
                # Check for valid command
                try:
                    command = Commands(arg)
                    # Add command
                    self.commands.append(Cmd(command, "", {}))
                    is_arg = True
                except:
                    if arg == '--server':
                        server.run()
                    else:
                        if arg != '--help' and arg != '-h':
                            log.error(f"Unknown command '{arg}'")
                        self.print_help = True
                    break
            elif self.commands:
                # Add argument if it's right after the command string
                if is_arg:
                    # Check for loglevel, set and remove from commands
                    if self.commands[-1].command == '--loglevel':
                        self.initLogging(arg)
                        self.commands.pop()
                    else:
                        self.commands[-1] = self.commands[-1]._replace(arg=arg)
                        is_arg = False
                elif '=' in arg:
                    # Parse settings
                    key, val = arg.split('=')
                    self.commands[-1].settings[key] = val
                else:
                    log.error(f"Expected settings as 'key:value' pair, got '{arg}'")
                    self.print_help = True
                    break
            else:
                log.error(f"{arg} is not a valid command")
                self.print_help = True
                break

    def execute(self):
        if self.print_help:
            self.printHelp()
        else:
            log.info(f"Launching {self.name}...")
            from stopandglow.processing_queue import ProcessingQueue
            
            queue = ProcessingQueue()
            for command in self.commands:
                # Add to queue
                queue.putCommand(command.command, command.arg, command.settings)
            
            # Execute commands
            queue.execute()
    
    def initLogging(self, loglevel):
        # Init logger
        reload(log)
        log.basicConfig(level=log._nameToLevel[loglevel], format='[%(levelname)s] %(message)s')
    
    def printHelp(self):
        print(f"""
{self.name} help

Usage: python {self.cmd_name} <command> <argument> [<setting=value> [...]] [...]
Chain commands for each data loading/capturing/processing step.

Commands are:
    --config: 
    --calibration: 
    --preview: 
    --capture: 
    --load: 
    --load_hdri: 
    --process: 
    --render: 
    --view: 
    --save: 
    --send: 
    --lights: 
    --sleep: 
    --loglevel:
    --server:
""")


if __name__ == '__main__':
    parser = ArgParser(cmd_name=sys.argv[0])
    parser.parse(sys.argv[1:])
    parser.execute()
    