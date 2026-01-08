@echo off
echo ==============================================
echo SCHOOL MANAGEMENT SYSTEM - INSTALLER CREATION
echo ==============================================
echo.

REM Check if InnoSetup is installed
where iscc >nul 2>&1
if %errorlevel% neq 0 (
    echo InnoSetup is not installed or not in PATH.
    echo Please install InnoSetup from https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

REM Check if executable exists
if not exist "dist\SchoolManagementSystem.exe" (
    echo Executable not found in dist folder.
    echo Please build the executable first using: python build_exe.py
    echo.
    pause
    exit /b 1
)

REM Create installer directory
if not exist "installer" mkdir installer

REM Create license file if it doesn't exist
if not exist "LICENSE.txt" (
    echo Creating license file...
    (
    echo SCHOOL MANAGEMENT SYSTEM
    echo =========================
    echo.
    echo END USER LICENSE AGREEMENT
    echo.
    echo 1. GRANT OF LICENSE
    echo This software is licensed, not sold. Greenwood Primary School grants you a 
    echo non-exclusive license to use this software for educational and administrative 
    echo purposes within your school.
    echo.
    echo 2. RESTRICTIONS
    echo You may not distribute, sell, or modify this software without written 
    echo permission from Greenwood Primary School.
    echo.
    echo 3. TERMINATION
    echo This license is effective until terminated. Your rights under this license 
    echo will terminate automatically without notice if you fail to comply with any 
    echo terms of this license.
    echo.
    echo 4. DISCLAIMER OF WARRANTY
    echo This software is provided "as is" without warranty of any kind.
    echo.
    echo By installing this software, you agree to these terms.
    ) > LICENSE.txt
)

REM Create setup wizard images if they don't exist
if not exist "assets\setup_wizard.bmp" (
    echo Creating setup wizard image...
    REM You can create a proper BMP image here
    echo Placeholder for setup wizard image > "assets\setup_wizard.bmp"
)

if not exist "assets\setup_wizard_small.bmp" (
    echo Creating small setup wizard image...
    echo Placeholder for small setup wizard image > "assets\setup_wizard_small.bmp"
)

REM Run InnoSetup compiler
echo Compiling installer with InnoSetup...
echo.

iscc "school_management_setup.iss"

if %errorlevel% equ 0 (
    echo.
    echo ==============================================
    echo INSTALLER CREATED SUCCESSFULLY!
    echo ==============================================
    echo.
    echo Installer location: installer\SchoolManagementSystem_Setup.exe
    echo.
    echo You can now distribute this installer to users.
) else (
    echo.
    echo ==============================================
    echo INSTALLER CREATION FAILED!
    echo ==============================================
    echo.
    echo Check the InnoSetup compiler output for errors.
)

echo.
pause