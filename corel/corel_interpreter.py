import re
import time
import sys
import json
import ctypes
import pyautogui

# Modifying print to flush immediately
# Taken from: https://stackoverflow.com/questions/230751/how-to-flush-output-of-python-print
def print(*objects, sep=' ', end='\n', file=sys.stdout, flush=True):
    __builtins__.print(*objects, sep=sep, end=end, file=file, flush=flush)

# Function for moving the mouse at the OS level as pyautogui doesn't work
MOUSEEVENTF_MOVE = 0x0001 # This constant is taken from the Windows API
def move_cursor(x, y):
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, x, y, 0, 0)

# pyautogui minimum time between clicks
pyautogui.MINIMUM_DURATION = 0
pyautogui.MINIMUM_SLEEP = 0
pyautogui.PAUSE = 0

# Nodes
class ASTnode:
    def __init__(self, type):
        self.type = type
        self.children = []

    def __repr__(self):
        return f"ASTnode({repr(self.type)}, {repr(self.children)})"

class WAITnode(ASTnode):
    def __init__(self, type, value, magnitude):
        super().__init__(type)
        self.value = value
        self.magnitude = magnitude

    def __repr__(self):
        return f"WAITnode({repr(self.type)}, {repr(self.value)}, {repr(self.magnitude)})"

class PRESSnode(ASTnode):
    def __init__(self, type, value):
        super().__init__(type)
        self.value = value.replace('"', '').replace("'", '').lower() # Remove the quotes from the string

    def __repr__(self):
        return f"PRESSnode({repr(self.type)}, {repr(self.value)})"

class KEYnode(ASTnode):
    def __init__(self, type, value):
        super().__init__(type)
        self.value = value.replace('"', '').replace("'", '').lower()

    def __repr__(self):
        return f"KEYnode({repr(self.type)}, {repr(self.value)})"

class CLICKnode(ASTnode):
    def __init__(self, type, value):
        super().__init__(type)
        self.value = value.replace('"', '').replace("'", '').lower() # Remove the quotes from the string

    def __repr__(self):
        return f"CLICKnode({repr(self.type)}, {repr(self.value)})"

class MOVEnode(ASTnode):
    def __init__(self, type, direction, value):
        super().__init__(type)
        self.direction = direction
        self.value = value

    def __repr__(self):
        return f"MOVEnode({repr(self.type)}, {repr(self.direction)}, {repr(self.value)})"

class LOOPnode(ASTnode):
    def __init__(self, type, value):
        super().__init__(type)
        self.value = value
        self.children = []

    def __repr__(self):
        return f"LOOPnode({repr(self.type)}, {repr(self.value)})"

class STRINGnode(ASTnode):
    def __init__(self, type, value):
        super().__init__(type)
        self.value = value

    def __repr__(self):
        return f"STRINGnode({repr(self.type)}, {repr(self.value)})"

# Interpreter
class CorelInterpreter:
    def __init__(self, ast):
        self.ast = ast

    def run(self):
        for node in self.ast:
            try:
                self.execute_node(node)
            except Exception as e:
                print(f'Unexpected error: {e}')

    def execute_node(self, node):
        if isinstance(node, WAITnode):
            self.execute_WAIT(node)
        elif isinstance(node, PRESSnode):
            self.execute_PRESS(node)
        elif isinstance(node, MOVEnode):
            self.execute_MOVE(node)
        elif isinstance(node, CLICKnode):
            self.execute_CLICK(node)
        elif isinstance(node, LOOPnode):
            self.execute_LOOP(node)
        else:
            raise Exception(f'Invalid node type: {node.type}')

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
        if node.value in pyautogui.KEYBOARD_KEYS:
            print(f'Pressing {node.value}...')
            pyautogui.press(node.value)
        else:
            raise Exception(f'Invalid key: {node.value}\nValid keys: {pyautogui.KEYBOARD_KEYS}')
    
    def execute_MOVE(self, node):
        print(f'Moving {node.value} {node.direction}...')
        if node.direction == 'x':
            move_cursor(node.value, 0)
        elif node.direction == 'y':
            move_cursor(0, node.value)
        else:
            raise Exception(f'Invalid direction: {node.direction}\nValid directions: x, y')

    def execute_CLICK(self, node):
        valid_buttons = ['left', 'middle', 'right']
        if node.value not in valid_buttons:
            raise Exception(f'Invalid button: {node.value}\nValid buttons: {valid_buttons}')
        
        pyautogui.click(button=node.value)

    def execute_LOOP(self, node):
        print(f'Looping {node.value} times...')
        for i in range(node.value):
            for child in node.children:
                self.execute_node(child)

# Debug code
def build_ast_from_json(json_file):
    def create_node(node_data):
        node_type = list(node_data['node_type'].keys())[0]
        node_info = node_data['node_type'][node_type]

        if node_type == "KEY":
            return KEYnode(node_type, node_info['value'])
        elif node_type == "LOOP":
            loop_node = LOOPnode(node_type, node_info['value'])
            for child in node_info['children']:  # Look into 'children' inside 'node_type'
                loop_node.children.append(create_node(child))
            return loop_node
        elif node_type == "MOVE":
            return MOVEnode(node_type, node_info['direction'], node_info['value'])
        elif node_type == "PRESS":
            return PRESSnode(node_type, node_info['value'])
        elif node_type == "WAIT":
            return WAITnode(node_type, node_info['value'], node_info['magnitude'])
        else:
            raise Exception(f'Unknown node type: {node_type}')

    ast = []
    for node in json_file:
        ast.append(create_node(node))
    
    return ast

def main(arg):
    print('AST from JSON:')
    with open(arg, 'r') as file:
        json_data = json.load(file)
        ast = build_ast_from_json(json_data)
   
    for node in ast:
        print(node)
        if isinstance(node, LOOPnode):
            for child in node.children:
                print('\t' + str(child))

    print('\nRunning interpreter...')
    interpreter = CorelInterpreter(ast)
    interpreter.run()

if __name__ == '__main__':
    main(sys.argv[1])
