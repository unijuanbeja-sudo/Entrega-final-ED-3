# EpiRed — Centro de inteligencia epidemiológica (piloto C3)

**EpiRed es un dashboard web interactivo que muestra problemas operativos epidemiológicos en lugar de presentar los algoritmos como botones académicos.** Su motor real está escrito en Python, con un grafo propio y los algoritmos que pide la entrega final del parcial de Estructuras de Datos No Lineales.

> **Muy importante:** es una SIMULACIÓN EDUCATIVA. No contiene datos actualizados de INS/SIVIGILA. Los reportes, los tiempos de conexión y los porcentajes de ahorro son hipotéticos; no sirven para decisiones sanitarias reales. Cubre un piloto de diez municipios de Antioquia, no todo Colombia.

## Iniciar en Windows / macOS / Linux

1. Extrae el ZIP y abre la carpeta `EpiRed_Final` en VS Code.
2. Comprueba que tienes **Python 3.10 o superior** (en Windows `py --version` o `python --version`; en macOS/Linux `python3 --version`).
3. Ejecuta en la terminal situada en la carpeta raíz:

   ```bash
   python server.py
   ```
   Si el comando `python` no existe, utiliza `python3 server.py` o `py server.py`.

4. Abre **http://localhost:8000** en un navegador. Mantén abierta la terminal del servidor. **No abras el archivo `static/index.html` haciendo doble clic**: sin el servidor los cálculos no funcionarían.
5. Si el puerto está ocupado: en Windows PowerShell `$env:PORT=8001; python server.py`; en macOS/Linux `PORT=8001 python3 server.py`. Luego visita `http://localhost:8001`.

**No es necesario instalar dependencias de Python ni NPM.** El mapa de puntos y conexiones funciona sin internet; la cartografía de fondo opcional usa teselas de OpenStreetMap, por lo que estas sí necesitan conexión.

## Cómo probar la app en 6 minutos

| Menú en la app | Qué probar | Qué deberías observar |
|---|---|---|
| **Centro de control** | Selecciona COVID-19, dengue e IRAG en la esquina superior | Cambian indicadores, ranking, gráfico y marcadores del mapa |
| **Mapa de enfermedades** | Pulsa municipios del mapa y activa **Red logística** | Fichas de casos y conexiones representadas sobre coordenadas |
| **Traslado de muestras** | Origen **Medellín**, destino **Caldas**, consolidación **Envigado** | Ruta mejor: Medellín → Itagüí → Caldas, **50 min**; referencia: **57 min**; reducción hipotética **12,3 %** |
| **Alertas territoriales** | Origen **Medellín**, 2 conexiones | Cobertura: **9 de 10 municipios**, con grupos por nivel |
| **Continuidad de la red** | Evalúa **Copacabana – Rionegro** y luego **Medellín – Bello** | El primero es crítico; el segundo tiene respaldo por otras conexiones |
| **Brigadas sanitarias** | Pulsa **Recalcular turnos** | **3 bloques** para diez municipios, sin vecinos simultáneos; reducción académica de bloques **70 %** |
| **Distribución de insumos** | Deja todos los destinos y centro **Medellín** | Circuito **327 min**, comparado con orden alfabético **362 min** (9,7 % de diferencia positiva) |
| **Registros y datos** | Cambia un valor entero en un reporte, guarda y vuelve al mapa | El dato y los indicadores cambian; también puedes **Exportar CSV/JSON** y **Restaurar** |

**Porcentajes:** son comparaciones matemáticas del escenario, no mejoras sanitarias medidas. UCS optimiza la suma de los minutos hipotéticos de las aristas; TSP es aproximado, nunca se anuncia como óptimo exacto.

## Menú de consola que exige la guía

Con el servidor en otra terminal o sin él:

```bash
python consola.py
```

Selecciona primero `1` para cargar la red. Luego están las opciones obligatorias: `2` UCS, `3` Welsh–Powell y `4` TSP, más BFS y DFS para evidencias de la rúbrica. Comparten `engine.py` con la web.

## Ejecutar pruebas

```bash
python -m unittest discover -s tests -v
```

Se incluyen **32 pruebas automatizadas** de modelo de datos, validación, algoritmo, escenarios y endpoints HTTP. Se comprobaron también las pantallas y cambios de formularios usando una sesión de navegador en un entorno de pruebas con respuestas reales del servidor local. Las capturas están en `evidencias/`.

