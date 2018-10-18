import requests
from bs4 import BeautifulSoup as bs
import logging
import http.client
import time
from random import randint
import json
from proxymanager import ProxyManager
from fake_useragent import UserAgent
import jsbeautifier
import datetime

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
#from subprocess import Popen, PIPE

print("==============================")
print(datetime.datetime.now())


me = "xxxxxxxxxxxxxxx@email.com"
you = "xxxxxxxxxxxxxxx@email.com"

# Create message container - the correct MIME type is multipart/alternative.
msg = MIMEMultipart('alternative')
msg['Subject'] = "PSNY"
msg['From'] = me
msg['To'] = you


ua = UserAgent()
proxy_manager = ProxyManager('proxies.txt')




with open('monitor_config.json') as json_data_file:
	config = json.load(json_data_file)

def get_sizes_from_stockx(stockx_link):
	desired_sizes = []
	stockx_notification = []	
	random_proxy = proxy_manager.random_proxy()
	proxies = random_proxy.get_dict()
	#print(proxies)
	session = requests.Session()
	session.headers = {'User-Agent': ua.random}
	print(ua.random)	
	stockx_response = session.get(stockx_link, proxies=proxies)	
	#stockx_response = session.get(stockx_link)
	#print(stockx_response.text)
	stockx_soup = bs(stockx_response.text, 'lxml')
	print(stockx_response.status_code)
	windowPreloaded = False
	#print(stockx_soup.findAll('script', {"type": "text/javascript"}))
	for stockx_script in stockx_soup.findAll('script', {"type": "text/javascript"}):
		#print(stockx_script)
#		with open('stockx_script.json', 'a') as f:
#			f.write(stockx_script)
		if 'window.preLoaded' in stockx_script.text:
			#print(stockx_script)
			windowPreloaded = True
			response_text_tmp = stockx_script.text.replace("window.preLoaded =", "")
			response_text = response_text_tmp.replace(";", "")
			data = json.loads(response_text)
		#	print(data)
			#with open('stockx_response.json', 'w') as f:
			#	f.write(data)
			title = data['product']['name']
			style_id = data['product']['styleId']
			retailPrice = data['product']['retailPrice']
			taxedRetail = round(retailPrice * 1.07, 2)
			print("{} {} retail price is ${} while taxed price is ${}".format(title, style_id, retailPrice, taxedRetail))
			data_children = data['product']['children']
			for child in data_children.keys():
				bid_size = data_children[child]['market']['highestBidSize']
				highest_bid = data_children[child]['market']['highestBid']
				resell_gain = round(highest_bid * 0.88, 2)
				if bid_size and (resell_gain > taxedRetail):
					desired_sizes.append(bid_size)
					resell_profit = round(resell_gain - taxedRetail, 2)
					print("Size {} highest bid is ${} while resell gain is ${} and resell profit is {}".format(bid_size, highest_bid, resell_gain, resell_profit))	
	if not windowPreloaded:
		desired_sizes.append('all')
		print('window.Preloaded not found')
		stockx_notification.append('window.Preloaded not found')
	return desired_sizes, stockx_notification
		
	
def get_sizes_in_stock(product_link, desired_sizes):
	
	print(desired_sizes)
	
	random_proxy = proxy_manager.random_proxy()
	proxies = random_proxy.get_dict()
	#print(proxies)
	session = requests.Session()
	session.headers = {'User-Agent': ua.random}
	print(ua.random)	
	product_response = session.get(product_link + '.js', proxies=proxies)	
	#product_response = session.get(product_link + '.js')
	prettyjson = jsbeautifier.beautify(product_response.text)
	with open('product_response.json', 'w') as f:
		f.write(prettyjson)
	print(product_response.status_code)
	
	product_data = json.loads(prettyjson)
	#print(data)
	
	sizes_in_stock = []

	if ('all' in desired_sizes) or ('All' in desired_sizes):	
		if product_data['available']:
			for size in product_data['variants']:
				if size['available']:
					sizes_in_stock.append(size['option1'])
	else:
		if product_data['available']:
			for size in product_data['variants']:
				if size['available'] and (size['option1'] in desired_sizes):
					sizes_in_stock.append(size['option1'])
	available_sizes = ' '.join(sizes_in_stock)		
	return available_sizes

sizes_notification = []

for item in config.keys():
	print(item)
	desired_sizes, stockx_notification = get_sizes_from_stockx(config[item]['stockx_link'])
	available_sizes = get_sizes_in_stock(config[item]['product_link'], desired_sizes)
	print(available_sizes)
	if available_sizes:
		sizes_notification.append(item + " -- " + available_sizes + "\n" + config[item]['product_link'])
		sizes_notification.extend(stockx_notification)

print("Email contents: {}".format(sizes_notification))

if sizes_notification:
	part1 = MIMEText('\n'.join(sizes_notification))
	# Attach parts into message container.
	# According to RFC 2046, the last part of a multipart message, in this case
	# the HTML message, is best and preferred.
	msg.attach(part1)
	
	# Send the message via local SMTP server.
	s = smtplib.SMTP('localhost')
	# sendmail function takes 3 arguments: sender's address, recipient's address
	# and message to send - here it is sent as one string.
	s.sendmail(me, you, msg.as_string())
	s.quit()	
