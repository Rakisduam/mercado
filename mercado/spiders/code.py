# -*- coding: utf-8 -*-
import scrapy
from scrapy.shell import inspect_response
import json
from urllib.parse import urlencode
from urllib.parse import urljoin
import csv
import io
import logging

class CodeSpider(scrapy.Spider):
    name = 'code'
    
    allowed_domains = ['mercadopublico.cl']
    # Enter Login and Password
    rut =  '22.087.581-4'
    passw=  'Licita.1234'
    
    
    
    
        
    def __init__(self, gs_id='', **kwargs):
        
        super().__init__(**kwargs)
        #Check if google id is provided, else use predefined
        if not gs_id:
            gs_id = '1AVcpYlYTBqepqycOUPp01Aub9NcT2xGfBbdep3x4-W4'
            
        logging.info(gs_id)    
        # logging.info(gs_id)
        # Base url for downloading data from google sheets as csv
        self.input_url  = 'https://docs.google.com/spreadsheets/d/{}/export?format=csv'.format(gs_id)
        # Decalre variables for later use
        self.detail_keys  = []
        # Active product ( being edited at current time)
        self.active = []
        # List of all products to edit
        self.details = []
        self.headers = {
                                'accept': "application/json, text/javascript, */*; q=0.01",
                                'origin': "https://www.mercadopublico.cl",
                                'x-requested-with': "XMLHttpRequest",
                                'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36",
                                'dnt': "1",
                                'content-type': "application/x-www-form-urlencoded",
                                'cache-control': "no-cache",    
                                }
                                

    
    def start_requests(self):
        #Download Google sheets with input data
        url = self.input_url
        yield scrapy.Request(url)
        
        
        
    def parse(self, response):
        #Read Google sheet and create details list from its data.
        sio = io.StringIO( response.text, newline=None) #.encode('ascii','ignore').decode('ascii')
        reader = csv.reader(sio, dialect=csv.excel)
        
        
        for row in reader:
            self.details.append(row)
        self.detail_keys = self.details[0]    
        self.details = self.details[1:]    
        self.active = self.details.pop()
           
        # login here. Then select organization that is supposed to be used
        url = 'https://www.mercadopublico.cl/Home/Autenticacion/NuevoLogin'
        data = {'Rut': self.rut,
                    'contraseña': self.passw,
                    'tipoUsuario': 'nacional',
                    'idPais': '0'}
        body = urlencode(data)   
        yield scrapy.Request(url, method = 'POST', body = body, headers = self.headers, callback = self.parsed)
        
        
        
    def parsed(self, response):
        # inspect_response(response,self)
        data = json.loads(response.text)
        id = data['sessionID']
      
        # Get organization
        url ='https://www.mercadopublico.cl/Home/Autenticacion/ObtenerOrganizaciones'
        
        data = {'rut': self.rut,
                    'pass': self.passw,
                    'session': id,
                    'tipo': 'login',}
                    
        yield scrapy.Request(url, method = 'POST', body = urlencode(data), headers = self.headers, callback = self.select_entity)
    
    def select_entity(self, response):
        # inspect_response(response, self)
        # Getting entity value by entity name
        headers = {
                        'accept': "*/*",
                        'origin': "https://www.mercadopublico.cl",
                        'x-requested-with': "XMLHttpRequest",
                        'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
                        'dnt': "1",
                        'content-type': "application/json; charset=UTF-8",
                        'cache-control': "no-cache",
                    
                    }
        
        entity = self.active[0]
        entity_value = response.xpath("//span[text()[ contains(.,'{}')]]/input/@value".format(entity)).extract_first()
        url = 'https://www.mercadopublico.cl/Home/Autenticacion/LoginPorOrganizacion'
        id = str(response.xpath("//input[@id ='hdSession']/@value").extract_first())
        body = json.dumps({"CodigoEmpresa":entity_value,"sessionId": id})
        yield scrapy.Request(url, method="POST", body = body, callback = self.middle_menu, headers = headers)
        
        
        
        
    def middle_menu(self, response):    
        
        # should click on middle menu
        url = 'http://www.mercadopublico.cl/CMII/Communication/comm.aspx?mode=seller'
        yield scrapy.Request(url, callback = self.convenio_marco)
        
    def convenio_marco(self, response):
        # inspect_response(response, self)
        # Click Administrator on specified agreement
        # Check if agreement description is available
        try:
            agreement_desc = self.active[7]
            url = response.xpath("//div[contains(.//h5,'{}')]".format(agreement_desc))[0].xpath(".//button/@onclick").extract_first()
        # If not agreement description use agreement 
        except:
            agreement = self.active[1]
            url  = response.xpath("//div[contains(.//a,'{}')]".format(agreement))[0].xpath(".//button/@onclick").extract_first()
        
        url = url.split("('")[1][:-2]
        url = urljoin(response.url, url)
        yield scrapy.Request(url, callback = self.administrar)
    
    
    def administrar(self, response):
        # inspect_response(response, self)
        #Click on APlicat Uno Oferta button for OfertaEspecial to get to search bar
        url = response.xpath("//a[contains(@href, 'frmOfertaEspecial')]/@href").extract_first()
        url = urljoin(response.url, url)
        
        i = []
        yield scrapy.Request(url, callback = self.search_bar,  dont_filter = True)
    
    def search_bar(self, response):
        # inspect_response(response, self)
        
        i = self.active
        body = {'__EVENTARGUMENT': '',
                     '__EVENTTARGET': '',
                     '__SCROLLPOSITIONX': '0',
                     '__SCROLLPOSITIONY': '0',
                    
                     'ddlOfertaEspecial': '0',
                     'imgBotonBusca.x': '47',
                     'imgBotonBusca.y': '12',
                     }
        # iterating through the list of items to be changed.
        
        body[ 'txtTextoBuscado'] = i[3]
            
            
        yield scrapy.FormRequest.from_response(response, formdata=body,   callback=self.item_edited ,  dont_filter = True )
        
    def item_edited(self, response):    
        
        i = self.active
        # inspect_response(response, self)  
        
        body = {'CTRL_ListadoOfertasEspeciales1:dgrOfertasEspeciales:_ctl3:imgbtn_Editar.y' : '11',
                    'CTRL_ListadoOfertasEspeciales1:dgrOfertasEspeciales:_ctl3:imgbtn_Editar.x' : '12',
                     '__EVENTARGUMENT': '',
                     '__EVENTTARGET': '',
                     '__SCROLLPOSITIONX': '0',
                     '__SCROLLPOSITIONY': '0',
                     'ddlOfertaEspecial': '0',
                    }
        body['txtTextoBuscado'] = i[3]             
        yield scrapy.FormRequest.from_response(response, formdata=body,   callback=self.item_found,  dont_filter = True)
        
    def item_found(self, response):
        # inspect_response(response, self)  
        cant_modify = response.xpath("//input[contains(@title,'no puede modificarla')]")
        
        i = self.active
        description =i[3]
        # price = str(float(i[1])+1)
        price = i[4]
        startDate = i[5]
        endDate = i[6]
         
        body = {
                     'CTRL_ListadoOfertasEspeciales1:dgrOfertasEspeciales:_ctl3:imgbtn_Guardar.x': '1',
                     'CTRL_ListadoOfertasEspeciales1:dgrOfertasEspeciales:_ctl3:imgbtn_Guardar.y': '1',
                     'CTRL_ListadoOfertasEspeciales1:dgrOfertasEspeciales:_ctl3:txtPrecio_OfEsp': '',
                     '__EVENTARGUMENT': '',
                     '__EVENTTARGET': '',
                     '__SCROLLPOSITIONX': '0',
                     '__SCROLLPOSITIONY': '0',
                     'ddlOfertaEspecial': '0',
                     }
        body['CTRL_ListadoOfertasEspeciales1:dgrOfertasEspeciales:_ctl3:txtPrecio_OfEsp'] = price
        body['CTRL_ListadoOfertasEspeciales1:dgrOfertasEspeciales:_ctl3:CalendarioPopUp1:txtNombre'] = startDate
        body[ 'CTRL_ListadoOfertasEspeciales1:dgrOfertasEspeciales:_ctl3:CalendarioPopUp1:valorID'] = startDate
        body['CTRL_ListadoOfertasEspeciales1:dgrOfertasEspeciales:_ctl3:CalendarioPopUp2:txtNombre'] = endDate
        body['CTRL_ListadoOfertasEspeciales1:dgrOfertasEspeciales:_ctl3:CalendarioPopUp2:valorID'] = endDate
        body['txtTextoBuscado'] =description          
        
        yield scrapy.FormRequest.from_response(response, formdata=body,   callback=self.edit_oferta, dont_filter = True)
        pass
        if cant_modify:
            print('Item cant not be modified')
        
        
        
        
    def edit_oferta(self, response):
        # inspect_response(response, self)
        
        alert = response.xpath("//script[contains(text(), 'alert')]/text()").extract()
        active_old = self.active
        value_to_set = active_old[4]
        key = self.detail_keys
        # logging.info(key)
        logging.info(active_old)
        new_ofert = response.xpath("//td[@class ='ofertasInterior']/span[contains(@id,'Precio')]/text()").extract_first()
        if not alert:
            # try:
                inspect_response(response, self)
                logging.info(active_old[4])
                logging.info(type(active_old[4]))
                logging.info( new_ofert)
                logging.info( type(new_ofert))
                if new_ofert:
                    # remove spaces dots and comas from ofert values to compare them
                    value_to_set = value_to_set.replace('.','').replace(',','').replace(' ','')
                    new_ofert = new_ofert.replace('.','').replace(',','').replace(' ','')
                    if value_to_set in new_ofert:
                        alert = 'OK'
                    elif value_to_set == new_ofert:
                        alert = 'OK'
                    elif value_to_set in new_ofert:
                        alert = 'OK'
                    else: alert = 'ERROR. New Ofert not equal to Expected value'
                else: alert = 'ERROR. No New Offert'
        
        yield { 
                   key[0] : active_old[0],
                   key[1] : active_old[1],
                   key[2] : active_old[2],
                   key[3] : active_old[3],
                   'new_desc' :  response.xpath("//a[contains(@href, 'NombreProducto')]/text()").extract_first(), 
                   key[4] : active_old[4],
                   'new_ofert' : new_ofert,
                   key[5] : active_old[5],
                   'new_date_start' : response.xpath("//td[@class ='ofertasInterior']/span[contains(@id,'Inicio')]/text()").extract_first(),
                   key[6] : active_old[6],
                   'new_date_end' : response.xpath("//td[@class ='ofertasInterior']/span[contains(@id,'Termino')]/text()").extract_first(),
                   'alert' : alert,
                   }
        
        # Check if any products  left to edit
        if self.details:
            
            # Assign new product to active
            self.active = self.details.pop()
            active = self.active
            # Check if entity and agreement are the same for previous and next item.
            if active_old[0] == active[0] and active_old[1] == active[1]:
                
                body = {'__EVENTARGUMENT': '',
                             '__EVENTTARGET': '',
                             '__SCROLLPOSITIONX': '0',
                             '__SCROLLPOSITIONY': '0',
                            
                             'ddlOfertaEspecial': '0',
                             'imgBotonBusca.x': '47',
                             'imgBotonBusca.y': '12',
                             }
                # iterating through the list of items to be changed.
                
                body[ 'txtTextoBuscado'] = active[3]
                    
                    
                yield scrapy.FormRequest.from_response(response, formdata=body,   callback=self.item_edited , dont_filter = True )
            # Check if entity is different but  agreement is  the same for previous and next item.
            elif active_old[0] != active[0]:
                
                cookie = str(response.request.headers['Cookie']).split('; ')
                id = [i.split('=')[-1] for i in cookie if 'ASP.NET_SessionId=' in i][0]
      
                # Get organization
                url ='https://www.mercadopublico.cl/Home/Autenticacion/ObtenerOrganizaciones'
                
                data = {'rut': self.rut,
                            'pass': self.passw,
                            'session': id,
                            'tipo': 'login',}
                            
                yield scrapy.Request(url, method = 'POST', body = urlencode(data), headers = self.headers, callback = self.select_entity)
            else:   
                url = 'http://www.mercadopublico.cl/CMII/Communication/comm.aspx?mode=seller'
                yield scrapy.Request(url, callback = self.convenio_marco)