import json
from multiprocessing import Pool
import multiprocessing
import socket
from sklearn.utils import shuffle
import pandas as pd
from utils import getIpGeo, getPeerCert, parseCertObject, getIp
from RainbowPrint import RainbowPrint as rp
import time
import os
import urllib
import hashlib
from selenium import webdriver
from tables import Sites, db
import config

def fetchSiteBatch(urlBatch):
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(f'--window-size=1920,1080')
    options.add_argument('--log-level=3')
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-blink-features")
    options.add_argument("--disable-blink-features=AutomationControlled")
    if config.HEADLESS:
        options.add_argument('--headless')
    browser = webdriver.Chrome(options=options)
    browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
            })
        """
    })
    browser.set_page_load_timeout(config.PAGE_TIMEOUT)
    socket.setdefaulttimeout(config.TCP_TIMEOUT)
    siteList = []
    rp.info(f"Fetching {len(urlBatch)} sites")
    for site in urlBatch:
        url = site['url']
        domainName = urllib.parse.urlparse(url).hostname

        if any(char.isalpha() for char in domainName):
            if not getIp(domainName):
                rp.info(f"DNS Failed, Skip: {url}")
                continue

        if db.query(Sites).filter(Sites.domain == domainName).first():
            rp.info(f"Skipping: {url}")
            continue

        siteType = site['type']
        startTime = time.time()
        rp.info(f"Fetching: {url}")
        try:
            valid = True
            browser.get(url)
            browser.execute_script("window.alert = function() {};")
        except Exception as e:
            errorMessage = str(e).splitlines()[0]
            if errorMessage.find("Timed out receiving message from renderer") != -1:
                rp.debug(f"Fetch Timeout: {url} - {errorMessage}")
                browser.execute_script('window.stop()')
            else:
                rp.error(f"Fetch Failed: {url} - {errorMessage}")
                valid = False

        sign = hashlib.md5(browser.current_url.encode('utf-8')).hexdigest()
        protocol = browser.execute_script(
            "return window.location.protocol").replace(":", "")
        title = browser.execute_script("return document.title")
        hostname = urllib.parse.urlparse(browser.current_url).hostname
        ipaddr = None
        port = urllib.parse.urlparse(browser.current_url).port
        if not port:
            port = 443 if protocol == "https" else 80
        # status_code = None
        site_type = siteType
        cert = None
        subject = None
        issuer = None
        certJson = None
        certVersion = None
        cert_not_before = None
        cert_not_after = None
        cert_subject_country = None
        cert_subject_stateOrProvinceName = None
        cert_subject_localityName = None
        cert_subject_organization = None
        cert_subject_common_name = None
        cert_issuer_country = None
        cert_issuer_organization = None
        cert_issuer_common_name = None
        country = None
        city = None
        asn = None

        # get ipaddr
        try:
            ipaddr = socket.gethostbyname(hostname)
        except Exception as e:
            rp.error(f"GetIP Failed for: {hostname}")

        # get status code
        # for request in browser.requests:
        #     if request.response:
        #         if request.host == hostname:
        #             status_code = request.response.status_code
        #             break

        # get cert
        rp.debug(f"GetCert: {hostname}")
        if ipaddr:
            cert = getPeerCert(hostname)
        if ipaddr and not cert:
            rp.error(f"GetCert Failed for: {hostname}")
        else:
            certJson = json.loads(json.dumps(cert))
            if certJson:
                subject = parseCertObject(
                    certJson['subject']) if 'subject' in certJson else None
                issuer = parseCertObject(
                    certJson['issuer']) if 'issuer' in certJson else None
                certVersion = certJson['version'] if 'version' in certJson else None
                cert_not_before = time.strptime(
                    certJson['notBefore'], "%b %d %H:%M:%S %Y %Z") if 'notBefore' in certJson else None
                cert_not_after = time.strptime(
                    certJson['notAfter'], "%b %d %H:%M:%S %Y %Z") if 'notAfter' in certJson else None
            if subject:
                cert_subject_country = subject.get('countryName')
                cert_subject_stateOrProvinceName = subject.get(
                    'stateOrProvinceName')
                cert_subject_localityName = subject.get('localityName')
                cert_subject_organization = subject.get('organizationName')
                cert_subject_common_name = subject.get('commonName')
            if issuer:
                cert_issuer_country = issuer.get('countryName')
                cert_issuer_organization = issuer.get('organizationName')
                cert_issuer_common_name = issuer.get('commonName')

        # get geo
        if ipaddr:
            rp.debug(f"GetGeo: {hostname} - {ipaddr}")
            geo = getIpGeo(ipaddr)
            if not geo:
                rp.error(f"GetGeo Failed for: {hostname} - {ipaddr}")
            else:
                country = geo['country']
                city = geo['city']
                asn = geo['asn']

        # save to db
        site = Sites(
            domain=hostname,
            valid=valid,
            # status_code=status_code,
            title=title,
            ip=ipaddr,
            port=port,
            site_type=site_type,
            country=country,
            city=city,
            asn=asn,
            sign=sign,
            protocol=protocol,
            cert=json.dumps(cert) if cert else None,
            cert_version=certVersion,
            cert_subject_country=cert_subject_country,
            cert_subject_stateOrProvinceName=cert_subject_stateOrProvinceName,
            cert_subject_localityName=cert_subject_localityName,
            cert_subject_organization=cert_subject_organization,
            cert_subject_common_name=cert_subject_common_name,
            cert_issuer_country=cert_issuer_country,
            cert_issuer_organization=cert_issuer_organization,
            cert_issuer_common_name=cert_issuer_common_name,
            cert_not_before=cert_not_before,
            cert_not_after=cert_not_after
        )
        if hostname and not protocol == "chrome-error":
            siteList.append(site)

        with open(f"pages/{hostname}.html", "w", encoding="utf-8") as f:
            f.write(browser.page_source)

        if config.SCREENSHOT:
            browser.save_screenshot(f"screenshots/{hostname}.png")

        rp.debug(f"TimeCost: {url} - {round(time.time() - startTime, 2)}s")

        browser.quit()
        if len(siteList) >= config.SQL_BATCH_SIZE:
            try:
                db.add_all(siteList)
                db.commit()
                siteList = []
            except Exception as e:
                rp.error(f"SQL Failed: {e}")
    try:
        db.add_all(siteList)
        db.commit()
    except Exception as e:
        rp.error(f"SQL Failed: {e}")


if __name__ == '__main__':
    if not os.path.isdir("screenshots"):
        os.mkdir("screenshots")
    if not os.path.isdir("pages"):
        os.mkdir("pages")
    print("Loading data...")
    sitesFile = pd.read_csv("./data/train1_0.csv")
    print("Shuffling data...")
    sitesFile = shuffle(sitesFile)
    urlBatch = []
    for i in range(0, len(sitesFile), config.BATCH_SIZE):
        for j in range(i, i + config.BATCH_SIZE):
            if j < len(sitesFile):
                urlBatch.append({
                    "url": sitesFile.iloc[j][0] if sitesFile.iloc[j][0].startswith("http://") or sitesFile.iloc[j][0].startswith("https://") else "http://" + sitesFile.iloc[j][0],
                    "type": sitesFile.iloc[j][1],
                })
        if len(urlBatch) > 0:
            print(f"Process: {i}/{len(sitesFile)}")
            p = multiprocessing.Process(
                target=fetchSiteBatch, args=(urlBatch,))
            p.start()
            urlBatch = []
            time.sleep(1)
            while len(multiprocessing.active_children()) >= config.MAX_PROCESS:
                time.sleep(1)
