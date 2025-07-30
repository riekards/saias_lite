import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from agent.gui import SaiasGUI

logging.basicConfig(filename='saiasrun_log.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("Your clear log message here.")

def main():
    # Initialize GUI Application
    app = QApplication(sys.argv)
    gui = SaiasGUI()
    gui.show()

    # Future integrations: Initialize self-patch system here

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
