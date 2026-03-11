use serde::{Serialize, Deserialize};
use crate::corel_lexer;
use std::fs;

// AST nodes
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NodeType {
    WAIT(Box<WAITnode>),
    PRESS(Box<PRESSnode>),
    KEY(Box<KEYnode>),
    CLICK(Box<CLICKnode>),
    LOOP(Box<LOOPnode>),
    MOVE(Box<MOVEnode>)
}

// AST nodes struct
#[derive(Debug, Clone, Serialize, Deserialize)]
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

#[derive(Debug, Clone, Serialize, Deserialize)]
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
#[derive(Debug, Clone, Serialize, Deserialize)]
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
#[derive(Debug, Clone, Serialize, Deserialize)]
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
#[derive(Debug, Clone, Serialize, Deserialize)]
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
#[derive(Debug, Clone, Serialize, Deserialize)]
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
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MOVEnode {
    value: i16,
    direction: String
}
impl MOVEnode {
    pub fn new(value: i16, direction: String) -> Self {
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
    fn current_token(&self) -> Option<corel_lexer::Token> {
        self.tokens.get(self.current_position as usize).cloned()
    }

    fn fail_and_advance(&mut self, message: String) {
        eprintln!("{message}");
        self.current_position += 1;
    }

    fn unexpected_eof(&mut self, context: &str) {
        eprintln!("Error: Unexpected end of input while parsing {context}");
        self.current_position = self.tokens.len() as i32;
    }

    pub fn parse_line(&mut self) {
        let Some(token) = self.current_token() else {
            return;
        };
        let token_type = token.r#type.clone();

        // Checking the token and parsing it
        match token_type.as_str() {
            "WAIT" => self.parse_wait(),
            "PRESS" => self.parse_press(),
            "STARTKEY" => self.parse_key(),
            "CLICK" => self.parse_click(),
            "LOOP" => self.parse_loop(),
            "MOVE" => self.parse_move(),
            "COMMENT" => self.current_position += 1, // Skip the COMMENT token
            _ => self.fail_and_advance(format!(
                "Error: Invalid token type: {} at line: {}",
                token_type, token.line_number
            )),
        }
    }

    pub fn parse(&mut self) -> Vec<ASTnode> {
        while self.current_position < self.tokens.len() as i32 {
            let previous_position = self.current_position;
            self.parse_line();

            // Last-resort recovery: never allow the parser to stall in place.
            if self.current_position <= previous_position {
                eprintln!(
                    "Error: Parser stalled at token index {}, forcing recovery",
                    self.current_position
                );
                self.current_position += 1;
            }
        }
        // Before returning the AST, we will pass it to a JSON file
        // so that we can use it in the interpreter
        let ast = self.nodes.clone();
        let ast_json = serde_json::to_string(&ast)
            .expect("Error: Could not convert AST to JSON");
        fs::write("ast.json", ast_json)
            .expect("Error: Could not write AST to file");
        
        ast // Returning the AST (cloned for borrow checker)
    }

    fn parse_wait(&mut self) {
        self.current_position += 1; // Skip the WAIT token
        let Some(token) = self.current_token() else {
            self.unexpected_eof("wait");
            return;
        };

        // Checking for correct syntax (wait(5s, 10ms, 15ds, 20cs))
        if token.r#type != "LPAREN" {
            self.fail_and_advance(format!("Error: Expected LPAREN at line: {}", token.line_number));
            return;
        }
        self.current_position += 1; // Skip the LPAREN token
        let Some(token) = self.current_token() else {
            self.unexpected_eof("wait");
            return;
        };

        if token.r#type != "TIME" {
            self.fail_and_advance(format!("Error: Expected TIME at line: {}", token.line_number));
            return;
        }

        // Split the time into numeric value and unit
        let time_str = &token.value;
        let digits_end = time_str.trim_end_matches(|c: char| !c.is_digit(10)).len();
        let (value_str, unit) = time_str.split_at(digits_end);

        let value = match value_str.parse::<i32>() {
            Ok(value) => value,
            Err(_) => {
                self.fail_and_advance(format!(
                    "Error: Invalid number in TIME at line: {}",
                    token.line_number
                ));
                return;
            }
        };

        self.current_position += 1; // Skip the TIME token

        let Some(token) = self.current_token() else {
            self.unexpected_eof("wait");
            return;
        };
        if token.r#type != "RPAREN" {
            self.fail_and_advance(format!("Error: Expected RPAREN at line: {}", token.line_number));
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
        let Some(token) = self.current_token() else {
            self.unexpected_eof("press");
            return;
        };

