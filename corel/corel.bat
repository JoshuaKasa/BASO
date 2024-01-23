@echo off
SETLOCAL

REM I'm suppressing all the output from the commands because they're not important. The difference between a normal "> NUL" and a ">NUL 2>&1" is that the second one also ignores all the output sent to the STDERR.
REM If you want to see the output, remove the "> NUL" from the end of the commands.

REM Store the current directory
SET current_dir=%CD%

REM Store the script's directory and go to that directory
SET script_dir=%~dp0
cd /d "%script_dir%"

REM Check if an argument is provided
IF "%~1"=="" (
    echo Please provide a file name.
    exit /b 1
)

REM Set variables
SET input_file=%current_dir%\%~1
SET output_file=corel.corel

REM Check if input file exists
IF NOT EXIST "%input_file%" (
    echo The file "%input_file%" does not exist.
    exit /b 1
)

REM Copy the provided file to corel.corel
copy "%input_file%" "%output_file%" > NUL
IF NOT %ERRORLEVEL% == 0 (
    echo Failed to copy file.
    exit /b 1
)

REM Check if cargo is available
cargo --version > NUL
IF NOT %ERRORLEVEL% == 0 (
    echo Cargo is not installed or not in PATH.
    exit /b 1
)

REM Run cargo build and suppress all output
cargo build > NUL 2>&1
IF NOT %ERRORLEVEL% == 0 (
    echo Cargo build failed.
    exit /b 1
)

REM Run cargo run and suppress all output
cargo run
IF NOT %ERRORLEVEL% == 0 (
    echo Cargo run failed.
    exit /b 1
)

REM Check if Python is available
python --version > NUL
IF NOT %ERRORLEVEL% == 0 (
    echo Python is not installed or not in PATH.
    exit /b 1
)

REM Run the Python script with "ast.json" as an argument
python "%script_dir%corel_interpreter.py" "ast.json"
IF NOT %ERRORLEVEL% == 0 (
    echo Failed to run corel_interpreter.py.
    exit /b 1
)

echo Script executed successfully.
exit /b 0
