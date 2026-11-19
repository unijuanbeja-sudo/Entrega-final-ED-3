import unittest
from engine import Red,Zona,crear_red
class PruebasEpiRed(unittest.TestCase):
 def setUp(self):self.red=crear_red()
 def test_datos_base(self):
  s=self.red.exportar()['resumen'];self.assertEqual((s['zonas'],s['conexiones']),(10,13));self.assertEqual(s['activos'],sum(z.activos for z in self.red.zonas.values()))
 def test_bfs(self):
  r=self.red.bfs('A');self.assertEqual(len(r['orden']),10);self.assertEqual(r['niveles']['C'],1)
 def test_dfs(self):
  r=self.red.dfs('A');self.assertEqual(len(set(r['orden'])),10);self.assertTrue(r['hay_ciclos'])
 def test_ucs(self):
  r=self.red.ucs('A','F');self.assertEqual(r['ruta'],['A','C','F']);self.assertEqual(r['costo_minutos'],50)
 def test_ucs_mismo_nodo(self):self.assertEqual(self.red.ucs('A','A')['costo_minutos'],0)
 def test_welsh(self):
  r=self.red.welsh_powell();self.assertTrue(r['sin_conflictos']);self.assertEqual(len(r['colores']),10)
  for a in self.red.ady:
   for b in self.red.ady[a]:self.assertNotEqual(r['colores'][a],r['colores'][b])
 def test_tsp(self):
  r=self.red.tsp('A');self.assertEqual(r['visitas'][0],'A');self.assertEqual(r['visitas'][-1],'A');self.assertEqual(set(r['visitas']),set(self.red.zonas));self.assertGreater(r['costo_minutos'],0)
 def test_tsp_subconjunto(self):self.assertEqual(self.red.tsp('A',['B','C'])['visitas'][0],'A')
 def test_error(self):
  with self.assertRaises(ValueError):self.red.ucs('INVALIDO','A')
  with self.assertRaises(ValueError):self.red.conectar('A','A',10)
 def test_desconectado(self):
  r=Red();r.agregar_zona(Zona('X','X',1,0,0,.2,.2));r.agregar_zona(Zona('Y','Y',1,0,0,.4,.4));self.assertIsNone(r.ucs('X','Y')['costo_minutos'])
if __name__=='__main__':unittest.main()
