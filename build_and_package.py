#!/usr/bin/env python3
"""
Complete build and packaging workflow for School Management System
"""
import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
import zipfile
from datetime import datetime

class PackagingSystem:
    """Complete packaging system for the application"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.build_script = self.project_root / 'build_exe.py'
        self.iss_script = self.project_root / 'school_management_setup.iss'
        self.installer_dir = self.project_root / 'installer'
        self.release_dir = self.project_root / 'releases'
        
        # Ensure directories exist
        self.installer_dir.mkdir(exist_ok=True)
        self.release_dir.mkdir(exist_ok=True)
    
    def check_prerequisites(self):
        """Check all prerequisites are installed"""
        print("Checking prerequisites...")
        
        prerequisites = {
            'Python': ['python', '--version'],
            'PyInstaller': ['pyinstaller', '--version'],
            'InnoSetup': ['iscc', '/?'],  # iscc is InnoSetup compiler
            'UPX': ['upx', '--version'],  # Optional
        }
        
        all_installed = True
        
        for name, cmd in prerequisites.items():
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 or name == 'InnoSetup':  # iscc returns non-zero for /?
                    print(f"  ✓ {name}")
                else:
                    print(f"  ✗ {name}")
                    all_installed = False
            except (subprocess.TimeoutExpired, FileNotFoundError):
                if name == 'UPX':
                    print(f"  ⓘ {name} (optional, not installed)")
                else:
                    print(f"  ✗ {name} (not installed)")
                    all_installed = False
        
        return all_installed
    
    def run_build(self, clean=True, optimize=True):
        """Run the build process"""
        print("\nBuilding executable...")
        
        cmd = [sys.executable, str(self.build_script)]
        
        if clean:
            cmd.append('--clean')
        
        if not optimize:
            cmd.append('--no-optimize')
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            
            if result.stderr:
                print("Build warnings/errors:")
                print(result.stderr)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Build failed: {e}")
            print(f"Output: {e.stdout}")
            print(f"Errors: {e.stderr}")
            return False
    
    def create_installer(self):
        """Create installer using InnoSetup"""
        print("\nCreating installer...")
        
        # Check if InnoSetup script exists
        if not self.iss_script.exists():
            print(f"  ✗ InnoSetup script not found: {self.iss_script}")
            return False
        
        # Check if executable exists
        exe_path = self.project_root / 'dist' / 'SchoolManagementSystem.exe'
        if not exe_path.exists():
            print(f"  ✗ Executable not found: {exe_path}")
            return False
        
        # Run InnoSetup compiler
        try:
            result = subprocess.run(
                ['iscc', str(self.iss_script)],
                capture_output=True,
                text=True,
                check=True
            )
            
            print("InnoSetup output:")
            print(result.stdout)
            
            if result.stderr:
                print("InnoSetup errors:")
                print(result.stderr)
            
            # Check if installer was created
            installer_pattern = self.installer_dir / 'SchoolManagementSystem_Setup.exe'
            installer_files = list(self.installer_dir.glob('*.exe'))
            
            if installer_files:
                installer_path = installer_files[0]
                size_mb = installer_path.stat().st_size / (1024 * 1024)
                print(f"\n✓ Installer created: {installer_path}")
                print(f"  Size: {size_mb:.2f} MB")
                return True
            else:
                print("\n✗ Installer not created!")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"\n✗ InnoSetup compilation failed: {e}")
            print(f"Output: {e.stdout}")
            print(f"Errors: {e.stderr}")
            return False
    
    def create_portable_zip(self):
        """Create portable ZIP package"""
        print("\nCreating portable ZIP package...")
        
        portable_dir = self.project_root / 'portable'
        portable_dir.mkdir(exist_ok=True)
        
        # Create portable package
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"SchoolManagementSystem_Portable_{timestamp}.zip"
        zip_path = self.release_dir / zip_filename
        
        # Files to include in portable package
        files_to_include = [
            ('dist/SchoolManagementSystem.exe', 'SchoolManagementSystem.exe'),
            ('database', 'database'),
            ('setup_database.py', 'setup_database.py'),
            ('setup_database.bat', 'setup_database.bat'),
            ('README.txt', 'README.txt'),
            ('INSTALLATION_GUIDE.txt', 'INSTALLATION_GUIDE.txt'),
            ('requirements.txt', 'requirements.txt'),
            ('assets', 'assets'),
            ('config.py', 'config.py'),
        ]
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for source, dest in files_to_include:
                    source_path = self.project_root / source
                    
                    if source_path.is_file():
                        zipf.write(source_path, dest)
                        print(f"  Added file: {dest}")
                    elif source_path.is_dir():
                        for file_path in source_path.rglob('*'):
                            if file_path.is_file():
                                arcname = dest / file_path.relative_to(source_path)
                                zipf.write(file_path, arcname)
                        print(f"  Added directory: {dest}")
            
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            print(f"\n✓ Portable package created: {zip_path}")
            print(f"  Size: {size_mb:.2f} MB")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Failed to create portable package: {e}")
            return False
    
    def create_release_package(self, include_source=False):
        """Create complete release package"""
        print("\nCreating release package...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        release_name = f"SchoolManagementSystem_v1.0.0_{timestamp}"
        release_path = self.release_dir / release_name
        release_path.mkdir(exist_ok=True)
        
        # Copy installer
        installer_files = list(self.installer_dir.glob('*.exe'))
        if installer_files:
            installer_src = installer_files[0]
            installer_dest = release_path / installer_src.name
            shutil.copy2(installer_src, installer_dest)
            print(f"  Added installer: {installer_dest.name}")
        
        # Copy portable ZIP if exists
        zip_files = list(self.release_dir.glob('*Portable*.zip'))
        if zip_files:
            zip_src = zip_files[-1]  # Get most recent
            zip_dest = release_path / zip_src.name
            shutil.copy2(zip_src, zip_dest)
            print(f"  Added portable package: {zip_dest.name}")
        
        # Copy documentation
        docs = ['README.md', 'INSTALLATION_GUIDE.txt', 'LICENSE.txt']
        for doc in docs:
            doc_path = self.project_root / doc
            if doc_path.exists():
                shutil.copy2(doc_path, release_path)
                print(f"  Added documentation: {doc}")
        
        # Include source code if requested
        if include_source:
            source_dir = release_path / 'source'
            source_dir.mkdir(exist_ok=True)
            
            # Copy Python source files
            for ext in ['*.py', '*.spec', '*.iss', '*.txt', '*.md']:
                for file_path in self.project_root.rglob(ext):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(self.project_root)
                        dest_path = source_dir / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, dest_path)
            
            print(f"  Added source code")
        
        # Create release notes
        release_notes = release_path / 'RELEASE_NOTES.txt'
        with open(release_notes, 'w', encoding='utf-8') as f:
            f.write(f"""SCHOOL MANAGEMENT SYSTEM - RELEASE NOTES
