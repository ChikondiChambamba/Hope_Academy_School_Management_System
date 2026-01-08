#!/usr/bin/env python3
"""
Build script for School Management System executable
"""
import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
import argparse

class BuildSystem:
    """Build system for creating executable"""
    
    def __init__(self, project_root=None):
        if project_root is None:
            self.project_root = Path(__file__).parent
        else:
            self.project_root = Path(project_root)
        
        self.build_dir = self.project_root / 'build'
        self.dist_dir = self.project_root / 'dist'
        self.spec_file = self.project_root / 'school_management.spec'
        
        # Ensure directories exist
        self.build_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
    
    def clean_build(self):
        """Clean build directories"""
        print("Cleaning build directories...")
        
        # Remove build and dist directories
        for dir_path in [self.build_dir, self.dist_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"  Removed: {dir_path}")
        
        # Remove __pycache__ directories
        for pycache_dir in self.project_root.rglob('__pycache__'):
            shutil.rmtree(pycache_dir)
            print(f"  Removed: {pycache_dir}")
        
        print("Clean complete.")
    
    def check_dependencies(self):
        """Check if all dependencies are installed"""
        print("Checking dependencies...")
        
        required_packages = [
            'mysql-connector-python',
            'pandas',
            'reportlab',
            'Pillow',
            'pyinstaller'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"  ✓ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"  ✗ {package} (missing)")
        
        if missing_packages:
            print(f"\nMissing packages: {', '.join(missing_packages)}")
            print("Install with: pip install " + " ".join(missing_packages))
            return False
        
        print("All dependencies are installed.")
        return True
    
    def create_assets(self):
        """Create necessary assets for the build"""
        print("Creating assets...")
        
        assets_dir = self.project_root / 'assets'
        icons_dir = assets_dir / 'icons'
        
        # Create icons directory if it doesn't exist
        icons_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a default icon if it doesn't exist
        icon_path = icons_dir / 'app_icon.ico'
        if not icon_path.exists():
            print("  Creating default icon...")
            self.create_default_icon(icon_path)
        
        # Create version file for Windows
        version_file = self.project_root / 'version.txt'
        if not version_file.exists():
            self.create_version_file(version_file)
        
        print("Assets created.")
    
    def create_default_icon(self, icon_path):
        """Create a default application icon"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import numpy as np
            
            # Create a 256x256 image
            size = (256, 256)
            image = Image.new('RGBA', size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(image)
            
            # Draw school-themed icon
            # Background circle
            draw.ellipse([10, 10, 246, 246], fill=(66, 133, 244, 255))
            
            # Draw book
            draw.rectangle([80, 100, 176, 180], fill=(255, 255, 255, 255))
            draw.rectangle([80, 100, 176, 180], outline=(0, 0, 0, 255), width=3)
            
            # Draw lines for pages
            for i in range(5):
                y = 110 + i * 15
                draw.line([85, y, 171, y], fill=(0, 0, 0, 255), width=2)
            
            # Draw pencil
            draw.polygon([120, 70, 136, 70, 146, 80, 110, 80], fill=(255, 200, 0, 255))
            draw.rectangle([118, 80, 138, 160], fill=(139, 69, 19, 255))
            draw.rectangle([125, 150, 131, 170], fill=(192, 192, 192, 255))
            
            # Save as ICO with multiple sizes
            image.save(icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
            
            print(f"  Created default icon: {icon_path}")
            
        except ImportError:
            # Create a simple text file as placeholder
            with open(icon_path, 'wb') as f:
                f.write(b'Icon placeholder')
            print(f"  Created placeholder icon (install Pillow for proper icon)")
    
    def create_version_file(self, version_file):
        """Create version information file for Windows"""
        version_content = """# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always set with 4-digit tuple
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x40004,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [StringStruct(u'CompanyName', u'Greenwood Primary School'),
           StringStruct(u'FileDescription', u'School Management Information System'),
           StringStruct(u'FileVersion', u'1.0.0.0'),
           StringStruct(u'InternalName', u'SchoolManagementSystem'),
           StringStruct(u'LegalCopyright', u'Copyright © 2024 Greenwood Primary School. All rights reserved.'),
           StringStruct(u'OriginalFilename', u'SchoolManagementSystem.exe'),
           StringStruct(u'ProductName', u'Primary School Management System'),
           StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [0x409, 0x4B0])])
  ]
)
"""
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(version_content)
        print(f"  Created version file: {version_file}")
    
    def run_pyinstaller(self, onefile=True, windowed=True, debug=False):
        """Run PyInstaller to create executable"""
        print("Running PyInstaller...")
        
        # Build command
        cmd = ['pyinstaller']
        
        if onefile:
            cmd.append('--onefile')
        
        if windowed and not debug:
            cmd.append('--windowed')
        else:
            cmd.append('--console')  # Show console for debugging
        
        if debug:
            cmd.append('--debug')
        
        # Add icon if exists
        icon_path = self.project_root / 'assets' / 'icons' / 'app_icon.ico'
        if icon_path.exists():
            cmd.extend(['--icon', str(icon_path)])
        
        # Add version file if exists
        version_file = self.project_root / 'version.txt'
        if version_file.exists():
            cmd.extend(['--version-file', str(version_file)])
        
        # Use spec file
        if self.spec_file.exists():
            cmd.append(str(self.spec_file))
        else:
            # Build without spec file
            cmd.append('--name=SchoolManagementSystem')
            cmd.append('--add-data=assets;assets')
            cmd.append('--add-data=database;database')
            cmd.append('--add-data=reports;reports')
            cmd.append('main.py')
        
        # Add hidden imports
        hidden_imports = [
            'mysql.connector',
            'mysql.connector.locales.eng.client_error',
            'reportlab.graphics.barcode',
            'reportlab.graphics.samples',
            'reportlab.graphics.charts',
            'reportlab.graphics.widgets',
            'reportlab.pdfbase',
            'reportlab.pdfgen',
            'pandas._libs',
            'pandas.io',
            'PIL.Image',
            'PIL.ImageFile',
            'PIL.ImageOps',
        ]
        
        for imp in hidden_imports:
            cmd.extend(['--hidden-import', imp])
        
        # Run PyInstaller
        print(f"Running command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("PyInstaller output:")
            print(result.stdout)
            
            if result.stderr:
                print("PyInstaller errors:")
                print(result.stderr)
            
            # Check if executable was created
            exe_path = self.dist_dir / 'SchoolManagementSystem.exe'
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"\n✓ Executable created successfully!")
                print(f"  Location: {exe_path}")
                print(f"  Size: {size_mb:.2f} MB")
                
                # Create standalone package
                self.create_standalone_package()
                
                return True
            else:
                print("\n✗ Executable not created!")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"\n✗ PyInstaller failed with error: {e}")
            print(f"Output: {e.stdout}")
            print(f"Errors: {e.stderr}")
            return False
    
    def create_standalone_package(self):
        """Create a standalone package with all required files"""
        print("\nCreating standalone package...")
        
        package_dir = self.project_root / 'package'
        package_dir.mkdir(exist_ok=True)
        
        # Copy executable
        exe_source = self.dist_dir / 'SchoolManagementSystem.exe'
        exe_dest = package_dir / 'SchoolManagementSystem.exe'
        
        if exe_source.exists():
            shutil.copy2(exe_source, exe_dest)
            print(f"  Copied executable")
        
        # Copy database files
        db_source = self.project_root / 'database'
        db_dest = package_dir / 'database'
        
        if db_source.exists():
            if db_dest.exists():
                shutil.rmtree(db_dest)
            shutil.copytree(db_source, db_dest)
            print(f"  Copied database files")
        
        # Copy setup script
        setup_source = self.project_root / 'setup_database.py'
        setup_dest = package_dir / 'setup_database.py'
        
        if setup_source.exists():
            shutil.copy2(setup_source, setup_dest)
            print(f"  Copied setup script")
        
        # Copy README
        readme_source = self.project_root / 'README.md'
        readme_dest = package_dir / 'README.txt'
        
        if readme_source.exists():
            shutil.copy2(readme_source, readme_dest)
            print(f"  Copied README")
        
        # Copy requirements
        req_source = self.project_root / 'requirements.txt'
        req_dest = package_dir / 'requirements.txt'
        
        if req_source.exists():
            shutil.copy2(req_source, req_dest)
            print(f"  Copied requirements")
        
        # Create installation guide
        self.create_installation_guide(package_dir)
        
        # Create batch script for setup
        self.create_setup_script(package_dir)
        
        print(f"✓ Standalone package created in: {package_dir}")
    
    def create_installation_guide(self, package_dir):
        """Create installation guide text file"""
        guide_content = """==============================================
