# Check if the script is running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
{
    # Relaunch the script with administrator privileges
    $arguments = "& '" + $myinvocation.mycommand.definition + "'"
    Start-Process powershell -Verb runAs -ArgumentList $arguments
    Exit
}

# General output text
Write-Output "Welcome to the Corel installer script!"

# Get the directory of the CorelInstaller.ps1 script
$installerScriptPath = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition

# Go up one directory from the script's location
$parentDirectory = Split-Path -Parent -Path $installerScriptPath

# Append the \corel path to this parent directory
$corelDirectory = Join-Path -Path $parentDirectory -ChildPath "corel"

# Get the current system PATH
$systemPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::Machine)

# Check if the corel directory is already in the PATH
Write-Output "Installation started..."
if (-not $systemPath.Contains($corelDirectory)) {
    # Append the new corel directory to the system PATH
    $newPath = $systemPath + ";" + $corelDirectory
    [Environment]::SetEnvironmentVariable("Path", $newPath, [EnvironmentVariableTarget]::Machine)
    Write-Output "Corel installation complete: $corelDirectory"
} 
else {
    Write-Output "Corel is already installed: $corelDirectory"
}

# Function to check if a program is installed
function IsProgramInstalled($programName) {
    $installed = $false
    $installedVersion = $null

    try {
        $installedVersion = (Get-Command $programName -ErrorAction SilentlyContinue).VersionInfo.FileVersion
        $installed = $true
    } catch {
        $installed = $false
    }

    return $installed, $installedVersion
}

# Check if Rust is already installed
$rustInstalled, $rustVersion = IsProgramInstalled "rustc"
if ($rustInstalled) {
    Write-Output "Rust is already installed (Version: $rustVersion)"
} else {
    # Install Rust
    Write-Output "Installing Rust..."
    Invoke-Expression "& { iex (iwr https://sh.rustup.rs -UseBasicParsing).Content }"
}

# Check if Python is already installed
$pythonInstalled, $pythonVersion = IsProgramInstalled "python"
if ($pythonInstalled) {
    Write-Output "Python is already installed (Version: $pythonVersion)"
} else {
    Write-Output "Installing Python..."
    Invoke-Expression "& { iex (iwr https://www.python.org/ftp/python/3.x.x/python-3.x.x-amd64.exe -UseBasicParsing).Content }"
}

Read-Host -Prompt "Press Enter to exit setup..." # Wait for user input before closing the window