## Arquitectura / archivos

```text
EpiRed_Final/
├── server.py                 Servidor HTTP, endpoints y edición temporal de registros
├── engine.py                 Zona, Red, BFS, DFS, UCS, Welsh–Powell, TSP y operaciones
├── consola.py                Menú interactivo solicitado por el profesor
├── static/
│   ├── index.html            Secciones de la plataforma, controles y formularios
│   ├── style.css             Interfaz responsiva
│   ├── app.js                Visualización del mapa y consumo real de endpoints
│   ├── logo.svg              Isotipo EpiRed
│   └── colombia-inset.svg    Silueta indicativa de Colombia
├── tests/                    Pruebas unitarias y HTTP
├── evidencias/               Capturas para sustentación
├── Reporte_Tecnico_EpiRed_Entrega_Final_C3.docx
├── README.md
└── EVIDENCIAS_PRUEBAS.txt
```

### Modelo de la red

- **Vértice (municipio):** código, nombre, latitud/longitud y cifras por evento (`confirmados`, `recuperados`, `fallecidos`, `activos`).
- **Arista (relación operativa):** conexión bidireccional entre dos municipios, ponderada en **minutos de práctica** (no distancia, ni tiempos viales reales). Diez vértices y trece aristas.
- **Grafo:** diccionario de adyacencia construido manualmente (`Red.ady`), sin NetworkX ni librerías externas.
- **Fuente de los diez municipios, datos de COVID y aristas:** `EpiRed/EpiRed-Grafo/datos.py` en https://github.com/unijuanbeja-sudo/EpiRed, consultado el 17/11/2026.
- **Dengue e IRAG:** valores nuevos INVENTADOS para poder probar filtros por evento.
- **Coordenadas:** aproximaciones de centros urbanos, solo para mostrar marcadores en el mapa. Los tiempos de ruta no se calculan con estas coordenadas.

### Motor de decisiones (descripción breve)

- **BFS:** vecinos por niveles, mostrado al usuario como plan de difusión territorial de alertas.
- **DFS:** verificación de conectividad con un enlace retirado y detección de ciclos, mostrado como continuidad de una red logística.
- **UCS:** mínimo tiempo acumulado según pesos positivos, mostrado como traslado de muestras entre municipios, frente a ruta de referencia con consolidación obligatoria.
- **Welsh–Powell:** asignación heurística de grupos compatibles, mostrado como bloques de brigadas para municipios vecinos que no pueden operar simultáneamente.
- **TSP aproximado:** vecino más cercano + UCS en cada tramo, mostrado como circuito de distribución que regresa al origen, comparado con un recorrido en orden alfabético.

### API disponible

- `GET /api/estado?enfermedad=COVID-19|Dengue|IRAG`
- `GET /api/operaciones/traslado?origen=A&destino=F&via=D`
- `GET /api/operaciones/alerta?origen=A&saltos=2`
- `GET /api/operaciones/continuidad?desde=G&hasta=J`
- `GET /api/operaciones/brigadas`
- `GET /api/operaciones/insumos?origen=A&destinos=B,C,D,E,F,G,H,I,J`
- `POST /api/registros/actualizar` (`{ "enfermedad":"Dengue","zona":"B","confirmados":99,"recuperados":60,"fallecidos":1 }`)
- `POST /api/registros/restablecer` (`{}`)
- Endpoints pedagógicos: `GET /api/red`, `GET /api/bfs`, `GET /api/dfs`, `GET /api/ucs`, `GET /api/welsh-powell`, `GET /api/tsp`.

### Lo que todavía faltaría para uso institucional real

Autenticación, control de acceso, auditoría de modificaciones, base de datos permanente, integración con datos oficiales INS/SIVIGILA, vigilancia con tasas y denominadores poblacionales, alertas validadas por autoridades, tiempos reales de transporte, validación de rutas viales, seguridad informática, cumplimiento de protección de datos y pruebas de operación. **No se deben usar estos resultados como guía clínica ni como un servicio de despacho real.**

El informe Word adjunto desarrolla el diseño de clases, los algoritmos, ejemplos reproducibles, limitaciones, capturas, conclusiones y un guion para exponer la entrega.
