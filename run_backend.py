import sys
import runpy

# Run app.py as a module so relative imports work
sys.path.insert(0, "./")
runpy.run_module("Threadly_SDK.app", run_name="__main__")
