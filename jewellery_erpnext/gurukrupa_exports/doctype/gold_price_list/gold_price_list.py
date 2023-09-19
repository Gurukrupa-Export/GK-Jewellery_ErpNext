
from datetime import datetime
import frappe,requests,pandas as pd
from frappe.model.document import Document

class GoldPriceList(Document):
	pass


@frappe.whitelist()
def get_gold_price():
	data_list = []
	url = frappe.db.get_value('Gold Price Scrape Settings','Gold Price Scrape Settings','api_url')
	session = requests.Session()
	response = session.get(url).json()
	
	current_date = datetime.now()
	formatted_date = current_date.strftime("%b %d, %Y")

	for data in response:
		if data == formatted_date:
			
			last_open = response[data]['last_open']
			last_close = response[data]['last_close']
			last_max = response[data]['last_max']
			last_min = response[data]['last_min']
			data_list.append([data,last_open,last_close,last_max,last_min])
	
	df = pd.DataFrame(data_list,columns=['date','last_open','last_close','last_max','last_min'])
	# # Set the span for EMA calculation
	span = 20
	# # Calculate the multiplier
	multiplier = 2 / (span + 1)
	# # Calculate EMA
	df['EMA'] = df['last_close'].ewm(span=span, adjust=False).mean()
	# # span = 20
	# # multiplier = 2 / (span + 1)
	# df['SMA'] = df['last_close'].rolling(window=span, min_periods=span).mean()
	# df.loc[span:, 'EMA'] = df.loc[span - 1, 'SMA'] + (df.loc[span:, 'last_close'] - df.loc[span - 1, 'SMA']) * multiplier
	# df['EMA'].ffill(inplace=True)
	df2= df[['date','last_close','EMA']]
	# # latest_ema_rate = df2.loc[0]['EMA']
	rate_in_ounce = round(df2.loc[0]['EMA']+100,2)
	rate_in_gram = rate_in_ounce/31.10348
	
	# cr = CurrencyConverter()
	# # inr_rate_in_ounce = round(cr.convert(rate_in_ounce, 'USD', 'INR'),2)

	usd_kt_24 = round(rate_in_gram,2)
	# inr_kt_24 = round(cr.convert(usd_kt_24, 'USD', 'INR'),2)

	usd_kt_22 = round(float((rate_in_gram)*22)/24,2)
	# inr_kt_22 = round(cr.convert(usd_kt_22, 'USD', 'INR'),2)

	usd_kt_18 = round((float(rate_in_gram)*18)/24,2)
	# inr_kt_18 = round(cr.convert(usd_kt_18, 'USD', 'INR'),2)

	usd_kt_14 = round((float(rate_in_gram)*14)/24,2)
	# inr_kt_14 = round(cr.convert(usd_kt_14, 'USD', 'INR'),2)

	usd_kt_10 = round((float(rate_in_gram)*10)/24,2)
	# inr_kt_10 = round(cr.convert(usd_kt_10, 'USD', 'INR'),2)

	kt_list = [['24KT','99.9',usd_kt_24],['22KT','91.7',usd_kt_22],['18KT','75.6',usd_kt_18],['14KT','59.0',usd_kt_14],['10KT','42.0',usd_kt_10]]

	
	return kt_list,rate_in_gram

	