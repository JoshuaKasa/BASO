extern crate regex;
use regex::Regex;

#[derive(Debug, Clone)]
pub struct Token {
    pub r#type: String,
    pub value: String,
    pub line_number: i32,
    pub column_number: i32
}

#[derive(Debug)]
pub struct CorelLexer {
    pub source_code: String,
    pub tokens: Vec<Token>,
    pub current_line: i32,
    pub current_column: i32,
    pub position : i32
}

impl Default for CorelLexer {
    fn default() -> Self {
        Self {
            source_code: String::new(),
            tokens: Vec::new(),
            current_line: 1,
            current_column: 0,
            position: 0
        }
    }
}

impl CorelLexer {
    pub fn tokenize(&self) -> Vec<Token> {
        let regex_tokens = Self::initialize_regex_tokens();
        let mut tokens: Vec<Token> = Vec::new();
        let mut current_line = 1;
        let mut current_column = 0;

        let mut position = 0;
        while position < self.source_code.len() {
            let mut matched = false;

            for (token_type, regex) in &regex_tokens {
                if let Some(mat) = regex.find(&self.source_code[position..]) {
                    if mat.start() == 0 { // Ensure the match is at the current position
                        let token = Token {
                            r#type: token_type.clone(),
                            value: mat.as_str().to_string(),
                            line_number: current_line,
                            column_number: current_column,
                        };
                        tokens.push(token);
                        position += mat.end();
                        current_column += mat.end() as i32;
                        matched = true;
                        break; // Exit the loop after the first match
                    }
                }
            }

            if !matched {
                // Handle newlines and increment position
                if self.source_code.chars().nth(position).unwrap() == '\n' {
                    current_line += 1;
                    current_column = 0;
                } else {
                    current_column += 1;
                }
                position += 1;
            }
        }

        tokens
    }

    fn initialize_regex_tokens() -> Vec<(String, Regex)> {
        // Order matters here: more specific patterns are placed before broader ones.
        let regex_tokens = vec![
            ("STARTKEY".to_string(), Regex::new(r"--<[^>\r\n]+>").unwrap()),
            ("WAIT".to_string(), Regex::new(r"\bwait\b").unwrap()),
            ("MOVE".to_string(), Regex::new(r"\bmove\b").unwrap()),
            ("PRESS".to_string(), Regex::new(r"\bpress\b").unwrap()),
            ("CLICK".to_string(), Regex::new(r"\bclick\b").unwrap()),
            ("LOOP".to_string(), Regex::new(r"\bloop\b").unwrap()),
            ("STRING".to_string(), Regex::new(r#"('([^']*)')|(\"([^\"]*)\")"#).unwrap()),
            ("TIME".to_string(), Regex::new(r"\b\d+(s|ms|cs|ds)\b").unwrap()),
            ("COORDINATE".to_string(), Regex::new(r"-?\d+(x|y)\b").unwrap()),
            ("NUMBER".to_string(), Regex::new(r"\b[0-9]+\b").unwrap()),
            ("COMMENT".to_string(), Regex::new(r"//.*").unwrap()),
            ("LPAREN".to_string(), Regex::new(r"\(\s*").unwrap()),
            ("RPAREN".to_string(), Regex::new(r"\)\s*").unwrap()),
            ("LBRACE".to_string(), Regex::new(r"\{\s*").unwrap()),
            ("RBRACE".to_string(), Regex::new(r"\}\s*").unwrap()),
        ];

        regex_tokens
    }
}
