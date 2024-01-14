extern crate regex;
use regex::Regex;

mod corel_lexer;

// AST nodes
#[derive(Debug)]
pub enum NodeType {
    AST,
    WAIT,
    PRESS,
    CLICK,
    LOOP,
    KEY,
    MOVE
}

// AST nodes struct
#[derive(Debug)]
pub struct ASTnode {
    node_type: NodeType,
    children: Vec<ASTnode>
}
impl ASTnode {
    pub fn new(node_type: NodeType) -> Self {
        Self {
            node_type: node_type,
            children: Vec::new()
        }
    }
}

pub struct WAITnode {
    node_type: NodeType,
    value: i32,
    magnitude: String
}
impl WAITnode {
    pub fn new(value: i32, magnitude: String) -> Self {
        Self {
            node_type: NodeType::WAIT,
            value: value,
            magnitude: magnitude
        }
    }
}

pub struct PRESSnode {
    node_type: NodeType,
    value: String
}
impl PRESSnode {
    pub fn new(value: String) -> Self {
        Self {
            node_type: NodeType::PRESS,
            value: value
        }
    }
}

pub struct KEYnode {
    node_type: NodeType,
    value: String
}
impl KEYnode {
    pub fn new(value: String) -> Self {
        Self {
            node_type: NodeType::KEY,
            value: value
        }
    }
}

pub struct CLICKnode {
    node_type: NodeType,
    value: String
}
impl CLICKnode {
    pub fn new(value: String) -> Self {
        Self {
            node_type: NodeType::CLICK,
            value: value
        }
    }
}

pub struct LOOPnode {
    node_type: NodeType,
    value: i32,
    children: Vec<ASTnode>
}
impl LOOPnode {
    pub fn new(value: i32) -> Self {
        Self {
            node_type: NodeType::LOOP,
            value: value,
            children: Vec::new()
        }
    }
}

pub struct MOVEnode {
    node_type: NodeType,
    value: String,
    direction: String
}
impl MOVEnode {
    pub fn new(value: String, direction: String) -> Self {
        Self {
            node_type: NodeType::MOVE,
            value: value,
            direction: direction
        }
    }
}

// Parser
pub struct CorelParser {
    pub tokens: Vec<corel_lexer::Token>,
    pub current_position: i32, 
    pub nodes: Vec<ASTnode>,
}
impl Default for CorelParser {
    fn default() -> Self {
        Self {
            tokens: Vec::new(),
            current_position: 0,
            nodes: Vec::new()
        }
    }
}
impl CorelParser {
    pub fn parse_line(&self) {
        // We gotta clone because of borrow checker 
        let token = self.tokens[self.current_position as usize].clone();
        let token_type = token.r#type.clone();

        // Checking the token and parsing it
        math token_type {
            "WAIT" => {
                self.parse_wait();
            },
            "PRESS" => {
                self.parse_press();
            },
            "KEY" => {
                self.parse_key();
            },
            "CLICK" => {
                self.parse_click();
            },
            "LOOP" => {
                self.parse_loop();
            },
            "MOVE" => {
                self.parse_move();
            },
            _ => {
                println!("Error: Invalid token type: {} at line: {}", token_type, token.line_number);
            }
        }
    }

    fn parse(&self) {
        while self.current_position < self.tokens.len() as i32 {
            self.parse_line();
            self.current_position += 1;
        }
    }

    fn parse_wait(&self) {
        self.current_position += 1; // Skip the WAIT token
        let token = self.tokens[self.current_position as usize].clone();

        // Checking for correct syntax (wait(5s))
        if token.r#type != "LPAREN" {
            println!("Error: Expected LPAREN at line: {}", token.line_number);
            return;
        }
        self.current_position += 1; // Skip the LPAREN token
        let token = self.tokens[self.current_position as usize].clone();

        if token.r#type != "TIME" {
            println!("Error: Expected TIME at line: {}", token.line_number);
            return;
        }
        // TODO: Finish everything (parse_wait too)
    }
}
