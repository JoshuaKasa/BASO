extern crate winapi;
extern crate corel_parser;

use winapi;

pub struct CorelInterpreter {
    pub ast: Vec<corel_parser::NodeType>,
}

impl CorelInterpreter {
    pub fn run(&self) {
        for node in &self.ast {
            match self.execute_node(node) {
                Ok(_) => {},
                Err(e) => {
                    println!("Unexpected error: {}", e);
                }
            } 
        }
    }

    pub fn execute_node(&self, node: &corel_parser::NodeType) -> Result<(), String> {
        
    })
}
