# COREL stands for: Command, Oriented, Recoil, Elimination, Language
import re

class Token:
    def __init__(self, type, value, line_number, character_position):
        self.type = type
        self.value = value
        self.line_number = line_number
        self.character_position = character_position

    def __repr__(self):
        return f'{self.type}:{self.value}'

class Lexer:
    def __init__(self, source_code):
        self.source_code = source_code # Source code is a string
        self.tokens = [] # List of tokens, empty at first
        self.current_position = 0 # Current position in the token list
        self.current_line = 1 # Current line number
        self.current_char_position = 0 # Current character position

    def tokenize(self):
        token_regex = [
            # Commands (using case-insensitive matching)
            ('WAIT', r'\bwait\b'),
            ('PRESS', r'\bpress\b'),
            ('CLICK', r'\bclick\b'),
            ('LOOP', r'\bloop\b'),

            # String Literals (for arguments like 'lmb')
            ('STRING', r"'[^']*'"),

            # Numerical values
            ('NUMBER', r'\b\d+\b'),

            # Parentheses and Brackets (space optional)
            ('LPAREN', r'\(\s*'),
            ('RPAREN', r'\s*\)'),
            ('LBRACE', r'\{\s*'),
            ('RBRACE', r'\s*\}'),

            # Comments
            ('COMMENT', r'//.*'),

            # Whitespace (ignored)
            ('WHITESPACE', r'\s+', None), # Not needed, but for completeness
        ]

        # Remove the WHITESPACE pattern or handle it differently
        token_regex = [pattern for pattern in token_regex if pattern[0] != 'WHITESPACE']

        regex_patterns = '|'.join('(?P<%s>%s)' % pair for pair in token_regex)
        for match in re.finditer(regex_patterns, self.source_code, re.IGNORECASE):
            kind = match.lastgroup
            value = match.group()
            start_pos = match.start()

            # Calculate line number and character position
            line_number = self.source_code.count('\n', 0, start_pos) + 1
            line_start = self.source_code.rfind('\n', 0, start_pos)
            if line_start < 0:
                line_start = 0
            character_position = start_pos - line_start

            if kind != 'WHITESPACE':
                token = Token(kind, value, line_number, character_position)
                self.tokens.append(token)

        return self.tokens

corel_file = open('corel.corel', 'r')
source_code = corel_file.read()
corel_file.close()

lexer = Lexer(source_code)
tokens = lexer.tokenize()
print(tokens)
