"""Menú obligatorio del parcial; comparte motor con la web."""
from engine import crear_red
import json

def mostrar(obj):print(json.dumps(obj,ensure_ascii=False,indent=2))
def main():
    red=None
    while True:
        print('\n=== EPIRED | MENÚ DE CONSOLA ===\n1. Cargar la red\n2. Ruta óptima UCS\n3. Asignar turnos Welsh-Powell\n4. Ruta de reparto TSP\n5. BFS\n6. DFS\n0. Salir')
        op=input('Opción: ').strip()
        if op=='0':break
        if op=='1':
            red=crear_red(); mostrar(red.exportar()['resumen']);continue
        if red is None:
            print('Primero selecciona la opción 1 para cargar la red.');continue
        try:
            if op=='2':mostrar(red.ucs(input('Origen [A]: ').strip().upper() or 'A',input('Destino [J]: ').strip().upper() or 'J'))
            elif op=='3':mostrar(red.welsh_powell())
            elif op=='4':
                inicio=input('Origen [A]: ').strip().upper() or 'A'
                ids=input('Destinos separados por coma [todas las zonas]: ').strip().upper()
                mostrar(red.tsp(inicio,ids.split(',') if ids else None))
            elif op=='5':mostrar(red.bfs(input('Inicio [A]: ').strip().upper() or 'A'))
            elif op=='6':mostrar(red.dfs(input('Inicio [A]: ').strip().upper() or 'A'))
            else:print('Opción no reconocida')
        except ValueError as exc:print('Error:',exc)
if __name__=='__main__':main()
