# COREL stands for: Command, Oriented, Recoil, Elimination, Language
import re
from CorelLexer import CorelLexer

# Building the AST
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

class NUMBERnode(ASTnode):
    def __init__(self, type, value):
        super().__init__(type)
        self.value = value

    def __repr__(self):
        return f"NUMBERnode({repr(self.type)}, {repr(self.value)})"

class COMMENTnode(ASTnode):
    def __init__(self, type, value):
        super().__init__(type)
        self.value = value

    def __repr__(self):
        return f"COMMENTnode({repr(self.type)}, {repr(self.value)})"

class CorelParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_position = 0
        self.nodes = [] # List of nodes inside the AST
        self.variables = {} # Dictionary of variables (not needed for now but i guess you never know, right?)

    def parse_line(self):
        token = self.tokens[self.current_position]

        if token.type == 'WAIT':
            self.parse_wait()
        elif token.type == 'PRESS':
            self.parse_press()
        elif token.type == 'CLICK':
            self.parse_click()
        elif token.type == 'LOOP':
            self.parse_loop()
        elif token.type == 'STRING':
            self.parse_string()
        elif token.type == 'NUMBER':
            self.parse_number()
        elif token.type == 'MOVE':
            self.parse_move()
        else:
            raise Exception(f'Invalid syntax at line {token.line_number}, character {token.character_position}')

    def parse(self):
        while self.current_position < len(self.tokens):
            self.parse_line()

        return self.nodes

    def parse_wait(self):
        self.current_position += 1  # Skip the WAIT token

        token = self.tokens[self.current_position]
        if token.type != 'LPAREN':
            raise Exception(f'Expected "(" after "wait", at line {token.line_number}, character {token.character_position}')
        self.current_position += 1  # Skip the LPAREN token

        token = self.tokens[self.current_position]
        if token.type != 'TIME':
            raise Exception(f'Expected time value (e.g., 10s, 10ms) after "(", at line {token.line_number}, character {token.character_position}')
        
        # Use regex to extract number and magnitude from the TIME token
        time_value = token.value
        pattern = re.compile(r'(\d+)(s|ms|cs|ds)')
        match = pattern.match(time_value)
        if not match:
            raise Exception(f'Invalid time format at line {token.line_number}, character {token.character_position}')

        number, magnitude = match.groups()
        self.current_position += 1  # Skip the TIME token

        if self.tokens[self.current_position].type != 'RPAREN':
            raise Exception(f'Expected ")" after time value, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1  # Skip the RPAREN token

        # Creating the WAITnode with number and magnitude
        node = WAITnode('WAIT', int(number), magnitude)
        self.nodes.append(node)

    def parse_press(self):
        self.current_position += 1 # Skip the PRESS token
        token = self.tokens[self.current_position]
        if self.tokens[self.current_position].type != 'LPAREN':
            raise Exception(f'There must be a open parentheses "(" before a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the LPAREN token
        if self.tokens[self.current_position].type != 'STRING':
            raise Exception(f'The function arguments must be a string, at line {token.line_number}, character {token.character_position}')
        token_value = self.tokens[self.current_position].value # Save the value of the STRING token
        self.current_position += 1 # Skip the STRING token
        if self.tokens[self.current_position].type != 'RPAREN':
            raise Exception(f'There must be a close parentheses ")" after a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the RPAREN token

        # Creating the AST node
        node = PRESSnode('PRESS', token_value)
        self.nodes.append(node)

    def parse_click(self):
        self.current_position += 1 # Skip the CLICK token
        token = self.tokens[self.current_position]
        if self.tokens[self.current_position].type != 'LPAREN':
            raise Exception(f'There must be a open parentheses "(" before a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the LPAREN token
        if self.tokens[self.current_position].type != 'STRING':
            raise Exception(f'The function arguments must be a string, at line {token.line_number}, character {token.character_position}')
        token_value = self.tokens[self.current_position].value # Save the value of the STRING token
        self.current_position += 1 # Skip the STRING token
        if self.tokens[self.current_position].type != 'RPAREN':
            raise Exception(f'There must be a close parentheses ")" after a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the RPAREN token

        # Creating the AST node
        node = CLICKnode('CLICK', token_value)
        self.nodes.append(node)

    def parse_loop(self):
        token = self.tokens[self.current_position]
        self.current_position += 1  # Skip the LOOP token

        if self.tokens[self.current_position].type != 'LPAREN':
            raise Exception(f'Expected "(" after "loop", at line {token.line_number}, character {token.character_position}')
        self.current_position += 1  # Skip the LPAREN token

        if self.tokens[self.current_position].type != 'NUMBER':
            raise Exception(f'Loop count must be a number, at line {token.line_number}, character {token.character_position}')
        
        # Convert the loop count to an integer
        loop_count = self.tokens[self.current_position].value
        try:
            loop_count = int(loop_count)
        except ValueError:
            raise Exception(f'Loop count must be a number, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1  # Skip the NUMBER token

        if self.tokens[self.current_position].type != 'RPAREN':
            raise Exception(f'Expected ")" after loop count, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1  # Skip the RPAREN token

        if self.tokens[self.current_position].type != 'LBRACE':
            raise Exception(f'Expected "{{" to start loop body, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1  # Skip the LBRACE token

        loop_body_nodes = []
        while self.tokens[self.current_position].type != 'RBRACE':
            self.parse_line()
            loop_body_nodes.append(self.nodes.pop())

        self.current_position += 1  # Skip the RBRACE token

        node = LOOPnode('LOOP', loop_count)
        node.children = loop_body_nodes
        self.nodes.append(node)

    def parse_string(self):
        token = self.tokens[self.current_position]
        token_value = self.tokens[self.current_position].value
        self.current_position += 1 # Skip the STRING token

        # Creating the AST node
        node = STRINGnode('STRING', token_value)
        self.nodes.append(node)

    def parse_number(self):
        token = self.tokens[self.current_position]
        token_value = self.tokens[self.current_position].value
        self.current_position += 1 # Skip the NUMBER token

        # Creating the AST node
        node = NUMBERnode('NUMBER', token_value)
        self.nodes.append(node)

    def parse_move(self):
        self.current_position += 1 # Skip the MOVE token
        token = self.tokens[self.current_position]
        
        # Check if the next token is a LPAREN
        if self.tokens[self.current_position].type != 'LPAREN':
            raise Exception(f'There must be a open parentheses "(" before a function arguments, at line {token.line_number}, character {token.character_position}')

        self.current_position += 1 # Skip the LPAREN token

        # Check if the next token is a NUMBER
        if self.tokens[self.current_position].type == 'NUMBER':
            raise Exception(f'You must the direction (x or y) after the number, at line {token.line_number}, character {token.character_position}')
        elif self.tokens[self.current_position].type != 'COORDINATES':
            raise Exception(f'The function arguments must be a coordinate, at line {token.line_number}, character {token.character_position}')
        
        # Save the value of the COORDINATES token
        token_value = self.tokens[self.current_position].value 
        self.current_position += 1 # Skip the COORDINATES token

        # Check if the next token is a closed parentheses
        if self.tokens[self.current_position].type != 'RPAREN':
            raise Exception(f'There must be a close parentheses ")" after a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1

        # Getting the values
        pattern = re.compile(r'(-?\d+)(x|y)\b')
        match = pattern.match(token_value) # Use regex to extract the direction and the value from the COORDINATES token
        if not match:
            raise Exception(f'Invalid coordinate format at line {token.line_number}, character {token.character_position}')

        try:
            value, direction = match.groups()
            value = int(value)
        except ValueError:
            raise Exception(f'Invalid coordinate format at line {token.line_number}, character {token.character_position}')

        # Creating the AST node
        node = MOVEnode('MOVE', direction, value)
        self.nodes.append(node)
