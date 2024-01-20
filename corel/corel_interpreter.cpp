#include <algorithm>
#include <windows.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <memory>

#include "ext\json.hpp"
using json = nlohmann::json;

// Node type enum
enum class NodeType {
		WAIT,
		MOVE,
		PRESS,
		CLICK,
		KEY,
		LOOP
};

// Defining base class for all AST nodes
class ASTnode;
class Node {
	public:
		NodeType node_type;
		virtual ~Node() = default; // The ~ symbol is used to define a destructor
		virtual void print(int depth = 0) const = 0; // Pure virtual function
		Node(NodeType node_type) : node_type(node_type) {}
};

// All AST nodes
class WAITnode : public Node {
	public:
		int value;
		std::string magnitude;
		WAITnode(int value, std::string magnitude) : Node(NodeType::WAIT), value(value), magnitude(magnitude) {} 

		void print(int depth = 0) const override {
			std::cout << std::string(depth, ' ') << "WAIT " << value << " " << magnitude << std::endl;
		}
};

class MOVEnode : public Node {
	public:
		int value;
		std::string direction;
		MOVEnode(int value, std::string direction) : Node(NodeType::MOVE), value(value), direction(direction) {}

		void print(int depth = 0) const override {
			std::cout << std::string(depth, ' ') << "MOVE " << value << " " << direction << std::endl;
		}
};

class PRESSnode : public Node {
	public:
		std::string button;
		PRESSnode(std::string button) : Node(NodeType::PRESS), button(button) {}

		void print(int depth = 0) const override {
			std::cout << std::string(depth, ' ') << "PRESS " << button << std::endl;
		}
};

class CLICKnode : public Node {
	public:
		std::string button;
		CLICKnode(std::string button) : Node(NodeType::CLICK), button(button) {}

		void print(int depth = 0) const override {
			std::cout << std::string(depth, ' ') << "CLICK " << button << std::endl;
		}
};

class KEYnode : public Node {
	public:
		std::string key;
		KEYnode(std::string key) : Node(NodeType::KEY), key(key) {}

		void print(int depth = 0) const override {
			std::cout << std::string(depth, ' ') << "KEY " << key << std::endl;
		}
};

// AST class
class ASTnode : public Node {
    public:
        std::unique_ptr<Node> actual_node;
        std::vector<std::unique_ptr<ASTnode>> children;

        ASTnode(std::unique_ptr<Node> actual_node) : Node(actual_node->node_type), actual_node(std::move(actual_node)) {}

        void add_child(std::unique_ptr<ASTnode> child) {
            children.push_back(std::move(child));
        }

        void print(int depth = 0) const override {
            actual_node->print(depth); 
            for (const auto& child : children) {
                child->print(depth + 1);
            }
        }
};

class LOOPnode : public Node {
	public:
		int value;
		std::vector<std::unique_ptr<ASTnode>> children;
		LOOPnode(int value, std::vector<std::unique_ptr<ASTnode>> children) : 
			Node(NodeType::LOOP), value(value), children(std::move(children)) {}

		void print(int depth = 0) const override {
			std::cout << std::string(depth, ' ') << "LOOP " << value << std::endl;

			for (const auto& child : children) {
				child->print(depth + 1);
			}
		}
};

// JSON representation of AST as a string
std::string read_ast_json() {
	std::ifstream file("ast.json");
	std::string str;

	file.seekg(0, std::ios::end);
	str.reserve(file.tellg());
	file.seekg(0, std::ios::beg);

	str.assign(
			(std::istreambuf_iterator<char>(file)), 
			std::istreambuf_iterator<char>()
	);
  return str;
}

// Recursively build AST from JSON object
std::unique_ptr<ASTnode> create_node(const json& node_json) {
    const json& type_json = node_json.contains("node_type") ? node_json["node_type"] : node_json;

    // Check for specific node types within the 'type_json' object
    if (type_json.contains("WAIT") && type_json["WAIT"].is_object()) {
        auto wait_node = type_json["WAIT"];
        return std::make_unique<ASTnode>(std::make_unique<WAITnode>(wait_node["value"], wait_node["magnitude"]));
    }

    if (type_json.contains("MOVE") && type_json["MOVE"].is_object()) {
        auto move_node = type_json["MOVE"];
        return std::make_unique<ASTnode>(std::make_unique<MOVEnode>(move_node["value"], move_node["direction"]));
    }

    if (type_json.contains("PRESS") && type_json["PRESS"].is_object()) {
        auto press_node = type_json["PRESS"];
        return std::make_unique<ASTnode>(std::make_unique<PRESSnode>(press_node["value"]));
    }

    if (type_json.contains("CLICK") && type_json["CLICK"].is_object()) {
        auto click_node = type_json["CLICK"];
        return std::make_unique<ASTnode>(std::make_unique<CLICKnode>(click_node["value"]));
    }

    if (type_json.contains("KEY") && type_json["KEY"].is_object()) {
        auto key_node = type_json["KEY"];
        return std::make_unique<ASTnode>(std::make_unique<KEYnode>(key_node["value"]));
    }

    if (type_json.contains("LOOP") && type_json["LOOP"].is_object()) {
        auto loop_node = type_json["LOOP"];
        if (!loop_node.contains("children") || !loop_node["children"].is_array()) {
            throw std::runtime_error("Invalid or missing 'children' in LOOP node: " + loop_node.dump());
        }

        std::vector<std::unique_ptr<ASTnode>> children;
        for (const auto& child : loop_node["children"]) {
            children.push_back(create_node(child["node_type"])); // Pass the 'node_type' of the child
        }
        return std::make_unique<ASTnode>(std::make_unique<LOOPnode>(loop_node["value"], std::move(children)));
    }

    throw std::runtime_error("Invalid node type: " + type_json.dump());
}

