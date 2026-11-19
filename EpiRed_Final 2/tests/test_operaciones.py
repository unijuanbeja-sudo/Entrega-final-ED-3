"""Pruebas de los problemas de gestión del simulador (resultados reproducibles)."""
import unittest
from engine import (crear_red, plan_traslado, cobertura_alerta, continuidad_red,
                    plan_brigadas, plan_insumos, REPORTES, ENFERMEDADES, Zona)


class EscenariosReproducibles(unittest.TestCase):
    def setUp(self):
        self.red=crear_red()

    def test_varias_enfermedades_distintas(self):
        self.assertEqual(set(ENFERMEDADES), {'COVID-19', 'Dengue', 'IRAG'})
        covid=crear_red('COVID-19').exportar()['resumen']['activos']
        dengue=crear_red('Dengue').exportar('Dengue')['resumen']['activos']
        self.assertEqual(covid, 290)
        self.assertNotEqual(covid, dengue)

    def test_cambio_reporte_conserva_topologia(self):
        mod=crear_red('Dengue',{('Dengue','A'):(200,150,0)})
        self.assertEqual(mod.zonas['A'].activos,50)
        self.assertEqual(len(mod.exportar('Dengue')['aristas']),13)

    def test_traslado_ucs_con_comparador_explicito(self):
        r=plan_traslado(self.red,'A','F','D')
        self.assertEqual(r['optima']['ruta'],['A','C','F'])
        self.assertEqual(r['optima']['costo_minutos'],50)
        self.assertEqual(r['referencia']['ruta'],['A','C','D','E','F'])
        self.assertEqual(r['referencia']['costo_minutos'],57)
        self.assertEqual((r['minutos_ahorrados'],r['porcentaje_ahorro']),(7,12.3))

    def test_sin_ahorro_si_no_existe_desvio_obligatorio(self):
        r=plan_traslado(self.red,'A','F','A')
        self.assertEqual(r['porcentaje_ahorro'],0)

    def test_traslado_mismos_municipios(self):
        with self.assertRaises(ValueError):plan_traslado(self.red,'A','A','D')

    def test_alerta_un_nivel(self):
        r=cobertura_alerta(self.red,'A',1)
        self.assertEqual(set(r['zonas_alcanzadas']), {'A','B','C','D','G'})
        self.assertEqual(r['total_zonas'],5)

    def test_alerta_dos_niveles(self):
        r=cobertura_alerta(self.red,'A',2)
        self.assertEqual(r['total_zonas'],9)
        self.assertNotIn('I',r['zonas_alcanzadas'])

    def test_alerta_saltos_invalidos(self):
        for x in (0,6,-3,1.2,True):
            with self.subTest(valor=x),self.assertRaises(ValueError):cobertura_alerta(self.red,'A',x)

    def test_enlace_critico(self):
        r=continuidad_red(self.red,'G','J')
        self.assertTrue(r['enlace_critico'])
        self.assertEqual(r['total_criticos'],3)
        self.assertIsNone(r['minutos_respaldo'])

    def test_enlace_con_respaldo(self):
        r=continuidad_red(self.red,'A','B')
        self.assertFalse(r['enlace_critico'])
        self.assertGreater(r['minutos_respaldo'],r['costo_directo'])
        self.assertEqual(r['ruta_respaldo'][0],'A')
        self.assertEqual(r['ruta_respaldo'][-1],'B')

    def test_enlace_que_no_existe(self):
        with self.assertRaises(ValueError):continuidad_red(self.red,'A','I')

    def test_brigadas_sin_adyacentes_compartidos(self):
        r=plan_brigadas(self.red)
        self.assertEqual(r['cantidad_colores'],3)
        self.assertEqual(r['reduccion_bloques_pct'],70)
        self.assertTrue(r['sin_conflictos'])
        for a,vecinos in self.red.ady.items():
            for b in vecinos:self.assertNotEqual(r['colores'][a],r['colores'][b])

    def test_reparto_y_referencia_mismos_destinos(self):
        r=plan_insumos(self.red,'A',list(self.red.zonas))
        self.assertEqual(r['plan']['costo_minutos'],327)
        self.assertEqual(r['referencia']['costo_minutos'],362)
        self.assertEqual(r['minutos_diferencia'],35)
        self.assertEqual(r['porcentaje_diferencia'],9.7)
        self.assertEqual(r['plan']['visitas'][0],'A')
        self.assertEqual(r['plan']['visitas'][-1],'A')

    def test_reparto_sin_zonas(self):
        with self.assertRaises(ValueError):plan_insumos(self.red,'A',[])

    def test_validacion_tipo_booleano_como_reporte(self):
        with self.assertRaises(ValueError):Zona('X','Ejemplo',True,0,0,0,0)

if __name__=='__main__':unittest.main()
