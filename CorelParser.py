# COREL stands for: Command, Oriented, Recoil, Elimination, Language
import re
from CorelLexer import Token, Lexer

# Building the AST
class ASTnode:
    def __init__(self, type):
        self.type = type
        self.children = []

    def __repr__(self):
        return f"ASTnode({repr(self.type)}, {repr(self.children)})"

class WAITnode(ASTnode):
    def __init__(self, type, value):
        super().__init__(type)
        self.value = value

    def __repr__(self):
        return f"WAITnode({repr(self.type)}, {repr(self.value)})"

class PRESSnode(ASTnode):
    def __init__(self, type, value):
        super().__init__(type)
        self.value = value

    def __repr__(self):
        return f"PRESSnode({repr(self.type)}, {repr(self.value)})"

class CLICKnode(ASTnode):
    def __init__(self, type, value):
        super().__init__(type)
        self.value = value

    def __repr__(self):
        return f"CLICKnode({repr(self.type)}, {repr(self.value)})"

class LOOPnode(ASTnode):
    def __init__(self, type, value):
        super().__init__(type)
        self.value = value

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
        elif token.type == 'COMMENT':
            self.parse_comment()
        else:
            raise Exception(f'Invalid syntax at line {token.line_number}, character {token.character_position}')

    def parse(self):
        while self.current_position < len(self.tokens):
            self.parse_line()

        return self.nodes

    def parse_wait(self):
        token = self.tokens[self.current_position]
        token_value = self.tokens[self.current_position].value
        self.current_position += 1 # Skip the WAIT token
        if self.tokens[self.current_position].type != 'LPAREN':
            raise Exception(f'There must be a open parentheses "(" before a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the LPAREN token
        if self.tokens[self.current_position].type != 'NUMBER':
            raise Exception(f'The function arguments must be a number, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the NUMBER token
        if self.tokens[self.current_position].type != 'RPAREN':
            raise Exception(f'There must be a close parentheses ")" after a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the RPAREN token

        # Creating the AST node
        node = WAITnode('WAIT', token_value)
        self.nodes.append(node)

    def parse_press(self):
        token = self.tokens[self.current_position]
        token_value = self.tokens[self.current_position].value
        self.current_position += 1 # Skip the PRESS token
        if self.tokens[self.current_position].type != 'LPAREN':
            raise Exception(f'There must be a open parentheses "(" before a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the LPAREN token
        if self.tokens[self.current_position].type != 'STRING':
            raise Exception(f'The function arguments must be a string, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the STRING token
        if self.tokens[self.current_position].type != 'RPAREN':
            raise Exception(f'There must be a close parentheses ")" after a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the RPAREN token

        # Creating the AST node
        node = PRESSnode('PRESS', token_value)
        self.nodes.append(node)

    def parse_click(self):
        token = self.tokens[self.current_position]
        token_value = self.tokens[self.current_position].value
        self.current_position += 1 # Skip the CLICK token
        if self.tokens[self.current_position].type != 'LPAREN':
            raise Exception(f'There must be a open parentheses "(" before a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the LPAREN token
        if self.tokens[self.current_position].type != 'STRING':
            raise Exception(f'The function arguments must be a string, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the STRING token
        if self.tokens[self.current_position].type != 'RPAREN':
            raise Exception(f'There must be a close parentheses ")" after a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the RPAREN token

        # Creating the AST node
        node = CLICKnode('CLICK', token_value)
        self.nodes.append(node)

    def parse_loop(self):
        token = self.tokens[self.current_position]
        token_value = self.tokens[self.current_position].value
        self.current_position += 1 # Skip the LOOP token
        if self.tokens[self.current_position].type != 'LPAREN':
            raise Exception(f'There must be a open parentheses "(" before a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the LPAREN token
        if self.tokens[self.current_position].type != 'NUMBER':
            raise Exception(f'The function arguments must be a number, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the NUMBER token
        if self.tokens[self.current_position].type != 'RPAREN':
            raise Exception(f'There must be a close parentheses ")" after a function arguments, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the RPAREN token

        # Parsing the loop body
        if self.tokens[self.current_position].type != 'LBRACE':
            raise Exception(f'There must be a open brace "{{" before a loop body, at line {token.line_number}, character {token.character_position}')
        self.current_position += 1 # Skip the LBRACE token
        while self.tokens[self.current_position].type != 'RBRACE':
            self.parse_line()
        self.current_position += 1 # Skip the RBRACE token

        # Creating the AST node
        node = LOOPnode('LOOP', token_value)
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

    def parse_comment(self):
        token = self.tokens[self.current_position]
        token_value = self.tokens[self.current_position].value
        self.current_position += 1 # Skip the COMMENT token

        # Creating the AST node
        node = COMMENTnode('COMMENT', token_value)
        self.nodes.append(node)

corel_file = open('corel.corel', 'r')
corel_code = corel_file.read()
corel_file.close()

lexer = Lexer(corel_code)
tokens = lexer.tokenize()

parser = CorelParser(tokens)
nodes = parser.parse()
