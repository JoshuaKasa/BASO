@echo off
REM Get the first argument and store it in a variable
SET input_file=%~1

REM Copy the provided file to corel.corel
copy %input_file% corel.corel

REM Run cargo build and cargo run
cargo build
cargo run

REM Run the Python script
python corel_interpreter.py
