import pathlib
import csv


BASE_PATH = pathlib.Path(__file__).parent/"data"
CSV_PATH = BASE_PATH/"csv"
AUDIO_PATH = BASE_PATH/"audio"
CSV_SETTINGS = {'quotechar': '"', 'quoting': csv.QUOTE_ALL}


def in_notebook() -> bool:
    try:
        from IPython import get_ipython
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or JupyterLab
        elif shell == 'TerminalInteractiveShell':
            return False  # IPython terminal
        else:
            return False  # Other shell
    except (NameError, ImportError):
        return False      # No IPython