        // Checking for correct syntax (press("a"))
        if token.r#type != "LPAREN" {
            self.fail_and_advance(format!("Error: Expected LPAREN at line: {}", token.line_number));
            return;
        }
        self.current_position += 1; // Skip the LPAREN token
        let Some(token) = self.current_token() else {
            self.unexpected_eof("press");
            return;
        };

        if token.r#type != "STRING" {
            self.fail_and_advance(format!("Error: Expected STRING at line: {}", token.line_number));
            return;
        }
        let value = token.value.clone();
        self.current_position += 1; // Skip the STRING token

        let Some(token) = self.current_token() else {
            self.unexpected_eof("press");
            return;
        };
        if token.r#type != "RPAREN" {
            self.fail_and_advance(format!("Error: Expected RPAREN at line: {}", token.line_number));
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
        let Some(token) = self.current_token() else {
            self.unexpected_eof("click");
            return;
        };

        // Checking for correct syntax (click("a"))
        if token.r#type != "LPAREN" {
            self.fail_and_advance(format!("Error: Expected LPAREN at line: {}", token.line_number));
            return;
        }
        self.current_position += 1; // Skip the LPAREN token
        let Some(token) = self.current_token() else {
            self.unexpected_eof("click");
            return;
        };

        if token.r#type != "STRING" {
            self.fail_and_advance(format!("Error: Expected STRING at line: {}", token.line_number));
            return;
        }
        let value = token.value.clone();
        self.current_position += 1; // Skip the STRING token

        let Some(token) = self.current_token() else {
            self.unexpected_eof("click");
            return;
        };
        if token.r#type != "RPAREN" {
            self.fail_and_advance(format!("Error: Expected RPAREN at line: {}", token.line_number));
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
        let Some(token) = self.current_token() else {
            self.unexpected_eof("loop");
            return;
        };

        // Checking for correct syntax (loop(5))
        if token.r#type != "LPAREN" {
            self.fail_and_advance(format!("Error: Expected LPAREN at line: {}", token.line_number));
            return;
        }
        self.current_position += 1; // Skip the LPAREN token
        let Some(token) = self.current_token() else {
            self.unexpected_eof("loop");
            return;
        };

        if token.r#type != "NUMBER" {
            self.fail_and_advance(format!("Error: Expected NUMBER at line: {}", token.line_number));
            return;
        }
        let value = match token.value.parse::<i32>() {
            Ok(value) => value,
            Err(_) => {
                self.fail_and_advance(format!(
                    "Error: Invalid loop count at line: {}",
                    token.line_number
                ));
                return;
            }
        };
        self.current_position += 1; // Skip the NUMBER token

        let Some(token) = self.current_token() else {
            self.unexpected_eof("loop");
            return;
        };
        if token.r#type != "RPAREN" {
            self.fail_and_advance(format!("Error: Expected RPAREN at line: {}", token.line_number));
            return;
        }
        self.current_position += 1; // Skip the RPAREN token

        // Parsing loops's children 
        let Some(token) = self.current_token() else {
            self.unexpected_eof("loop");
            return;
        };
        if token.r#type != "LBRACE" {
            self.fail_and_advance(format!("Error: Expected LBRACE at line: {}", token.line_number));
            return;
        }
        self.current_position += 1; // Skip the LBRACE token

        let mut children: Vec<ASTnode> = Vec::new();
        while self.current_position < self.tokens.len() as i32 {
            let Some(token) = self.current_token() else {
                self.unexpected_eof("loop");
                return;
            };
            if token.r#type == "RBRACE" {
                break;
            }
            let previous_len = self.nodes.len();
            self.parse_line();
            if self.nodes.len() > previous_len {
                if let Some(node) = self.nodes.pop() {
                    children.push(node);
                }
            }
        }

        if self.current_position >= self.tokens.len() as i32 {
            self.unexpected_eof("loop body");
            return;
        }
        self.current_position += 1; // Skip the RBRACE token

        // Creating the AST node
        let loop_node = Box::new(LOOPnode::new(value, children)); 
        let ast_node = ASTnode::new(NodeType::LOOP(loop_node));
        self.nodes.push(ast_node);
    }

    fn parse_move(&mut self) {
        self.current_position += 1; // Skip the MOVE token
        let Some(token) = self.current_token() else {
            self.unexpected_eof("move");
            return;
        };

        // Checking for correct syntax (move(100x) or move(100y))
        if token.r#type != "LPAREN" {
            self.fail_and_advance(format!("Error: Expected LPAREN at line: {}", token.line_number));
            return;
        }
        self.current_position += 1; // Skip the LPAREN token
    
        let Some(token) = self.current_token() else {
            self.unexpected_eof("move");
            return;
        };
        match token.r#type.as_str() {
            "NUMBER" => {
                self.fail_and_advance(format!(
                    "Error: Expected COORDINATE at line: {}",
                    token.line_number
                ));
                return;
            },
            "COORDINATE" => {
                let (value_str, axis) = token.value.split_at(token.value.len() - 1);
                let value = match value_str.parse::<i32>() {
                    Ok(value) => value,
                    Err(_) => {
                        self.fail_and_advance(format!(
                            "Error: Invalid coordinate value at line: {}",
                            token.line_number
                        ));
                        return;
                    }
                };
                self.current_position += 1; // Skip the COORDINATE token

                let Some(token) = self.current_token() else {
                    self.unexpected_eof("move");
                    return;
                };
                if token.r#type != "RPAREN" {
                    self.fail_and_advance(format!(
                        "Error: Expected RPAREN at line: {}",
                        token.line_number
                    ));
                    return;
                }
                self.current_position += 1; // Skip the RPAREN token
                let value_int = value as i16;

                // Creating the AST node
                let move_node = Box::new(MOVEnode::new(value_int, axis.to_string()));
                let ast_node = ASTnode::new(NodeType::MOVE(move_node));
                self.nodes.push(ast_node);
            },
            _ => {
                self.fail_and_advance(format!(
                    "Error: Invalid token type: {} at line: {}",
                    token.r#type, token.line_number
                ));
            }
        }    
    }

    fn parse_key(&mut self) {
        let Some(token) = self.current_token() else {
            self.unexpected_eof("start key");
            return;
        };

        // Adding the KEY node to the AST
        let key_node = Box::new(KEYnode::new(token.value.clone()));
        let ast_node = ASTnode::new(NodeType::KEY(key_node));
        self.nodes.push(ast_node);

        self.current_position += 1; // Skip the KEY token
    }
}
