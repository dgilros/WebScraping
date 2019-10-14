import re
import pandas as pd
import requests
from bs4 import BeautifulSoup

MIN_YEAR = 2005
USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0'

####
# Classe que implementa un crawler bàsic. Els arguments són
# el URL Base, el nom del CSV a generar i els atributs (i.e.
# les columnes del CSV)
# El consructor crida el mètods followLinks() i writeCSV()
####
class BasicCrawler:
    def __init__(self, base_url, csv_name, columns):
        self.base_url = base_url
        self.csv_name = csv_name 
        self.attr = columns
        self.records = []
        self.followLinks()
        self.writeCSV()
    
    # Genera un nou objecte BeatifulSoup a partir d'un request
    # per al URL passat com argument
    def newSoup(self, url):
        req = requests.get(self.base_url+url, {'User-Agent': USER_AGENT})
        return BeautifulSoup(req.text, 'lxml')
        
    # Mètode abstracte que extreu els links
    def followLinks(self):
        pass

    # Mètode abstract que analitza les pàgines i insereix els registres
    # en la llista self.records
    def parse(self, url, **kwargs):
        pass
                
    # Mètode que genera un fitxer. Construeix un dataframe de pandas
    # amb la llista de registres i el nom dels atributs i després
    # usa el mètode to_csv() de l'objecte dataframe
    def writeCSV(self, sep=';'):
        df = pd.DataFrame(self.records, columns=self.attr)
        df.to_csv(self.csv_name, sep=sep, index=False)
    

####
# Classe que obté les pàgines de resolucions de preu de tabac del BOE
# i per a cadascuna d'elles l'analitza i emmagatzema els preus
####        
class BOECrawler(BasicCrawler):
    def __init__(self, filename, columns):
        BasicCrawler.__init__(self, 'https://www.boe.es/', filename, columns)
        
    # Crida al buscador del BOE per a obtenir les pàgines de resolució
    # de preus i les analitza cridant parse()
    def followLinks(self):
        url = 'buscar/legislacion_ava.php?campo%5B0%5D=ID_SRC&dato%5B0%5D=&operador%5B0%5D=and&campo%5B1%5D=NOVIGENTE&operador%5B1%5D=and&campo%5B2%5D=CONSO&operador%5B3%5D=and&campo%5B3%5D=TIT&dato%5B3%5D=comisionado+para+el+mercado+de+tabacos&operador%5B3%5D=and&campo%5B4%5D=ID_RNG&dato%5B4%5D=1370&operador%5B4%5D=and&campo%5B5%5D=ID_DEM&dato%5B5%5D=&operador%5B5%5D=and&campo%5B6%5D=MAT&dato%5B6%5D=Tabaco+Precios&operador%5B6%5D=and&campo%5B7%5D=DOC&dato%5B7%5D=&operador%5B7%5D=and&campo%5B8%5D=NBO&dato%5B8%5D=&operador%5B8%5D=and&campo%5B9%5D=NOF&dato%5B9%5D=&operador%5B9%5D=and&campo%5B10%5D=DOC&dato%5B10%5D=&operador%5B11%5D=and&campo%5B11%5D=FPU&dato%5B11%5D%5B0%5D=2002-01-01&dato%5B11%5D%5B1%5D=2019-10-14&operador%5B12%5D=and&campo%5B12%5D=FAP&dato%5B12%5D%5B0%5D=&dato%5B12%5D%5B1%5D=&page_hits=2000&sort_field%5B0%5D=PESO&sort_order%5B0%5D=desc&sort_field%5B1%5D=ref&sort_order%5B1%5D=asc&accion=Buscar'
        soup = self.newSoup(url)
        for link in soup.find_all('a', 'resultado-busqueda-link-defecto'):
            url = link['href']
            url = url.replace('../buscar/doc.php', 'diario_boe/xml.php')
            self.parse(url)
    
    # Analitza les pàgines de resolució de preus generant un registre
    # per a cada modificació de preu        
    def parse(self, url, **kwargs):
        soup = self.newSoup(url)
        date = soup.find('fecha_vigencia').get_text()
        if date.strip() == '': return
        area = 'Peninsula e Illes Balears'
        for table in soup.find_all('table', 'tabla'):
            names = table.find_all('p', 'cuerpo_tabla_izq')
            prices = table.find_all('p', 'cuerpo_tabla_centro')
            for n, p in zip(names, prices):
                name = n.get_text().strip()
                price = p.get_text().strip()
                try:
                    price = float(price.replace(',', '.'))
                    self.records.append([name, date, area, price])
                except:
                    pass
            area = 'Ceuta y Melilla'


####
# Classe que obté les fulles de càlcul de vendes de
# tabac del Ministeri d'Hisenda i per a cadascuna d'elles 
# l'analitza i emmagatzema els valors
####                    
class MinhacCrawler(BasicCrawler):
    def __init__(self, filename, columns):
        BasicCrawler.__init__(self, 'https://www.hacienda.gob.es',
                              filename, columns)
    
    # Extreu els enllaços d'estadístiques de vendes de tabac
    # i crida a parse() per a analitzar-les
    def followLinks(self):
        url = '/es-ES/Areas%20Tematicas/CMTabacos/Paginas/EstadisticassobreelMercadodeTabacos.aspx'
        soup = self.newSoup(url)
        for link in soup.find_all('a'):
            text = link.get_text()
            match = re.match('Resumen anual de ventas.+?(\d+)', text)
            if match is not None:
                year = int(match.groups()[0])
                if year >= MIN_YEAR:
                    url = link['href']
                    self.parse(url, year=year)
    
    # Obté i analitza les fulles de càlcul d'estadístiques de preus
    # inserint els registres en la llista
    def parse(self, url, **kwargs):
        year = kwargs['year']
        soup = self.newSoup(url)
        for link in soup.find_all('a'):
            text = link.get_text()
            match = re.match('Comunidades \(([^\)]+)', text)
            if match is not None:
                units = match.groups()[0]
                url = self.base_url + link['href']
                if year < MIN_YEAR:
                    continue
                elif year <= 2014:
                    # el 2014 va haver un canvi de format dels informes
                    header, cols = 3, 'A:E'
                else:
                    header, cols = 5, 'B:F'
                try:
                    df = pd.read_excel(url, header=header, usecols=cols, nrows=16)
                    for _, row in df.iterrows():
                        for col in ['CIGARRILLOS', 'CIGARROS', 'P. LIAR', 'P. PIPA']:
                            record = [row['COMUNIDAD'], year,
                                      col, int(row[col]), units]
                            self.records.append(record)
                except:
                    # ignorem els errors de format incorrecte
                    pass
                 
####
# Cridem els dos crawlers per a generar els fitxers CSV
####
BOECrawler('TabacoPrecios.csv', ['Nombre','Fecha','Area', 'Precio'])
MinhacCrawler('TabacoVentas.csv', ['Comunidad', 'Año', 'Labor', 'Totales', 'Unidades'])