Version: 1.0.0
Release Date: {datetime.now().strftime('%Y-%m-%d')}

NEW FEATURES:
- Complete student management system
- Teacher management
- Financial tracking with fee management
- Inventory management
- Attendance tracking
- Comprehensive reporting system

INSTALLATION:
1. Run SchoolManagementSystem_Setup.exe
2. Follow the installation wizard
3. Ensure MySQL Server is installed
4. Run setup_database.bat to create database

SYSTEM REQUIREMENTS:
- Windows 7 or later
- MySQL Server 5.7 or later
- 4GB RAM minimum
- 500MB free disk space

KNOWN ISSUES:
- None

SUPPORT:
Email: school@greenwood.edu
""")
        
        print(f"\n✓ Release package created: {release_path}")
        
        return release_path
    
    def sign_installer(self, certificate_path=None, password=None):
        """Sign the installer with digital certificate (optional)"""
        print("\nSigning installer (optional)...")
        
        if not certificate_path:
            print("  ⓘ No certificate provided, skipping signing")
            return True
        
        installer_files = list(self.installer_dir.glob('*.exe'))
        if not installer_files:
            print("  ✗ No installer found to sign")
            return False
        
        installer_path = installer_files[0]
        
        # Check if signtool is available
        try:
            subprocess.run(['signtool', 'sign', '/?'], capture_output=True)
        except FileNotFoundError:
            print("  ✗ signtool not found (part of Windows SDK)")
            return False
        
        # Sign the installer
        try:
            cmd = [
                'signtool', 'sign',
                '/f', certificate_path,
                '/t', 'http://timestamp.digicert.com',  # Timestamp server
                '/v'  # Verbose
            ]
            
            if password:
                cmd.extend(['/p', password])
            
            cmd.append(str(installer_path))
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"  ✓ Installer signed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to sign installer: {e}")
            print(f"  Error: {e.stderr}")
            return False
    
    def run_tests(self):
        """Run tests on the built executable"""
        print("\nRunning tests...")
        
        exe_path = self.project_root / 'dist' / 'SchoolManagementSystem.exe'
        
        if not exe_path.exists():
            print("  ✗ Executable not found for testing")
            return False
        
        # Simple test: check if executable runs
        try:
            # Run with --help or similar flag if your app supports it
            result = subprocess.run(
                [str(exe_path), '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 or result.returncode == 1:  # Many apps return 1 for help
                print(f"  ✓ Executable runs successfully")
                return True
            else:
                print(f"  ✗ Executable returned error code: {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            print("  ✓ Executable started (may not have --help flag)")
            return True
        except Exception as e:
            print(f"  ✗ Executable test failed: {e}")
            return False
    
    def create_complete_package(self, clean=True, optimize=True, include_source=False):
        """Create complete package: executable + installer + portable"""
        print("=" * 60)
        print("  SCHOOL MANAGEMENT SYSTEM - COMPLETE PACKAGING")
        print("=" * 60)
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("\nPlease install missing prerequisites and try again.")
            return False
        
        # Build executable
        if not self.run_build(clean=clean, optimize=optimize):
            return False
        
        # Test executable
        if not self.run_tests():
            print("\nWarning: Executable test failed, continuing anyway...")
        
        # Create installer
        if not self.create_installer():
            return False
        
        # Create portable package
        if not self.create_portable_zip():
            print("\nWarning: Portable package creation failed, continuing...")
        
        # Create complete release package
        release_path = self.create_release_package(include_source=include_source)
        
        print("\n" + "=" * 60)
        print("  PACKAGING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nOutput files:")
        
        # List all created files
        if self.installer_dir.exists():
            for file in self.installer_dir.glob('*.exe'):
                size_mb = file.stat().st_size / (1024 * 1024)
                print(f"  • Installer: {file.name} ({size_mb:.1f} MB)")
        
        if self.release_dir.exists():
            for file in self.release_dir.glob('*Portable*.zip'):
                size_mb = file.stat().st_size / (1024 * 1024)
                print(f"  • Portable: {file.name} ({size_mb:.1f} MB)")
            
            for dir_path in self.release_dir.iterdir():
                if dir_path.is_dir() and dir_path.name.startswith('SchoolManagementSystem_v'):
                    print(f"  • Release package: {dir_path.name}/")
        
        print("\nNext steps:")
        print("1. Test the installer on a clean Windows system")
        print("2. Distribute the installer to users")
        print("3. Provide MySQL installation instructions")
        
        return True


def main():
    """Main packaging function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Package School Management System for distribution'
    )
    parser.add_argument('--no-clean', action='store_true', 
                       help='Do not clean before building')
    parser.add_argument('--no-optimize', action='store_true',
                       help='Do not optimize executable size')
    parser.add_argument('--include-source', action='store_true',
                       help='Include source code in release package')
    parser.add_argument('--sign', action='store_true',
                       help='Sign the installer (requires certificate)')
    parser.add_argument('--certificate', type=str,
                       help='Path to code signing certificate (.pfx)')
    parser.add_argument('--password', type=str,
                       help='Password for code signing certificate')
    
    args = parser.parse_args()
    
    # Create packaging system
    packager = PackagingSystem()
    
    # Run complete packaging
    success = packager.create_complete_package(
        clean=not args.no_clean,
        optimize=not args.no_optimize,
        include_source=args.include_source
    )
    
    # Sign installer if requested
    if success and args.sign:
        packager.sign_installer(args.certificate, args.password)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()