use std::fs;
use std::io::Result;
use std::collections::HashMap;

mod corel_lexer;

fn main() {
    let source_code_path = "corel.corel";
    let source_code = fs::read_to_string(source_code_path)
        .expect("Something went wrong reading the file");
    println!("Source code:\n{}", source_code);
    
    // Creating the lexer
    let lexer = corel_lexer::CorelLexer {
        source_code: source_code,
        ..Default::default()
    };

    // Tokenizing the source code
    let tokens = lexer.tokenize();
    println!("Tokens: {:?}", tokens);
}
