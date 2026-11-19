"""EpiRed: simulador operacional epidemiológico con grafo propio.

Las 10 zonas y las 13 conexiones provienen de EpiRed-Grafo/datos.py del
repositorio académico. Los tiempos y reportes SON SIMULADOS.
El grafo es no dirigido, ponderado por minutos *hipotéticos* de traslado.
No utiliza bibliotecas externas de grafos.
"""
from collections import deque
from dataclasses import dataclass, asdict
import heapq
import math


ENFERMEDADES = {
    "COVID-19": "COVID-19",
    "Dengue": "Dengue",
    "IRAG": "Infección respiratoria aguda grave (IRAG)",
}


@dataclass
class Zona:
    id: str
    nombre: str
    confirmados: int
    recuperados: int
    fallecidos: int
    x: float
    y: float
    lat: float = 0.0
    lon: float = 0.0

    def __post_init__(self):
        if not self.id or not self.nombre:
            raise ValueError("El código y nombre de la zona son obligatorios")
        for valor in (self.confirmados, self.recuperados, self.fallecidos):
            if type(valor) is not int or valor < 0:
                raise ValueError("Los reportes deben ser enteros no negativos")
        if self.recuperados + self.fallecidos > self.confirmados:
            raise ValueError("Recuperados más fallecidos no pueden superar confirmados")
        if not all(map(math.isfinite, (self.lat, self.lon, self.x, self.y))):
            raise ValueError("Las coordenadas deben ser finitas")

    @property
    def activos(self):
        return self.confirmados - self.recuperados - self.fallecidos

    @property
    def carga(self):
        # Umbrales didácticos para organizar escenarios, NO medida de riesgo.
        return "Alta" if self.activos >= 50 else "Media" if self.activos >= 20 else "Baja"

    def exportar(self):
        return {**asdict(self), "activos": self.activos,
                "carga": self.carga, "riesgo": self.carga}


