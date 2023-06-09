import json
import ssl
import socket
import random
import geoip2.database
from RainbowPrint import RainbowPrint as rp
import dns.resolver

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)

def getPeerCert(domain, port=443, timeout=5):
    try:
        conn = ssl.create_connection((domain, 443))
        conn.settimeout(timeout)
        ctx = ssl.create_default_context()
        conn = ctx.wrap_socket(conn, server_hostname=domain)
        cert = conn.getpeercert()
        return cert
    except Exception as e:
        return False


geoipCityReader = geoip2.database.Reader('./data/GeoLite2-City.mmdb')
geoipASNReader = geoip2.database.Reader('./data/GeoLite2-ASN.mmdb')
geoipCountryReader = geoip2.database.Reader('./data/GeoLite2-Country.mmdb')


def getIpGeo(ip):
    try:
        city = geoipCityReader.city(ip)
        asn = geoipASNReader.asn(ip)
        return {
            'country': city.country.iso_code,
            'city': city.city.name,
            'asn': asn.autonomous_system_organization
        }
    except Exception as e:
        return False


def parseCertObject(obj):
    result = {}
    for sub_list in obj:
        for pair in sub_list:
            result[pair[0]] = pair[1]
    return result

dnsServerList = ['8.8.8.8', '114.114.114.114', '223.5.5.5', '180.76.76.76', '119.29.29.29']

def getIp(domain):
    try:
        dns.resolver.default_resolver.nameservers = [random.choice(dnsServerList)]
        resp = dns.resolver.resolve(domain).response.answer[0][0]
        return resp
    except Exception as e:
        print(e)
        return None