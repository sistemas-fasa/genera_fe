# coding=utf-8
import logging
import sys

from PyQt5.QtWidgets import QApplication
from os.path import join

from controladores.InformaCAEA import InformaCAEAController
from libs.Utiles import LeerIni


def inicio():
    logging.basicConfig(filename='informacaea.log', level=logging.DEBUG,
                        format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    if LeerIni(clave='homo') == 'S':
        print("Sistema en modo homologacion")
        logging.debug("Sistema en modo homologacion")
    else:
        logging.debug("Sistema en modo produccion")
        print("Sistema en modo produccion")
    # Instancia para iniciar una aplicación
    args = []
    #args = ['', '-style', 'Cleanlooks']
    app = QApplication(args)
    ex = InformaCAEAController()
    ex.run()
    sys.exit(app.exec_())

if __name__ == "__main__":

    inicio()