std::unique_ptr<ASTnode> build_ast(const json& j) {
	auto node = create_node(j["node_type"]);

	std::unique_ptr<ASTnode> ast_node = std::make_unique<ASTnode>(std::move(node));
  if (j.contains("children")) {
      for (const auto& child : j["children"]) {
      	ast_node->add_child(build_ast(child));
      }
  }
    return ast_node;
}

// Helper functions
std::string nodetype_to_string(NodeType type) {
    switch (type) {
        case NodeType::WAIT: return "WAIT";
        case NodeType::MOVE: return "MOVE";
        case NodeType::PRESS: return "PRESS";
        case NodeType::CLICK: return "CLICK";
        case NodeType::KEY: return "KEY";
        case NodeType::LOOP: return "LOOP";
        default: return "UNKNOWN";
    }
}


void print_ast(const ASTnode& node, int depth = 0) {
    node.actual_node->print(depth); // Use actual_node here

    for (const auto& child : node.children) {
        print_ast(*child, depth + 1); // Recursively print children
    }
}

// Interpreter class
class Interpreter {
	private:
		std::vector<std::unique_ptr<ASTnode>>& ast_nodes;

	public:
		Interpreter(std::vector<std::unique_ptr<ASTnode>>& ast_nodes) : ast_nodes(ast_nodes) {}

		void run() {
			for (auto& node : ast_nodes) {
				try {
					run_node(node);
				} catch (const std::exception& e) {
					std::cout << "Error: " << e.what() << std::endl;
				}
			}
		}

		void run_node(const std::unique_ptr<ASTnode>& node) {
			// Debug print
			switch (node->actual_node->node_type) {
				case NodeType::WAIT:
					execute_wait(*static_cast<const WAITnode*>(node->actual_node.get()));
					break;
				case NodeType::MOVE:
					execute_move(*static_cast<const MOVEnode*>(node->actual_node.get()));
					break;
				case NodeType::PRESS:
					execute_press(*static_cast<const PRESSnode*>(node->actual_node.get()));
					break;
				case NodeType::CLICK:
					execute_click(*static_cast<const CLICKnode*>(node->actual_node.get()));
					break;
				case NodeType::KEY:
					execute_key(*static_cast<const KEYnode*>(node->actual_node.get()));
					break;
				case NodeType::LOOP:
					execute_loop(*static_cast<const LOOPnode*>(node->actual_node.get()));
					break;
				default:
					throw std::runtime_error("Invalid node type");
			}
		}

		void execute_wait(const WAITnode& node) {
			std::cout << "Executing WAIT node: " << node.value << " " << node.magnitude << std::endl;
		}

		void execute_move(const MOVEnode& node) {
			std::cout << "Executing MOVE node: " << node.value << " " << node.direction << std::endl;
		}

		void execute_press(const PRESSnode& node) {
			std::cout << "Executing PRESS node: " << node.button << std::endl;
		}

		void execute_click(const CLICKnode& node) {
			std::cout << "Executing CLICK node: " << node.button << std::endl;
		}

		void execute_key(const KEYnode& node) {
			std::cout << "Executing KEY node: " << node.key << std::endl;
		}

		void execute_loop(const LOOPnode& node) {
			std::cout << "Executing LOOP node: " << node.value << std::endl;
			for (int i = 0; i < node.value; i++) {
				for (const auto& child : node.children) {
					run_node(child);
				}
			}
		}
};

int main(int argc, char** argv) {
	std::string ast_json = read_ast_json();
	std::cout << ast_json << std::endl;

	// Parse JSON string into JSON object
	auto j = json::parse(ast_json);
	std::cout << j.dump(4) << std::endl;

	// Build AST from JSON object
	std::vector<std::unique_ptr<ASTnode>> ast_nodes;
	for (const auto& node_json : j) {
			auto ast_node = build_ast(node_json);
			ast_nodes.push_back(std::move(ast_node));
	}

	std::cout << "AST: " << std::endl;
	for (const auto& node : ast_nodes) {
			print_ast(*node);
	}

	// Run interpreter
	Interpreter interpreter(ast_nodes);
	interpreter.run();

	return 0; 
}