class Red:
    def __init__(self):
        self.zonas = {}
        self.ady = {}

    def agregar_zona(self, zona):
        if zona.id in self.zonas:
            raise ValueError(f"Zona duplicada: {zona.id}")
        self.zonas[zona.id] = zona
        self.ady[zona.id] = {}

    def conectar(self, a, b, minutos):
        if (a not in self.zonas or b not in self.zonas or a == b
                or not isinstance(minutos, (int, float))
                or not math.isfinite(minutos) or minutos <= 0):
            raise ValueError("Conexión inválida: requiere nodos distintos y minutos positivos")
        self.ady[a][b] = float(minutos)
        self.ady[b][a] = float(minutos)

    def validar(self, nodo):
        if nodo not in self.zonas:
            raise ValueError(f"No existe el municipio con código {nodo!r}")

    def bfs(self, inicio):
        """Cobertura por número de saltos; NO simula contagios ni minutos."""
        self.validar(inicio)
        cola = deque([inicio]); vistos = {inicio}; orden = []; niveles = {inicio: 0}
        while cola:
            u = cola.popleft(); orden.append(u)
            for v in sorted(self.ady[u]):
                if v not in vistos:
                    vistos.add(v); niveles[v] = niveles[u] + 1; cola.append(v)
        return {"orden": orden, "niveles": niveles}

    def dfs(self, inicio):
        """Audita profundidad y ciclos del grafo no dirigido."""
        self.validar(inicio)
        orden = []; vistos = set(); padres = {inicio: None}; ciclos = []; detectadas = set()
        def visitar(u):
            vistos.add(u); orden.append(u)
            for v in sorted(self.ady[u]):
                if v not in vistos:
                    padres[v] = u; visitar(v)
                elif padres.get(u) != v:
                    arista = tuple(sorted((u, v)))
                    if arista not in detectadas:
                        detectadas.add(arista); ciclos.append(list(arista))
        visitar(inicio)
        return {"orden": orden, "aristas_retroceso": ciclos, "hay_ciclos": bool(ciclos)}

    def ucs(self, inicio, destino, evitar_enlace=None):
        """Búsqueda de costo uniforme (Dijkstra) sobre minutos positivos."""
        self.validar(inicio); self.validar(destino)
        if evitar_enlace is not None:
            a, b = evitar_enlace
            if a not in self.ady or b not in self.ady[a]:
                raise ValueError("El enlace que se desea evitar no existe")
        dist = {inicio: 0.0}; padre = {inicio: None}; heap = [(0.0, inicio)]; expandidos = []
        while heap:
            costo, u = heapq.heappop(heap)
            if costo != dist[u]:
                continue
            expandidos.append(u)
            if u == destino:
                ruta = []; nodo = u
                while nodo is not None:
                    ruta.append(nodo); nodo = padre[nodo]
                return {"ruta": ruta[::-1], "costo_minutos": round(costo, 2), "expandidos": expandidos}
            for v, peso in sorted(self.ady[u].items()):
                if evitar_enlace is not None and {u, v} == set(evitar_enlace):
                    continue
                nuevo = costo + peso
                if nuevo < dist.get(v, math.inf):
                    dist[v] = nuevo; padre[v] = u
                    heapq.heappush(heap, (nuevo, v))
        return {"ruta": [], "costo_minutos": None, "expandidos": expandidos}

    def costo_ruta(self, ruta):
        if not ruta:
            return None
        for z in ruta:
            self.validar(z)
        if any(v not in self.ady[u] for u, v in zip(ruta, ruta[1:])):
            raise ValueError("La ruta incluye una conexión inexistente")
        return round(sum(self.ady[u][v] for u, v in zip(ruta, ruta[1:])), 2)

    def welsh_powell(self):
        """Heurística de coloración, NO garantiza mínimo cromático global."""
        orden = sorted(self.zonas, key=lambda z: (-len(self.ady[z]), z))
        colores = {}; grupos = []
        for nodo in orden:
            if nodo in colores:
                continue
            color = len(grupos); grupo = []
            for candidato in orden:
                if candidato not in colores and all(candidato not in self.ady[x] for x in grupo):
                    colores[candidato] = color; grupo.append(candidato)
            grupos.append(grupo)
        valido = all(colores[a] != colores[b] for a in self.ady for b in self.ady[a])
        return {"orden_por_grado": orden, "grados": {n: len(self.ady[n]) for n in orden},
                "colores": colores, "grupos": grupos, "cantidad_colores": len(grupos),
                "sin_conflictos": valido}

    def recorrido_ordenado(self, inicio, destinos):
        """Circuito con orden explícito de paradas; cada tramo usa UCS."""
        self.validar(inicio)
        total = 0.0; actual = inicio; visitas = [inicio]; recorrido = [inicio]; tramos = []
        for z in destinos:
            self.validar(z)
            if z == actual:
                continue
            resultado = self.ucs(actual, z)
            if resultado['costo_minutos'] is None:
                raise ValueError("No es posible completar la visita")
            tramos.append({"desde": actual, "hasta": z,
                           "ruta": resultado['ruta'], "minutos": resultado['costo_minutos']})
            total += resultado['costo_minutos']; recorrido.extend(resultado['ruta'][1:])
            visitas.append(z); actual = z
        if actual != inicio:
            regreso = self.ucs(actual, inicio)
            if regreso['costo_minutos'] is None:
                raise ValueError("No existe conexión de regreso al centro")
            tramos.append({"desde": actual, "hasta": inicio,
                           "ruta": regreso['ruta'], "minutos": regreso['costo_minutos']})
            total += regreso['costo_minutos']; recorrido.extend(regreso['ruta'][1:]); visitas.append(inicio)
        return {"visitas": visitas, "recorrido_completo": recorrido,
                "tramos": tramos, "costo_minutos": round(total, 2)}

    def tsp(self, inicio, destinos=None):
        """Vecino más cercano sobre rutas UCS y retorno; sin garantía de óptimo."""
        self.validar(inicio)
        objetivos = list(self.zonas) if destinos is None else list(dict.fromkeys(destinos))
        for z in objetivos:
            self.validar(z)
        pendientes = set(objetivos) - {inicio}
        orden = [inicio]; recorrido = [inicio]; total = 0.0; actual = inicio; tramos = []
        while pendientes:
            opciones = []
            for z in sorted(pendientes):
                resultado = self.ucs(actual, z)
                if resultado['costo_minutos'] is not None:
                    opciones.append((resultado['costo_minutos'], z, resultado['ruta']))
            if not opciones:
                raise ValueError("No es posible visitar todas las zonas")
            costo, z, ruta = min(opciones)
            tramos.append({"desde": actual, "hasta": z, "ruta": ruta, "minutos": costo})
            recorrido.extend(ruta[1:]); total += costo; orden.append(z); actual = z; pendientes.remove(z)
        if actual != inicio:
            regreso = self.ucs(actual, inicio)
            if regreso['costo_minutos'] is None:
                raise ValueError("No existe ruta de regreso")
            tramos.append({"desde": actual, "hasta": inicio, "ruta": regreso['ruta'], "minutos": regreso['costo_minutos']})
            recorrido.extend(regreso['ruta'][1:]); total += regreso['costo_minutos']; orden.append(inicio)
        return {"visitas": orden, "recorrido_completo": recorrido, "tramos": tramos,
                "costo_minutos": round(total, 2),
                "metodo": "vecino más cercano + UCS; aproximación sin garantía óptima"}

    def exportar(self, enfermedad="COVID-19"):
        if enfermedad not in ENFERMEDADES:
            raise ValueError("Enfermedad no disponible en la demostración")
        aristas = [{"desde": a, "hasta": b, "minutos": w}
                   for a in self.ady for b, w in self.ady[a].items() if a < b]
        zonas = [z.exportar() for z in self.zonas.values()]
        resumen = {"zonas": len(zonas), "conexiones": len(aristas),
                   "confirmados": sum(z['confirmados'] for z in zonas),
                   "recuperados": sum(z['recuperados'] for z in zonas),
                   "fallecidos": sum(z['fallecidos'] for z in zonas),
                   "activos": sum(z['activos'] for z in zonas),
                   "carga_alta": sum(z['carga'] == 'Alta' for z in zonas)}
        return {"enfermedad": enfermedad, "enfermedades": ENFERMEDADES,
                "zonas": zonas, "aristas": aristas, "resumen": resumen,
                "metadata": {
                    "origen": "COVID-19: dataset del repositorio EpiRed-Grafo/datos.py. Dengue e IRAG: datos adicionales inventados para demo.",
                    "corte": "ESCENARIO SIMULADO, no es vigilancia oficial en tiempo real",
                    "pesos": "Minutos hipotéticos; no medidos por vías ni GPS",
                    "geografia": "Puntos aproximados georreferenciados; líneas de enlace NO representan carreteras",
                    "carga": "Alta ≥50, Media 20–49, Baja <20 casos activos; umbrales académicos, no riesgo individual",
                    "cobertura": "Piloto de 10 municipios de Antioquia, no cobertura nacional"}}


