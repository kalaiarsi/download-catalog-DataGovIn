from selenium import webdriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from time import sleep
from selenium.webdriver.common.keys import Keys
import os
import logging
import sys
import requests
from pyvirtualdisplay import Display

logging.basicConfig(filename="catalog_download.log", level=logging.INFO, filemode="w")
MAX_DOWNLOAD_COUNT=10
# For popup user details on data.gov.in
SITE_USERNAME="python dummyuser"
SITE_USEREMAIL="pythonuser.example.user@gmail.com"
# Time for the browser to Load an url, to Wait.
TIME_LOAD=5
TIME_WAIT=2

def popup(browser):
	sleep(TIME_LOAD)
	browser.find_element_by_xpath("/html/body/div[1]/div[1]/div/div[7]/div/div[2]/section/div/div/div/div/div/article/div/div/div[2]/div/div/div/div[2]/div[2]/div[2]/form/div/div[4]/div/div[2]/label").click()
	sleep(TIME_WAIT)
	browser.find_element_by_xpath("/html/body/div[1]/div[1]/div/div[7]/div/div[2]/section/div/div/div/div/div/article/div/div/div[2]/div/div/div/div[2]/div[2]/div[2]/form/div/div[5]/div/div[2]/label").click()
	name=browser.find_element_by_id("edit-name-d")
	name.send_keys(SITE_USERNAME)
	email=browser.find_element_by_id("edit-mail-d")
	email.send_keys(SITE_USEREMAIL)
	browser.find_element_by_id("edit-submit").click()


def set_profile(profile,catalogname):
	os.makedirs(catalogname, exist_ok=True)
	profile.set_preference("browser.download.folderList", 2)
	profile.set_preference("browser.download.manager.showWhenStarting", False)
	profile.set_preference("browser.download.panel.shown", False)
	profile.set_preference("browser.download.dir", os.path.join(os.getcwd(),catalogname))
	profile.set_preference("browser.helperApps.neverAsk.openFile","application/xml,text/xml,application/csv,text/csv,application/json,application/jsonp,application/octet-stream")
	profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/xml,text/xml,application/csv,text/csv,application/json,application/jsonp,application/octet-stream")



def extract_filetype(browser,main_window,resource_window,filetype):
	try:
		ft=browser.find_elements_by_link_text(filetype)[0]
		ft.click()
		sleep(TIME_WAIT)
		popup(browser)
		sleep(TIME_LOAD)
		browser.close()
		logging.info("closed resource browser")
		browser.switch_to.window(browser.window_handles[1])
		browser.close()
		browser.switch_to.window(browser.window_handles[0])
	except:
		logging.error("No link found for data download. Terminating")
		#sys.exit(-1)

def setup_browser(catalogname,catalog_url):
	profile = FirefoxProfile()
	set_profile(profile,catalogname)
	browser=webdriver.Firefox(firefox_profile=profile)
	return browser	

def all_links(browser):
	num_resources=int(browser.find_element_by_class_name("view-header").text.split(' ')[0])
	logging.info("total number of available resources:%s"%str(num_resources))
	print("total number of available resources:%s"%str(num_resources))
	filetypes=[];links=[];
	elem=browser.find_element_by_class_name("download-confirmation-box")#centre box
	filetypes.append(elem.text)
	links.append(elem.find_element_by_tag_name("a").get_attribute("href"))
	try:
		elem=browser.find_element_by_class_name("data-export-cont")
		for l in elem.find_elements_by_tag_name("li"):#to find types
			filetypes.append(l.find_element_by_tag_name("a").get_attribute("title"))
			links.append(l.find_element_by_tag_name("a").get_attribute("href"))
	except NoSuchElementException:
		logging.info("No Export Links available")
	finally:
		print("available filetypes",filetypes)
		logging.info("available filetypes:%s"%str(filetypes))
		logging.info("sample links:%s"%str(links))
		return filetypes, links

def open_central_link(browser,filetype,download_count):
	main_window=browser
	elems=browser.find_elements_by_class_name("download-confirmation-box")
	for elem in elems:
		download_count+=1
		if download_count>MAX_DOWNLOAD_COUNT:
			return MAX_DOWNLOAD_COUNT
		el=elem.find_element_by_tag_name("a")
		url=el.get_attribute("href")
		if url:
			print("opening url:",url)
			logging.info("opening url:%s"%url)
			browser.execute_script('window.open(arguments[0]);', url)
			resource_window=browser.window_handles[1]
			main_window=browser.window_handles[0]
			sleep(TIME_LOAD)
			browser.switch_to.window(resource_window)
			sleep(TIME_WAIT)
			extract_filetype(browser,main_window,resource_window,filetype)
	return len(elems)

