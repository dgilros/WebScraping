####
# Web Scraping amb Selenium WebDriver.
# El lloc web conté un cercador de països amb JavaScript i AJAX.
# Repositori: https://github.com/dgilros/WebScraping
# Autor: David Gil del Rosal.
####
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import pandas as pd
import time
import re

####
# Classe que realitza el web scraping.
# Els arguments del constructor són el nom de les capçaleres 
# del CSV que es genera.
####
class CountryScraper:
    # El constructor crea una nova instancia de webdriver amb
    # Firefox
    def __init__(self, *headers):
        self.links = []
        self.headers = headers
        self.records = []
        self.browser = webdriver.Firefox()

    # Obre la pagina del cercador i li envia la cadena passada
    # com a argument        
    def executeSearch(self, search):
        self.browser.get("http://example.webscraping.com/places/default/search")
        input_txt = self.browser.find_element_by_id("search_term")
        input_txt.clear()
        input_txt.send_keys(search)
        input_txt.send_keys(Keys.RETURN)

    # Executa una pausa del nombre de segons passat com a argument
    def pause(self, seconds=2):
        time.sleep(seconds)

    # Obte els resultats de la cerca
    def getAjaxResults(self):
        # pausa per a donar temps a generar els resultats amb AJAX
        self.pause()
        # emmagatzemen els URLs dels resultats de la cerca
        results = self.browser.find_element_by_id("results")
        for link in results.find_elements_by_tag_name("a"):
            self.links.append(link.get_attribute("href"))
        try:
            # paginacio invocant una funcio de JavaScript
            self.browser.find_element_by_id("next")
            self.browser.execute_script("next();")
            # crida recursiva mentres hagi mes pagines
            self.getAjaxResults()
        except:
            pass
        
    # Processa cadascu dels URLs obtinguts, recorrent el
    # DOM per a extreure la informacio rellevant i
    # inserint un registre per a cada URL en la llista
    # records
    def processResults(self):
        for url in self.links:
            self.browser.get(url)
            fields, record = {}, []
            for tr in self.browser.find_elements_by_tag_name("tr"):
                tr_id = tr.get_attribute("id")
                match = re.match('^places_(\S+?)__row$', tr_id)
                if match is not None:
                    value = tr.find_elements_by_tag_name("td")[1].text
                    fields[match.groups()[0]] = value
            fields['population'] = fields['population'].replace(',', '')
            record = list([fields[header] for header in self.headers])
            self.records.append(record)
            self.pause()
    
    # Escriu un fitxer CSV amb els registres emmagatzemats        
    def writeCSV(self, csv_name, sep=';'):
        df = pd.DataFrame(self.records, columns=self.headers)
        df.to_csv(csv_name, sep=sep, index=False)

    # Tanca el navegador Firefox
    def close(self):
        self.browser.quit()
        
if __name__ == '__main__':                
    scraper = CountryScraper('country', 'iso', 'capital', 'population')
    scraper.executeSearch('z')         # països amb una Z en el nom
    scraper.getAjaxResults()
    scraper.processResults()
    scraper.writeCSV('Countries.csv')
    scraper.close()