SCHOOL MANAGEMENT SYSTEM - INSTALLATION GUIDE
==============================================

System Requirements:
- Windows 7 or later
- MySQL Server 5.7 or later
- 4GB RAM minimum
- 500MB free disk space

Installation Steps:

1. INSTALL MYSQL SERVER
   --------------------
   If you don't have MySQL installed:
   - Download MySQL Installer from https://dev.mysql.com/downloads/installer/
   - Run the installer and choose "Developer Default" or "Server only"
   - During installation, set a root password and remember it
   - Complete the installation

2. SET UP DATABASE
   ---------------
   - Run setup_database.bat (Windows) or setup_database.py (Python)
   - Enter your MySQL root password when prompted
   - The script will create the database and tables

3. RUN THE APPLICATION
   -------------------
   - Double-click SchoolManagementSystem.exe
   - If prompted by Windows Defender, click "More info" then "Run anyway"
   - Configure database connection if needed

4. INITIAL SETUP
   -------------
   - When you run the application for the first time:
     * Go to Finance tab to set up fee types
     * Go to Students tab to add students
     * Go to Teachers tab to add teachers

Troubleshooting:

1. If the application won't start:
   - Install Microsoft Visual C++ Redistributable:
     https://aka.ms/vs/16/release/vc_redist.x64.exe