def open_export_link(browser,filetype,download_count,catalogname):
	elems=browser.find_elements_by_class_name("data-export-cont")
	for elem in elems:
		download_count+=1
		if download_count>MAX_DOWNLOAD_COUNT:
			return MAX_DOWNLOAD_COUNT
		el=elem.find_element_by_class_name(filetype)
		url=el.get_attribute("href")
		print("opening url:",url)
		logging.info("opening url:%s"%url)
		response = requests.get(url).text
		[_,_,_,p1,p2,_,_,p3]=url.split('/');filename=p1+'_'+p2+'.'+p3
		#os.makedirs(catalogname, exist_ok=True)
		with open(os.path.join(os.getcwd(),catalogname,filename),"w") as fh:
			fh.write(response)
	return len(elems)
	
def get_data(catalogname,catalog_url,filetype):
	catalogname=catalog_url.split('/')[-1]
	display = Display(visible=0, size=(800, 600))
	display.start()
	browser=setup_browser(catalogname,catalog_url)
	#browser.set_window_position(-3000, 0) # browser.set_window_position(0, 0) to get it back
	catalog_url=catalog_url+"?title=&file_short_format=&page=0"
	browser.get(catalog_url)
	sleep(TIME_LOAD)
	filetypes,links=all_links(browser)
	if not filetype in filetypes:
		print("Filetype unavaible in this catalog. choose from available filetypes: ", filetypes)
		logging.error("Filetype unavaible in this catalog. choose from available filetypes: %s"%str(filetypes))
		#sys.exit(-1)
	download_count=0
	while True:# to scan for multiple pages
		if filetypes.index(filetype)==0:#central page link, opens in new window
			download_count=open_central_link(browser,filetype,download_count)
		else: #node link, no need of new window
			download_count=open_export_link(browser,filetype,download_count,catalogname)
		if download_count>=MAX_DOWNLOAD_COUNT:
			logging.info("Max download limit of %s reached"%str(MAX_DOWNLOAD_COUNT))
			break
		try:
			if browser.find_element_by_class_name("pager-next"):
				pagenum=int(catalog_url.split('=')[-1])+1#starts from 0 for first page
				catalog_url='='.join(catalog_url.split('=')[:-1]+[str(pagenum)])
				request = requests.get(catalog_url)
				if request.status_code == 200:
					logging.info('next page exists')
					browser.get(catalog_url)
		except:
			logging.info('no more pages')
			break
	browser.close()
	print("Downloaded",download_count," files")
	logging.info("Downloaded %s files "% download_count)
	display.stop()
	print("done")


def get_catalog_name_url(catalog):
	if "https://data.gov.in/catalog/" in catalog:
		catalog_url=catalog
		catalogname=catalog_url.split('/')[-1]
	else:
		catalog_url="https://data.gov.in/catalog/"+catalog
		catalogname=catalog
	request = requests.get(catalog_url)
	if request.status_code == 200:
		logging.info('catalog exists')
		return catalogname,catalog_url
	else:
		logging.error('catalog doesnt exist')
		return

def check_input():
	if len(sys.argv)!=3:
		print("CLI usage python downloadcatalog.py central-government-health-scheme csv	or		python downloadcatalog.py https://data.gov.in/catalog/central-government-health-scheme xml")
		#sys.exit(-1)

def check_catalog_name(catalog_name_or_url):
	try:
		catalogname,catalog_url=get_catalog_name_url(catalog_name_or_url)
		print("Downloading catalog:",catalogname)
		logging.info("Downloading catalog:%s" % catalogname)
		return catalogname,catalog_url
	except:
		print("Error in finding catalog!")
		logging.error("Error in finding catalog. You entered : %s"% catalog_name_or_url)
		#sys.exit(-1)

def download_catalog(catalog_name_or_url, filetype_to_download):
	logging.info("Inputs validated. Starting to scrap the catalog")
	catalogname,catalog_url=check_catalog_name(catalog_name_or_url)
	get_data(catalogname,catalog_url,filetype_to_download)
	#sys.exit(0)

if __name__=="__main__":
	check_input()
	download_catalog(sys.argv[1],sys.argv[2])