# Datos confirmados / recuperados / fallecidos. COVID del taller original.
# Dengue e IRAG son muestras enteramente ficticias agregadas a la demo.
REPORTES = {
    "COVID-19": {
        "A": (300, 268, 2), "B": (140, 126, 2), "C": (500, 415, 5),
        "D": (180, 168, 2), "E": (100, 84, 1), "F": (90, 81, 1),
        "G": (280, 217, 3), "H": (120, 94, 1), "I": (70, 65, 0),
        "J": (220, 173, 2),
    },
    "Dengue": {
        "A": (126, 96, 0), "B": (75, 52, 0), "C": (91, 70, 1),
        "D": (63, 51, 0), "E": (32, 24, 0), "F": (44, 34, 0),
        "G": (70, 39, 1), "H": (41, 24, 0), "I": (56, 30, 0),
        "J": (79, 63, 0),
    },
    "IRAG": {
        "A": (180, 149, 2), "B": (98, 72, 1), "C": (122, 101, 1),
        "D": (84, 72, 0), "E": (55, 45, 0), "F": (40, 32, 0),
        "G": (74, 51, 1), "H": (57, 38, 0), "I": (42, 30, 0),
        "J": (98, 75, 1),
    },
}
NOMBRES = {"A": "Medellín", "B": "Bello", "C": "Itagüí", "D": "Envigado",
           "E": "Sabaneta", "F": "Caldas", "G": "Copacabana",
           "H": "Girardota", "I": "Barbosa", "J": "Rionegro"}
