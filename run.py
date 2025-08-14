import logging
from agent.gui import launch

logging.basicConfig(filename='saiasrun_log.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
	launch()