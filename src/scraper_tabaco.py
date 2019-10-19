####
# Web Scraping de l'evolucio de preus i vendes de tabac a Espanya
# Repositori: https://github.com/dgilros/WebScraping
# Autor: David Gil del Rosal
####
import re
import requests
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
import pandas as pd
import time

MIN_YEAR = 2005
MAX_YEAR = int(time.strftime("%Y"))-1
USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0'


####
# Classe que analitza el fitxer robots.txt si existeix i indica
# si una pagina es accessible pel bot. Es un proxy per a 
# RobotFileParser
####
class RobotsTxt:
    def __init__(self, base_url):
        try:
            url = urljoin(base_url, 'robots.txt')
            self.rp = RobotFileParser()
            self.set_url(url)
            self.rp.read()
        except:
            self.rp = None
            
    def canFetch(self, url):
        if self.rp is None:
            return True
        else:
            return self.rp.can_fetch('*', url)

####
# Classe que implementa un scraper basic. Els arguments son
# el URL Base, el nom del CSV a generar i els atributs (i.e.
# les columnes del CSV)
# El consructor crida el metodes followLinks() i writeCSV()
####
class BasicScraper:
	# El constructor reb l'URL base del lloc web, el
	# nom del CSV a generar i una llista d'atributs (columnes)
    def __init__(self, base_url, csv_name, columns):
        self.base_url = base_url
        self.csv_name = csv_name 
        self.attr = columns
        self.robotstxt = RobotsTxt(base_url)
        self.records = []
        self.followLinks()
        self.writeCSV()
    
    # Donat un URL relatiu retorna l'URL complet
    def getFullUrl(self, url):
        return urljoin(self.base_url, url)
    
    # Genera un nou objecte BeatifulSoup a partir d'un request
    # per al URL passat com argument o None si no es possible
	# obtenir-lo ja sigui per un error de carrega o per estar
	# filtrar al fitxer "robots.txt"
    def newSoup(self, url):
        soup = None
        try:
            if self.robotstxt.canFetch(url):
                req = requests.get(self.getFullUrl(url), 
                                   headers={'User-Agent': USER_AGENT})
                soup = BeautifulSoup(req.text, 'lxml')
        except:
            pass
        return soup
        
    # Metode abstracte que extreu els links de la pagina inicial
    def followLinks(self):
        pass

    # Metode abstracte que analitza les pagines i insereix els registres
    # en la llista self.records
    def parse(self, url, **kwargs):
        pass
                
    # Metode que genera un fitxer CSV. Construeix un dataframe de pandas
    # amb la llista de registres i el nom dels atributs i despres
    # usa el metode to_csv() de l'objecte dataframe
    def writeCSV(self, sep=';'):
        df = pd.DataFrame(self.records, columns=self.attr)
        df.to_csv(self.csv_name, sep=sep, index=False)
    

####
# Classe que obte les pagines de resolucions de preu de tabac del BOE
# i per a cadascuna d'elles l'analitza i emmagatzema els preus
####        
class PreciosScraper(BasicScraper):
	# El constructor reb el nom del CSV a generar i les columnes
    def __init__(self, filename, columns):
        BasicScraper.__init__(self, 'https://www.boe.es', filename, columns)
                
    # Accedeix al cercador del BOE per a obtenir les pagines de resolucio
    # de preus i les analitza cridant parse()
    def followLinks(self):
        url = 'buscar/legislacion_ava.php?campo%5B0%5D=ID_SRC&dato%5B0%5D=&operador%5B0%5D=and&campo%5B1%5D=NOVIGENTE&operador%5B1%5D=and&campo%5B2%5D=CONSO&operador%5B3%5D=and&campo%5B3%5D=TIT&dato%5B3%5D=comisionado+para+el+mercado+de+tabacos&operador%5B3%5D=and&campo%5B4%5D=ID_RNG&dato%5B4%5D=1370&operador%5B4%5D=and&campo%5B5%5D=ID_DEM&dato%5B5%5D=&operador%5B5%5D=and&campo%5B6%5D=MAT&dato%5B6%5D=Tabaco+Precios&operador%5B6%5D=and&campo%5B7%5D=DOC&dato%5B7%5D=&operador%5B7%5D=and&campo%5B8%5D=NBO&dato%5B8%5D=&operador%5B8%5D=and&campo%5B9%5D=NOF&dato%5B9%5D=&operador%5B9%5D=and&campo%5B10%5D=DOC&dato%5B10%5D=&operador%5B11%5D=and&campo%5B11%5D=FPU&dato%5B11%5D%5B0%5D=2002-01-01&dato%5B11%5D%5B1%5D=2019-10-14&operador%5B12%5D=and&campo%5B12%5D=FAP&dato%5B12%5D%5B0%5D=&dato%5B12%5D%5B1%5D=&page_hits=2000&sort_field%5B0%5D=PESO&sort_order%5B0%5D=desc&sort_field%5B1%5D=ref&sort_order%5B1%5D=asc&accion=Buscar'
        soup = self.newSoup(url)
		# la consulta al cercador retorna un document HTML on els enllacos a
		# Resolucions de preus tenen class CSS resultado-busqueda-link-defecto
        for link in soup.find_all('a', 'resultado-busqueda-link-defecto'):
			# accedim a la versio XML de la Resolucio modificant l'URL
            url = link['href']
            url = url.replace('../buscar/doc.php', 'diario_boe/xml.php')
            self.parse(url)
    
    # Analitza les pagines de resolucio de preus inserint un registre
    # en self.records per a cada modificacio de preu        
    def parse(self, url, **kwargs):
        soup = self.newSoup(url)
        date = soup.find('fecha_vigencia').get_text()
        if date.strip() == '': return
        year = int(date[0:4])
        if year < MIN_YEAR or year > MAX_YEAR: return
        # les resolucions tenen dues taules: ens interessa la primera 
		# que recull els preus a 'Peninsula e Illes Balears'. 
		# L'estructura es:		
		#   <table>
		#     <tr>
		#      <td><p>MARCA1</p></td>
		#      <td><p>PREU1</p></td>
		#     </tr>
		#     <tr>
		#      <td><p>MARCA2</p></td>
		#      <td><p>PREU2</p></td>
		#     </tr>
        #    ...
        #   </table>		
        for table in soup.find_all('table'):
            for tr in table.find_all('tr'):
                values = tr.find_all('p')
                if len(values) == 2:
                    brand = values[0].get_text().strip()
                    price = values[1].get_text().strip()
                    try:
                        # obtenim el preu
                        price = float(price.replace(',', '.'))
                        self.records.append([brand, date, price])
                    except:
					    # ignorem les files que no tenen preu associat
                        pass
			# sortir quan hem processat la primera taula
            break
        