CONEXIONES = [
    ("A", "B", 20), ("A", "C", 15), ("A", "D", 30), ("B", "C", 30),
    ("C", "D", 10), ("D", "E", 12), ("E", "F", 20), ("C", "F", 35),
    ("A", "G", 35), ("B", "G", 20), ("G", "H", 15), ("H", "I", 20),
    ("G", "J", 40),
]
# Centro urbano aproximado de cada municipio. Se usa solo para la posición
# en el mapa; no para calcular ni ajustar los tiempos del ejercicio.
COORDENADAS = {
    "A": (6.24420, -75.58121), "B": (6.33673, -75.55959),
    "C": (6.17508, -75.61206), "D": (6.16670, -75.58219),
    "E": (6.14990, -75.61548), "F": (6.09432, -75.63335),
    "G": (6.35762, -75.50508), "H": (6.37947, -75.44424),
    "I": (6.44000, -75.33100), "J": (6.14715, -75.37732),
}
# Las posiciones x/y se conservan de la versión anterior para compatibilidad.
POSICIONES = {"A": (.44, .36), "B": (.25, .12), "C": (.23, .47),
             "D": (.47, .64), "E": (.34, .87), "F": (.08, .75),
             "G": (.65, .27), "H": (.83, .43), "I": (.90, .77), "J": (.78, .07)}


def crear_red(enfermedad="COVID-19", cambios=None):
    if enfermedad not in REPORTES:
        raise ValueError("Enfermedad desconocida. Elige COVID-19, Dengue o IRAG")
    red = Red()
    cambios = cambios or {}
    for id, nombre in NOMBRES.items():
        datos = cambios.get((enfermedad, id), REPORTES[enfermedad][id])
        lat, lon = COORDENADAS[id]
        red.agregar_zona(Zona(id, nombre, *datos, *POSICIONES[id], lat, lon))
    for a, b, w in CONEXIONES:
        red.conectar(a, b, w)
    return red


def plan_traslado(red, origen, destino, via):
    if origen == destino:
        raise ValueError("Selecciona municipios distintos para origen y destino")
    ruta = red.ucs(origen, destino)
    if ruta["costo_minutos"] is None:
        raise ValueError("No se encontró un trayecto conectado")
    # Comparador explícito: transporte con consolidación obligatoria en el nodo 'via'.
    parte1 = red.ucs(origen, via)
    parte2 = red.ucs(via, destino)
    if parte1["costo_minutos"] is None or parte2["costo_minutos"] is None:
        raise ValueError("La referencia con paso por punto de consolidación no es posible")
    referencia = {
        "ruta": parte1["ruta"] + parte2["ruta"][1:],
        "costo_minutos": round(parte1["costo_minutos"] + parte2["costo_minutos"], 2),
        "via": via,
    }
    ahorro = round(referencia['costo_minutos'] - ruta['costo_minutos'], 2)
    porcentaje = round(100 * ahorro / referencia['costo_minutos'], 1) if referencia['costo_minutos'] else 0
    return {"optima": ruta, "referencia": referencia, "minutos_ahorrados": ahorro,
            "porcentaje_ahorro": porcentaje,
            "hipotesis": "Referencia: paso obligatorio por punto de consolidación; ambos trayectos usan la misma red de minutos simulados.",
            "nota": "Ahorro estimado dentro del escenario, no medición de tiempo real o velocidad."}


