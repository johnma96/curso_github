#Importo el modulo turubulencia copia desde otro repo
# import Modules Como tiene pandas_bokeh no se puede

#Algunas funciones básicas
import archivo3
def suma(x,y):
    suma = x + y
    return suma

import archivo2
import archivo4

print('Generando un nuevo cambio en master y creando rama funciones2')

print('A partir de esta linea se crearia las funciones especiales')

def saludar(nombre):
    print('Hola {}'.format(nombre))

def potencia(x,y):
    pot = x**y
    return pot

def modulo(x,y):
    mod = x%y
    return mod

print('Solucioné problemas de mezclado manteniendo lo de mabas ramas')

class Humano():
    def __init__(self, nombre, apellido, profesion):
        self.nombre = nombre
        self.apellido = apellido
        self.profesion = profesion

    def hablar(self, frase):
        print('Don {} dice {}'.format(self.nombre, frase))

#SOLO AGREGO UNA LINEA EXPLICATIVA
#Una vez importado todos los modulos y creado las funciones, el archivo
# principal está lista

print(modulo(3,2))
pedro = Humano('Pedro', 'Ramirez', 'Ingeniero')
print(pedro.hablar(frase = 'Hola mundo'))