2. Database connection errors:
   - Check if MySQL service is running (services.msc)
   - Verify MySQL credentials in the application

3. Application crashes:
   - Check error.log in the application folder
   - Ensure all dependencies are installed

Support:
- Contact: school@greenwood.edu
- Documentation: See README.txt

==============================================
"""
        
        guide_path = package_dir / 'INSTALLATION_GUIDE.txt'
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)
    
    def create_setup_script(self, package_dir):
        """Create setup batch script for Windows"""
        batch_content = """@echo off
echo ==============================================
echo SCHOOL MANAGEMENT SYSTEM - DATABASE SETUP
echo ==============================================
echo.
echo This script will set up the database for the School Management System.
echo.
echo Requirements:
echo - MySQL Server must be installed and running
echo - You need MySQL root password
echo.
pause

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Run database setup
echo Setting up database...
python setup_database.py

if %errorlevel% equ 0 (
    echo.
    echo ==============================================
    echo DATABASE SETUP COMPLETED SUCCESSFULLY!
    echo ==============================================
    echo.
    echo You can now run SchoolManagementSystem.exe
) else (
    echo.
    echo ==============================================
    echo DATABASE SETUP FAILED!
    echo ==============================================
    echo.
    echo Please check:
    echo 1. MySQL service is running
    echo 2. MySQL root password is correct
)

pause
"""
        
        batch_path = package_dir / 'setup_database.bat'
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
    
    def optimize_executable(self):
        """Optimize the executable size"""
        print("\nOptimizing executable...")
        
        exe_path = self.dist_dir / 'SchoolManagementSystem.exe'
        if not exe_path.exists():
            print("  Executable not found, skipping optimization")
            return
        
        # Check if UPX is installed
        try:
            subprocess.run(['upx', '--version'], capture_output=True, check=True)
            
            # Use UPX to compress the executable
            print("  Compressing with UPX...")
            result = subprocess.run(
                ['upx', '--best', '--lzma', str(exe_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"  ✓ Executable compressed to {size_mb:.2f} MB")
            else:
                print(f"  ✗ UPX compression failed: {result.stderr}")
                
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  ℹ UPX not installed, skipping compression")
            print("  Install UPX from: https://upx.github.io")
    
    def build(self, clean=False, optimize=True, debug=False):
        """Main build function"""
        print("=" * 60)
        print("  SCHOOL MANAGEMENT SYSTEM - BUILD PROCESS")
        print("=" * 60)
        
        # Clean if requested
        if clean:
            self.clean_build()
        
        # Check dependencies
        if not self.check_dependencies():
            print("\nPlease install missing dependencies and try again.")
            return False
        
        # Create assets
        self.create_assets()
        
        # Run PyInstaller
        success = self.run_pyinstaller(onefile=True, windowed=True, debug=debug)
        
        if success and optimize:
            self.optimize_executable()
        
        print("\n" + "=" * 60)
        if success:
            print("  BUILD COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Test the executable in the 'dist' folder")
            print("2. Run InnoSetup to create installer")
            print("3. Distribute the installer to users")
        else:
            print("  BUILD FAILED!")
            print("=" * 60)
        
        return success


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Build School Management System executable')
    parser.add_argument('--clean', action='store_true', help='Clean build directories before building')
    parser.add_argument('--no-optimize', action='store_true', help='Skip UPX optimization')
    parser.add_argument('--debug', action='store_true', help='Build with debug console')
    parser.add_argument('--project-dir', type=str, help='Project directory path')
    
    args = parser.parse_args()
    
    # Create build system
    build_system = BuildSystem(args.project_dir)
    
    # Run build
    success = build_system.build(
        clean=args.clean,
        optimize=not args.no_optimize,
        debug=args.debug
    )
    
    if success:
        print("\nTo create installer:")
        print("1. Install InnoSetup from https://jrsoftware.org/isdl.php")
        print("2. Open school_management_setup.iss in InnoSetup")
        print("3. Click 'Compile' to create installer")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()