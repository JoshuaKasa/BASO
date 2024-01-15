extern crate regex;
use regex::Regex;

use crate::corel_lexer;

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
    pub fn parse_line(&mut self) {
        // We gotta clone because of borrow checker 
        let token = self.tokens[self.current_position as usize].clone();
        let token_type = token.r#type.clone();

        // Checking the token and parsing it
        match token_type.as_str() {
            "WAIT" => self.parse_wait(),
            "PRESS" => self.parse_press(),
            "KEY" => self.parse_key(),
            "CLICK" => self.parse_click(),
            "LOOP" => self.parse_loop(),
            "MOVE" => self.parse_move(),
            _ => println!("Error: Invalid token type: {} at line: {}", token_type, token.line_number),
        }
    }

    pub fn parse(&mut self) {
        while self.current_position < self.tokens.len() as i32 {
            self.parse_line();
            self.current_position += 1;
        }
    }

    fn parse_wait(&mut self) {
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
        let value = token.value.parse::<i32>().unwrap();
        self.current_position += 1; // Skip the TIME token

        let token = self.tokens[self.current_position as usize].clone();
        if token.r#type != "RPAREN" {
            println!("Error: Expected RPAREN at line: {}", token.line_number);
            return;
        }
        self.current_position += 1; // Skip the RPAREN token

        // Creating the AST node
        let mut node = ASTnode::new(NodeType::WAIT);
        let wait_node = WAITnode::new(value, token.value);
        node.children.push(ASTnode::new(NodeType::WAIT));
        self.nodes.push(node);
    }

    fn parse_press(&mut self) {
        self.current_position += 1; // Skip the PRESS token
        let token = self.tokens[self.current_position as usize].clone();

        // Checking for correct syntax (press("a"))
        if token.r#type != "LPAREN" {
            println!("Error: Expected LPAREN at line: {}", token.line_number);
            return;
        }
        self.current_position += 1; // Skip the LPAREN token
        let token = self.tokens[self.current_position as usize].clone();

        if token.r#type != "STRING" {
            println!("Error: Expected STRING at line: {}", token.line_number);
            return;
        }
        let value = token.value.clone();
        self.current_position += 1; // Skip the STRING token

        let token = self.tokens[self.current_position as usize].clone();
        if token.r#type != "RPAREN" {
            println!("Error: Expected RPAREN at line: {}", token.line_number);
            return;
        }
        self.current_position += 1; // Skip the RPAREN token

        // Creating the AST node
        let mut node = ASTnode::new(NodeType::PRESS);
        let press_node = PRESSnode::new(value);
        node.children.push(ASTnode::new(NodeType::PRESS));
        self.nodes.push(node);
    }

    fn parse_click(&mut self) {
        self.current_position += 1; // Skip the CLICK token
        let token = self.tokens[self.current_position as usize].clone();

        // Checking for correct syntax (click("a"))
        if token.r#type != "LPAREN" {
            println!("Error: Expected LPAREN at line: {}", token.line_number);
            return;
        }
        self.current_position += 1; // Skip the LPAREN token
        let token = self.tokens[self.current_position as usize].clone();

        if token.r#type != "STRING" {
            println!("Error: Expected STRING at line: {}", token.line_number);
            return;
        }
        let value = token.value.clone();
        self.current_position += 1; // Skip the STRING token

        let token = self.tokens[self.current_position as usize].clone();
        if token.r#type != "RPAREN" {
            println!("Error: Expected RPAREN at line: {}", token.line_number);
            return;
        }
        self.current_position += 1; // Skip the RPAREN token

        // Creating the AST node
        let mut node = ASTnode::new(NodeType::CLICK);
        let click_node = CLICKnode::new(value);
        node.children.push(ASTnode::new(NodeType::CLICK));
        self.nodes.push(node);
    }

    fn parse_loop(&mut self) {
        self.current_position += 1; // Skip the LOOP token
        let token = self.tokens[self.current_position as usize].clone();

        // Checking for correct syntax (loop(5))
        if token.r#type != "LPAREN" {
            println!("Error: Expected LPAREN at line: {}", token.line_number);
            return;
        }
        self.current_position += 1; // Skip the LPAREN token
        let token = self.tokens[self.current_position as usize].clone();

        if token.r#type != "NUMBER" {
            println!("Error: Expected NUMBER at line: {}", token.line_number);
            return;
        }
        let value = token.value.parse::<i32>().unwrap();
        self.current_position += 1; // Skip the NUMBER token

        let token = self.tokens[self.current_position as usize].clone();
        if token.r#type != "RPAREN" {
            println!("Error: Expected RPAREN at line: {}", token.line_number);
            return;
        }
        self.current_position += 1; // Skip the RPAREN token

        // Parsing loops's children 
        let token = self.tokens[self.current_position as usize].clone();
        if token.r#type != "LBRACE" {
            println!("Error: Expected LBRACE at line: {}", token.line_number);
            return;
        }
        self.current_position += 1; // Skip the LBRACE token

        let mut children: Vec<ASTnode> = Vec::new();
        while self.current_position < self.tokens.len() as i32 {
            let token = self.tokens[self.current_position as usize].clone();
            if token.r#type == "RBRACE" {
                break;
            }
            self.parse_line();
            self.current_position += 1;
        }

        // Creating the AST node
        let mut node = ASTnode::new(NodeType::LOOP);
        let loop_node = LOOPnode::new(value);
        node.children.push(ASTnode::new(NodeType::LOOP));
        self.nodes.push(node);
    }

    fn parse_move(&mut self) {
        self.current_position += 1; // Skip the MOVE token
        let token = self.tokens[self.current_position as usize].clone();

        // Checking for correct syntax (move(100x) or move(100y))
        if token.r#type != "LPAREN" {
            println!("Error: Expected LPAREN at line: {}", token.line_number);
            return;
        }
        self.current_position += 1; // Skip the LPAREN token
    
        let token = self.tokens[self.current_position as usize].clone();
        match token.r#type.as_str() {
            "NUMBER" => {
                println!("Error: Expected COORDINATE at line: {}", token.line_number);
                return;
            },
            "COORDINATES" => {
                let value = token.value.parse::<i32>().unwrap();
                self.current_position += 1; // Skip the COORDINATE token

                let token = self.tokens[self.current_position as usize].clone();
                if token.r#type != "RPAREN" {
                    println!("Error: Expected RPAREN at line: {}", token.line_number);
                    return;
                }
                self.current_position += 1; // Skip the RPAREN token
                let value_string = value.to_string();

                // Creating the AST node
                let mut node = ASTnode::new(NodeType::MOVE);
                let move_node = MOVEnode::new(value_string, token.value);
                node.children.push(ASTnode::new(NodeType::MOVE));
                self.nodes.push(node);
            },
            _ => {
                println!("Error: Invalid token type: {} at line: {}", token.r#type, token.line_number);
            }
        }    
    }

    fn parse_key(&mut self) {
        let token = self.tokens[self.current_position as usize].clone();
        let mut node = ASTnode::new(NodeType::KEY);    
        let key_node = KEYnode::new(token.value);
        node.children.push(ASTnode::new(NodeType::KEY));
        self.nodes.push(node);
    }
}
