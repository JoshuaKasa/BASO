# This is the COREL interpreter, which will take the AST and execute it.
# For those wondering the difference between an interpreter and a compiler:
# A compiler will take the source code and translate it into machine code.
# An interpreter will take the source code and execute it directly.
import re
import time
import sys
import ctypes
import pyautogui
import CorelParser
from CorelLexer import CorelLexer

# Modifying print to flush immediately
# Taken from: https://stackoverflow.com/questions/230751/how-to-flush-output-of-python-print
def print(*objects, sep=' ', end='\n', file=sys.stdout, flush=True):
    __builtins__.print(*objects, sep=sep, end=end, file=file, flush=flush)

# Interpreter
class CorelInterpreter:
    def __init__(self, ast):
        self.ast = ast

    def run(self):
        for node in self.ast:
            self.execute_node(node)

    def execute_node(self, node):
        if isinstance(node, CorelParser.WAITnode):
            self.execute_WAIT(node)
        elif isinstance(node, CorelParser.PRESSnode):
            self.execute_PRESS(node)
        elif isinstance(node, CorelParser.CLICKnode):
            self.execute_CLICK(node)
        elif isinstance(node, CorelParser.LOOPnode):
            self.execute_LOOP(node)

    def execute_WAIT(self, node):
        print(f'Waiting {node.value} {node.magnitude}...')
        
        sleep_time = node.value
        magnitude = node.magnitude
        match magnitude:
            case 's':
                sleep_time *= 1
            case 'ms':
                sleep_time /= 1000
            case 'cs':
                sleep_time /= 100
            case 'ds':
                sleep_time /= 10
            case _:
                raise Exception(f'Invalid time magnitude: {magnitude}')
        time.sleep(sleep_time)

    def execute_PRESS(self, node):
        print(f'Pressing {node.value}...')
        res = pyautogui.press(node.value) # Returns the key that was pressed (None if failed)
        if res == None:
            raise Exception(f'Invalid key: {node.value}\nValid keys: {pyautogui.KEYBOARD_KEYS}')

    def execute_CLICK(self, node):
        print(f'Clicking {node.value}...')
        res = pyautogui.click(button=node.value)
        if res == None:
            raise Exception(f'Invalid button: {node.value}\nValid buttons: {pyautogui.mouseInfo()}')

    def execute_LOOP(self, node):
        print(f'Looping {node.value} times...')
        for i in range(node.value):
            for child in node.children:
                self.execute_node(child)

# Debug code
def main(arg):
    with open(arg) as f:
        source_code = f.read()

    print('Source Code:')
    print(source_code)

    lexer = CorelLexer(source_code)
    tokens = lexer.tokenize()

    parser = CorelParser.CorelParser(tokens)
    ast = parser.parse()
    
    interpreter = CorelInterpreter(ast)
    interpreter.run()

if __name__ == '__main__':
    main(sys.argv[1])
