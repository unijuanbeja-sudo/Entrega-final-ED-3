"""Pruebas HTTP de la aplicación local, sin servicios de terceros."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from server import Handler, CAMBIOS, LOCK

class APIEpiRed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.t=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.t.start()
        cls.base=f'http://127.0.0.1:{cls.http.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.t.join(timeout=2)

    def setUp(self):
        with LOCK:CAMBIOS.clear()

    def get(self,path):
        with urlopen(self.base+path,timeout=6) as r:return json.load(r)

    def post(self,path,obj):
        payload=json.dumps(obj).encode('utf-8')
        req=Request(self.base+path,data=payload,headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=6) as r:return json.load(r)

    def test_frontend_disponible(self):
        with urlopen(self.base+'/',timeout=6) as r:self.assertIn(b'Mapa de enfermedades',r.read())

    def test_api_estado(self):
        d=self.get('/api/estado?enfermedad=Dengue')
        self.assertEqual(d['enfermedad'],'Dengue')
        self.assertEqual(len(d['aristas']),13)

    def test_api_muestras(self):
        d=self.get('/api/operaciones/traslado?origen=A&destino=F&via=D')
        self.assertEqual(d['porcentaje_ahorro'],12.3)

    def test_api_brigadas(self):
        d=self.get('/api/operaciones/brigadas')
        self.assertTrue(d['sin_conflictos'])

    def test_api_modificacion_y_restauracion(self):
        r=self.post('/api/registros/actualizar',{
            'enfermedad':'COVID-19','zona':'C','confirmados':600,'recuperados':400,'fallecidos':5})
        self.assertTrue(r['ok'])
        d=self.get('/api/estado');self.assertEqual(d['modificaciones'],1)
        self.assertEqual(next(z for z in d['zonas'] if z['id']=='C')['activos'],195)
        self.post('/api/registros/restablecer',{})
        d=self.get('/api/estado');self.assertEqual(d['modificaciones'],0)
        self.assertEqual(next(z for z in d['zonas'] if z['id']=='C')['activos'],80)

    def test_api_rechaza_inconsistencias(self):
        req=Request(self.base+'/api/registros/actualizar',data=json.dumps({
            'enfermedad':'COVID-19','zona':'A','confirmados':3,'recuperados':6,'fallecidos':1}).encode(),
            headers={'Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as c:urlopen(req,timeout=6)
        self.assertEqual(c.exception.code,400)

    def test_api_rechaza_codigos_invalidos(self):
        with self.assertRaises(HTTPError) as c:self.get('/api/ucs?inicio=ZZ&destino=A')
        self.assertEqual(c.exception.code,400)

if __name__=='__main__':unittest.main()
