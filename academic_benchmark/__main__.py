import sys
import os
from .core.cli import parse_args
from .core.registry_setup import AlgorithmRegistry

def main():
    """Main entrypoint for academic benchmark."""
    args, unknown = parse_args()
    
    if args.subcommand == "dashboard":
        import subprocess
        from pathlib import Path
        print("\nLaunching dashboard... Go to http://localhost:8501")
        print("Press Ctrl+C to stop.")
        try:
            dashboard_path = Path(__file__).resolve().parent / "dashboard.py"
            subprocess.run(["streamlit", "run", str(dashboard_path)])
        except KeyboardInterrupt:
            print("\nDashboard stopped.")
        return 0
        
    elif args.subcommand == "run":
        # Launch non-interactive execution (to be implemented if needed)
        print("CLI 'run' placeholder")
        return 0
        
    elif args.subcommand == "tune":
        # Launch non-interactive tuning
        print("CLI 'tune' placeholder")
        return 0
        
    else:
        # No subcommand -> Launch interactive engine
        from .cli_engine import main as engine_main
        # Provide the parsed args so mode/flags can be used
        sys.argv = [sys.argv[0]] # clean up args for cli_engine internal argparse
        return engine_main()

if __name__ == "__main__":
    sys.exit(main())
