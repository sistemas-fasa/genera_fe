# coding=utf-8
import sys

from PyQt5.QtWidgets import QMessageBox
from libs import Avisos


def showAlert(titulo, mensaje):
    return Avisos.mostrar_info(titulo, mensaje)

def showConfirmation(titulo, mensaje):
    return Avisos.confirmar_accion(titulo, mensaje)


def showMsgAutoClose(titulo, mensaje):
    msg = CajaMensaje()
    msg.setIcon(QMessageBox.Question)
    msg.setText(mensaje)
    msg.setWindowTitle(titulo)
    msg.timeout = 3
    msg.autoClose = True
    msg.setStandardButtons(QMessageBox.Ok)
    retval = msg.exec_()

    return retval

class CajaMensaje(QMessageBox):

    timeout = 0
    autoClose = False
    currentTime = 0

    def showEvent(self, QShowEvent):
        self.currentTime = 0
        if self.autoClose:
            self.startTimer(1000)

    def timerEvent(self, *args, **kwargs):
        self.currentTime += 1
        if self.currentTime >= self.timeout:
            self.done(0)
            self.close()


