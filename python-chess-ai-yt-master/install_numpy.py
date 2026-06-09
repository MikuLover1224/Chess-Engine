import subprocess
import sys
import os

def install_numpy():
    """Install numpy for the chess AI neural network."""
    print("Installing numpy for neural network...")
    
    try:
        # Try installing numpy using pip
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "numpy"
        ], capture_output=True, text=True, check=True)
        
        if result.returncode == 0:
            print("✅ Numpy installed successfully!")
            print("You can now use the neural network features.")
            return True
        else:
            print(f"❌ Installation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error installing numpy: {e}")
        return False

def check_numpy():
    """Check if numpy is already installed."""
    try:
        import numpy
        print("✅ Numpy is already installed!")
        return True
    except ImportError:
        print("❌ Numpy is not installed.")
        return False

if __name__ == "__main__":
    if not check_numpy():
        install_numpy()
    else:
        print("Numpy is ready for neural network training!")
