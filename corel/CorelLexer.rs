use regex::Regex;
use std::collections::HashMap;

#[derive(Debug)]

struct Token {
    type: String,
    value: String,
    line_number: i32,
    column_number: i32
}

struct CorelLexer {
    source_code: String,
    tokens: Vec<Token>,
    current_line: i32,
    current_column: i32,
    position : i32
}

impl CorelLexer {
    fn tokenize(&self) -> Vec<Token> {
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
                            type: token_type.clone(),
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

    fn initialize_regex_tokens() -> HashMap<String, Regex> {
        let mut regex_rokens = HashMap::new();

        // Inserting each regex pattern inside the HashMap
        // Used for defining the key that will start your macro
        regex_tokens.insert("STARTKEY", Regex::new(r"--<[a-zA-Z]+>").unwrap());

        // Commands, move and click the mouse, press a key, wait for a time, loop
        regex_tokens.insert("WAIT", Regex::new(r"\bwait\b").unwrap());
        regex_tokens.insert("MOVE", Regex::new(r"\bmove\b").unwrap());
        regex_tokens.insert("PRESS", Regex::new(r"\bpress\b").unwrap());
        regex_tokens.insert("CLICK", Regex::new(r"\bclick\b").unwrap());
        regex_tokens.insert("LOOP", Regex::new(r"\bloop\b").unwrap());
    
        // String literals, (e.g. 'left', 'right', 'f', 'z')
        regex_tokens.insert("STRING", Regex::new(r"('([^']*)')|(\"([^\"]*)\")").unwrap());
    
        // Numerical values, time: 1s, 1ms, 1cs, 1ds, coordinates: +-1x, +-1y
        regex_tokens.insert("NUMBER", Regex::new(r"\b[0-9]+\b").unwrap());
        regex_tokens.insert("TIME", Regex::new(r"\b\d+(s|ms|cs|ds)\b").unwrap());
        regex_tokens.insert("COORDINATE", Regex::new(r"-?d+(x|y)\b").unwrap());
        
        // Comments
        regex_tokens.insert("COMMENT", Regex::new(r"//.*").unwrap());

        // Return the HashMap
        regex_tokens
    }
}

fn main() {
}
