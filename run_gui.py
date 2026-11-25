"""Launch the StripSolve desktop GUI."""
from multiprocessing import freeze_support

if __name__ == "__main__":
    # Required for multiprocessing workers in PyInstaller-frozen applications.
    freeze_support()
    from gui.main import main
    raise SystemExit(main())
