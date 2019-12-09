import logging
from pathlib import Path

logfile = Path(Path(__file__).parent, 'log')
logger = logging.getLogger('sezanlight')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(str(logfile))
handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logger.addHandler(handler)
# also enable console output:
logger.addHandler(logging.StreamHandler())
