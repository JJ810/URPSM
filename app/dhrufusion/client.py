from __future__ import absolute_import
import decimal
# import StringIO
# import sys
import re
# import decimal
import requests
from bs4 import BeautifulSoup
import json
from xml.dom.minidom import Document
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _


class Client(object):
    _requestformat = 'json'
    # _blacklist = [
    #     'servcie worldiwd iphone all device 1-3days maximum time stable working',
    #     '3g,3s,4g,4s,5g,5s,5c premium service',
    #     'IPHONE 3g/3gs/4/4s/5/5c/5s/6/6p not found',
    #     'APAC All iPhone 3G/3GS/4/4S/5 (Blacklisted / Stolen)',
    #     'icloud remove service',
    #     'remove icloud service',
    #     'blacklisted / stolen',
    #     'IPHONE premium',
    #     'blocked imei',
    # ]

    def __init__(self, username=None, apiaccesskey=None, dhrufusion_url=None):
        if not username or not apiaccesskey or not dhrufusion_url:
            raise AttributeError(
                u'Missing username, api access key or dhrufusion_url')
        self.username = username
        self.apiaccesskey = apiaccesskey
        self.dhrufusion_url = dhrufusion_url + '/api/index.php' if not dhrufusion_url.endswith(
            '/') else dhrufusion_url.strip('/') + '/api/index.php'

    def action(self, action=None, parameters=None):
        _postdata = {
            'username': self.username,
            'apiaccesskey': self.apiaccesskey,
            'action': action,
            'requestformat': self._requestformat
        }
        if parameters:
            _postdata.update({'parameters': parameters})
            
        # temporary proxy
        # socks = {'socks4': '127.0.0.1:9000'}
        r = requests.post(self.dhrufusion_url, data=_postdata)
        return r.content.lower().strip()

    def get_country_code(self, country_name=None):
        r = self.action(action='providerlist')
        dom = self.get_response(r)
        res = dom.list.findChildren(recursive=False)
        for rs in res:
            if rs.findNext('name').text == str(country_name).lower():
                return rs.findNext('name').findNext('id').text

    def status(self):
        try:
            r = self.action(action='accountinfo')
            print r
            dom = self.get_response(r)
            if dom.message.text == 'invalid ip request' or dom.message.text == 'authentication failed':
                return False
            return True
        except: return False

    def get_credit(self):
        r = self.action(action='accountinfo')
        dom = self.get_response(r)
        # return dom
        info = {
            'email': dom.mail.text,
            'credit': self.exchange(amount=re.sub('[^0123456789\.]', '', dom.credit.text)),
            'currency': dom.currency.text
        }
        try:
            if float(info['credit']) < 200:
                user = User.objects.get(username=self.username)
                users = User.objects.fitler(profile__server=user.profile.server)
                msg = _('your credit is {0} you need to provision your credit as soon as possible')
                msg = msg.format(info['credit'])
                for user in users:
                    user.profile.notify_server_by_admin(user.profile.server,msg)
        except Exception as e:
            print e

        return json.dumps(info)

    def get_account_currency(self):
        r = self.action(action='accountinfo')
        dom = self.get_response(r)
        return dom.currency.text

    def get_imei_service_list(self):
        r = self.action(action='imeiservicelist')
        dom = self.get_response(r)
        res = dom.list.findChildren(recursive=False)
        services = {}
        for rs in res:
            result = []
            for r in rs.services.findChildren(recursive=False):
                result.append((r.findNext('serviceid').text,
                               "{} - {}  {}".format(
                    r.findNext('servicename').text,
                    r.findNext('credit').text, r.findNext('time').text),))
            services[rs.findNext('groupname').text] = tuple(result)
        return json.dumps(services)

    def get_network_list(self, for_search=False):
        r = self.action(action='imeiservicelist')
        dom = self.get_response(r)
        res = dom.list.findChildren(recursive=False)
        networks = []
        for rs in res:
            networks.append((rs.findNext('groupname').text,
                             rs.findNext('groupname').text))
        if for_search:
            return networks
        return json.dumps(tuple(networks))

    def get_services_list(self, network, for_search=False):
        r = self.action(action='imeiservicelist')
        dom = self.get_response(r)
        res = dom.list.findChildren(recursive=False)
        services = {}
        for rs in res:
            if rs.findNext('groupname').text.strip() == network:
                for r in rs.services.findChildren(recursive=False):
                    services[r.serviceid.text + ':' +
                             r.servicename.text] = r.servicename.text
        if for_search:
            return services
        return json.dumps(services)

    def get_provider_list(self, id=None):
        r = self.action(action='providerlist',
                        parameters=self._create_xml_params({'ID': str(id)}))
        dom = self.get_response(r)
        return dom

    def _create_xml_params(self, params):
        doc = Document()
        base = doc.createElement('PARAMETERS')
        doc.appendChild(base)
        for p in params:
            entry = doc.createElement(p)
            value = doc.createTextNode(params[p])
            entry.appendChild(value)
            base.appendChild(entry)
        return doc.toxml(encoding='utf-8')

    def get_mep_list(self):
        dom = self.get_response(self.action(action='meplist'))
        res = dom.list.findChildren(recursive=False)
        meps = {}
        for rs in res:
            meps[rs.findNext('id').text] = rs.findNext('name').text
        return json.dumps(meps)

    def get_model_list(self, id=None):
        r = self.action(action='modellist',
                        parameters=self._create_xml_params({'ID': str(id)}))
        dom = self.get_response(r)
        return dom

    def get_response(self, r=None, parse=False):
        if parse:
            dom = BeautifulSoup(r, parse)
        else:
            dom = BeautifulSoup(r)
        return dom

    # def get_imei_order(self, id=None):
    #     r = self.action(action='getimeiservicedetails',
    #                     parameters=self._create_xml_params({'ID': '194'}))

    #     dom = self.get_response(r)

    #     return dom

    def get_imei_service_details(self, id=None):
        r = self.action(action='getimeiservicedetails',
                        parameters=self._create_xml_params({'ID': str(id)}))
        dom = self.get_response(r)
        print "get_imei_service_details: response dom(): ", dom
        # return dom
        service = {}
        # res = dom.result.findChildren(recursive=False)
        # for r in res:
        if dom.list.credit:
            service['credit'] = self.exchange(amount=dom.list.credit.text)
        if dom.list.time:
            service['time'] = dom.list.time.text
        else :
            import datetime
            service['time'] = str(datetime.datetime.now())
        if dom.list.model:
            service['model'] = dom.list.model.text
        if dom.list.provider:
            service['provider'] = dom.list.provider.text
        if dom.list.mep:
            service['mep'] = dom.list.mep.text
        # service['sn'] = dom.list.sn.text
        if dom.list.pin:
            service['pin'] = dom.list.pin.text
        if dom.list.kbh:
            service['kbh'] = dom.list.kbh.text
        if dom.list.prd:
            service['prd'] = dom.list.prd.text
        if dom.list.type:
            service['type'] = dom.list.type.text
        if dom.list.reference:
            service['reference'] = dom.list.reference.text
        if dom.list.locks:
            service['locks'] = dom.list.locks.text
        print "service object: ",service
        return json.dumps(service)

    def place_imei_order(self, id, imei):
        r = self.action(action='placeimeiorder',
                        parameters=self._create_xml_params({
                            'ID': str(id),
                            'IMEI': imei
                        }))
        dom = self.get_response(r)
        # return dom
        order = {}
        if dom.referenceid:
            order = {
                'referenceid': dom.referenceid.text,
                'message': dom.message.text
            }
        return json.dumps(order)

    def get_imei_order(self, id):
        r = self.action(action='getimeiorder',
                        parameters=self._create_xml_params({'ID': str(id)}))

        dom = self.get_response(r)
        order = {
            'id': dom.id.text,
            'imei': dom.imei.text,
            'status': dom.status.text,
            'code': dom.code.text,
        }
        return json.dumps(order)

    def exchange(self, amount=0):
        currency = self.get_account_currency()
        print "current currency in DHRU :", currency
        amount = decimal.Decimal(amount)
        url = "http://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20yahoo.finance.xchange%20where%20pair%20in%20%28%22{}USD%22%29&env=store://datatables.org/alltableswithkeys".format(
            currency)
        print "url for exchange rate : ", url
        r = requests.get(url).content.lower().strip()
        dom = BeautifulSoup(r, 'xml')
        return str(round(decimal.Decimal(dom.rate.rate.text) * amount, 2))

# c = Client(username='esoufien4', apiaccesskey='XB6-VVU-XHS-L3B-LJ6-44C-UK6-WU4',
#            dhrufusion_url='http://www.supportunlock.com')

# print c.get_country_code('morocco')
# print c.get_credit()
# print c.get_imei_service_list()
# print c.get_provider_list(id=2606)
# print c.get_mep_list()


# print c.get_model_list(id=82)

# services = json.loads(c.get_imei_service_list())

# for i in services:
#     for k in services[i]:
#         print c.get_provider_list(k[0])

# print c.get_model_list(id=1337)

# print c.get_imei_order()

# print c.get_imei_service_details(id=2228)

# 194-mep, 185-prd, 176-model

# print c.place_imei_order(id=194, imei='359652052115453')

# print c.get_imei_order(id=502)

# print c.get_network_list()

# login  : esoufien4
# pass : SIIAKDM2

# print c.get_services_list(network='blackberry unlock')
# place an order method
# get order details method
# credit conversion in service detail

# testing with blackberry
# creating the forms to place orders
# working with the balance when an order has been placed
# working with smart select and ajaxify the forms
# orders list and checking orders status by refreshing the page
#

# print c.status()


# exchange(currency='MAD')