####
# Classe que obte les fulles de calcul de vendes de
# tabac del Ministeri d'Hisenda i per a cadascuna d'elles 
# l'analitza i emmagatzema els valors
####                    
class VentasScraper(BasicScraper):
	# El constructor reb el nom del CSV a generar i les columnes
    def __init__(self, filename, columns):
        BasicScraper.__init__(self, 'https://www.hacienda.gob.es',
                              filename, columns)
    
    # Extreu els enllacos d'estadistiques de vendes de tabac
    # i crida a parse() per a analitzar-los
    def followLinks(self):
        url = '/es-ES/Areas%20Tematicas/CMTabacos/Paginas/EstadisticassobreelMercadodeTabacos.aspx'
        soup = self.newSoup(url)
        for link in soup.find_all('a'):
            # extreurem nomes els resums anuals de vendes identificats pel
            # text del enllac
            text = link.get_text()
            match = re.match('Resumen anual de ventas.+?(\d+)', text)
            if match is not None:
                year = int(match.groups()[0])
                if year >= MIN_YEAR:
                    url = link['href']
                    self.parse(url, year=year)
    
    # Obte i analitza les fulles de calcul d'estadistiques de preus
    # inserint els registres en la llista self.records
    def parse(self, url, **kwargs):
        year = kwargs['year']
        soup = self.newSoup(url)
		# extreu els enllacos amb text "Comunidades (euros)" i
		# "Comunidades (unidades)" que son els que ens interessa
		# analitzar
        for link in soup.find_all('a'):
            text = link.get_text()
            match = re.match('Comunidades \(([^\)]+)', text)
            if match is not None:
                units = 'euros' if match.groups()[0] == 'euros' else 'cantidad'
                if year < MIN_YEAR or year > MAX_YEAR:
                    continue
                elif year <= 2014:
                    header, cols = 3, 'A:E'
                else:
                    # el 2015 va haver un canvi de format dels informes
                    header, cols = 5, 'B:F'
                try:
				    # llegeix el fitxer Excel en un dataframe de Pandas. Te 16 
                    # files: una per Comunitat Autonoma excepte Canaries
                    url = self.getFullUrl(link['href'])
                    df = pd.read_excel(url, header=header, usecols=cols, nrows=16)
                    for _, row in df.iterrows():
					    # inserim un registre per a cada combinacio Comunitat-Any-Labor
						# on Labor es el tipus de de tabac: cigarrets, cigarros i picadures
                        for col in ['CIGARRILLOS', 'CIGARROS', 'P. LIAR', 'P. PIPA']:
                            record = [row['COMUNIDAD'], year, col, units, int(row[col])]
                            self.records.append(record)
                except:
                    # ignorem els errors de format incorrecte
                    pass
                 
####
# Instanciem els dos scrapers per a generar els fitxers CSV
####
PreciosScraper('TabacoPrecios.csv', ['Marca','Fecha', 'Precio'])
VentasScraper('TabacoVentas.csv', ['Comunidad', 'Anyo', 'Labor', 'Unidad', 'Total'])