def cobertura_alerta(red, origen, saltos):
    if type(saltos) is not int or saltos < 1 or saltos > 5:
        raise ValueError("La cobertura debe estar entre 1 y 5 conexiones")
    recorrido = red.bfs(origen)
    por_nivel = {}
    for nodo, n in recorrido['niveles'].items():
        if n <= saltos:
            por_nivel.setdefault(str(n), []).append(nodo)
    cobertura = [z for z in recorrido['orden'] if recorrido['niveles'][z] <= saltos]
    return {"origen": origen, "max_conexiones": saltos,
            "zonas_alcanzadas": cobertura, "total_zonas": len(cobertura),
            "por_nivel": por_nivel, "niveles": recorrido['niveles'],
            "orden": recorrido['orden'],
            "nota": "Niveles de contactos operativos, NO simulación epidemiológica de transmisión."}


def _accesibles_por_dfs(red, inicio, enlace_bloqueado):
    """DFS explícito tras retirar de forma conceptual una arista."""
    vistos = set(); pila = [inicio]
    while pila:
        u = pila.pop()
        if u in vistos:
            continue
        vistos.add(u)
        for v in sorted(red.ady[u], reverse=True):
            if {u, v} != set(enlace_bloqueado) and v not in vistos:
                pila.append(v)
    return vistos


def continuidad_red(red, desde, hasta):
    red.validar(desde); red.validar(hasta)
    if hasta not in red.ady[desde]:
        raise ValueError("Escoge un enlace existente entre dos municipios")
    enlaces = [(a, b, m) for a in red.ady for b, m in red.ady[a].items() if a < b]
    criticos = []
    for a, b, m in enlaces:
        if b not in _accesibles_por_dfs(red, a, (a, b)):
            criticos.append({"desde": a, "hasta": b, "minutos": m})
    alterno = red.ucs(desde, hasta, evitar_enlace=(desde, hasta))
    directo = red.ady[desde][hasta]
    return {"desde": desde, "hasta": hasta, "costo_directo": directo,
            "enlace_critico": alterno["costo_minutos"] is None,
            "ruta_respaldo": alterno["ruta"],
            "minutos_respaldo": alterno["costo_minutos"],
            "minutos_extra": (round(alterno['costo_minutos'] - directo, 2)
                              if alterno['costo_minutos'] is not None else None),
            "enlaces_criticos": criticos, "total_criticos": len(criticos),
            "total_enlaces": len(enlaces), "deteccion_ciclos": red.dfs(desde)['hay_ciclos'],
            "nota": "Auditoría topológica con DFS. Los tramos son hipotéticos, no vialidad en tiempo real."}


def plan_brigadas(red):
    p = red.welsh_powell(); cantidad = len(red.zonas)
    return {**p, "zonas": cantidad, "bloques_individuales": cantidad,
            "bloques_agrupados": p['cantidad_colores'],
            "reduccion_bloques_pct": round((cantidad-p['cantidad_colores'])*100/cantidad, 1),
            "nota": "Compara bloques de programación, NO horas efectivas ni dosis aplicadas. Un grupo no tiene zonas vecinas simultáneas."}


def plan_insumos(red, origen, destinos):
    if destinos is None:
        objetivos = list(red.zonas)
    else:
        objetivos = list(dict.fromkeys(destinos))
        if not objetivos:
            raise ValueError("Selecciona al menos una zona")
    mejor = red.tsp(origen, objetivos)
    # Línea de referencia: mismas paradas, pero en orden por código alfabético.
    referencia = red.recorrido_ordenado(origen, sorted(set(objetivos) - {origen}))
    diferencia = round(referencia['costo_minutos'] - mejor['costo_minutos'], 2)
    porcentaje = round(diferencia * 100 / referencia['costo_minutos'], 1) if referencia['costo_minutos'] else 0
    return {"plan": mejor, "referencia": referencia,
            "minutos_diferencia": diferencia, "porcentaje_diferencia": porcentaje,
            "metodo_referencia": "Visitas en orden alfabético por código, tramos calculados con UCS.",
            "nota": "Vecino más cercano es heurístico; puede ser peor que la referencia y NO garantiza solución óptima."}
