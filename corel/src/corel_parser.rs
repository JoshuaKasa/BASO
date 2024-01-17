// TODO: Fix the LOOP node.
// Current problem is: The parser is detecting the LOOP node correctly but then not correctly
// parsing it's body, I have no idea how to parse each line of the body of the loop.

extern crate regex;
use regex::Regex;

use crate::corel_lexer;

// AST nodes
#[derive(Debug, Clone)]
pub enum NodeType {
    WAIT(Box<WAITnode>),
    PRESS(Box<PRESSnode>),
    KEY(Box<KEYnode>),
    CLICK(Box<CLICKnode>),
    LOOP(Box<LOOPnode>),
    MOVE(Box<MOVEnode>)
}

// AST nodes struct
#[derive(Debug, Clone)]
pub struct ASTnode {
    node_type: NodeType,
    children: Vec<ASTnode>
}
impl ASTnode {
    pub fn new(node_type: NodeType) -> Self {
        Self {
            node_type,
            children: Vec::new()
        }
    }

    pub fn add_child(&mut self, child: ASTnode) {
        self.children.push(child);
    }
}

#[derive(Debug, Clone)]
pub struct WAITnode {
    value: i32,
    magnitude: String
}
impl WAITnode {
    pub fn new(value: i32, magnitude: String) -> Self {
        Self {
            value: value,
            magnitude: magnitude
        }
    }
}
#[derive(Debug, Clone)]
pub struct PRESSnode {
    value: String
}
impl PRESSnode {
    pub fn new(value: String) -> Self {
        Self {
            value: value
        }
    }
}
#[derive(Debug, Clone)]
pub struct KEYnode {
    value: String
}
impl KEYnode {
    pub fn new(value: String) -> Self {
        Self {
            value: value
        }
    }
}
#[derive(Debug, Clone)]
pub struct CLICKnode {
    value: String
}
impl CLICKnode {
    pub fn new(value: String) -> Self {
        Self {
            value: value
        }
    }
}
#[derive(Debug, Clone)]
pub struct LOOPnode {
    value: i32,
    children: Vec<ASTnode>
}
impl LOOPnode {
    pub fn new(value: i32, children: Vec<ASTnode>) -> Self {
        Self {
            value: value,
            children: children
        }
    }
}
#[derive(Debug, Clone)]
pub struct MOVEnode {
    value: String,
    direction: String
}
impl MOVEnode {
    pub fn new(value: String, direction: String) -> Self {
        Self {
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
            "STARTKEY" => self.parse_key(),
            "CLICK" => self.parse_click(),
            "LOOP" => self.parse_loop(),
            "MOVE" => self.parse_move(),
            "COMMENT" => return,
            _ => println!("Error: Invalid token type: {} at line: {}", token_type, token.line_number),
        }
    }

    pub fn parse(&mut self) -> Vec<ASTnode> {
        while self.current_position < self.tokens.len() as i32 {
            self.parse_line();
            self.current_position += 1;
        }
        self.nodes.clone() // Returning the AST (cloned for borrow checker)
    }

    fn parse_wait(&mut self) {
        self.current_position += 1; // Skip the WAIT token
        let token = self.tokens[self.current_position as usize].clone();

        // Checking for correct syntax (wait(5s, 10ms, 15ds, 20cs))
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

        // Split the time into numeric value and unit
        let time_str = &token.value;
        let digits_end = time_str.trim_end_matches(|c: char| !c.is_digit(10)).len();
        let (value_str, unit) = time_str.split_at(digits_end);

        let value = match value_str.parse::<i32>() {
            Ok(value) => value,
            Err(_) => {
                println!("Error: Invalid number in TIME at line: {}", token.line_number);
                return;
            }
        };

        self.current_position += 1; // Skip the TIME token

        let token = self.tokens[self.current_position as usize].clone();
        if token.r#type != "RPAREN" {
            println!("Error: Expected RPAREN at line: {}", token.line_number);
            return;
        }
        self.current_position += 1; // Skip the RPAREN token

        // Creating the AST node
        let wait_node = Box::new(WAITnode::new(value, unit.to_string()));
        let ast_node = ASTnode::new(NodeType::WAIT(wait_node));
        self.nodes.push(ast_node); 
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
        let press_node = Box::new(PRESSnode::new(value));
        let ast_node = ASTnode::new(NodeType::PRESS(press_node));
        self.nodes.push(ast_node);
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
        let click_node = Box::new(CLICKnode::new(value));
        let ast_node = ASTnode::new(NodeType::CLICK(click_node));
        self.nodes.push(ast_node);
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
            children.push(self.nodes.pop().unwrap());
        }
        self.current_position += 1;

        // Creating the AST node
        let loop_node = Box::new(LOOPnode::new(value, children)); 
        let ast_node = ASTnode::new(NodeType::LOOP(loop_node));
        self.nodes.push(ast_node);
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
            "COORDINATE" => {
                let (value_str, axis) = token.value.split_at(token.value.len() - 1);
                let value = match value_str.parse::<i32>() {
                    Ok(value) => value,
                    Err(_) => {
                        println!("Error: Invalid coordinate value at line: {}", token.line_number);
                        return;
                    }
                };
                self.current_position += 1; // Skip the COORDINATE token

                let token = self.tokens[self.current_position as usize].clone();
                if token.r#type != "RPAREN" {
                    println!("Error: Expected RPAREN at line: {}", token.line_number);
                    return;
                }
                self.current_position += 1; // Skip the RPAREN token
                let value_string = value.to_string();

                // Creating the AST node
                let move_node = Box::new(MOVEnode::new(value_string, axis.to_string()));
                let ast_node = ASTnode::new(NodeType::MOVE(move_node));
                self.nodes.push(ast_node);
            },
            _ => {
                println!("Error: Invalid token type: {} at line: {}", token.r#type, token.line_number);
            }
        }    
    }

    fn parse_key(&mut self) {
        let token = self.tokens[self.current_position as usize].clone();

        // Adding the KEY node to the AST
        let key_node = Box::new(KEYnode::new(token.value.clone()));
        let ast_node = ASTnode::new(NodeType::KEY(key_node));
        self.nodes.push(ast_node);
    }
}
