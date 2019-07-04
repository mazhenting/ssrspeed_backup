#coding:utf-8

import logging
import copy
import time

logger = logging.getLogger("Sub")

from SSRSpeed.SpeedTest.Methods.SpeedTestMethods import SpeedTest
from SSRSpeed.Utils.IPGeo import domain2ip, IPLoc

class SpeedTestCore(object):
	def __init__(self,parser,client,method = "SOCKET"):
		self.__parser = parser
		self.__client = client
		self.__testMethod = method
		self.__results = []
		self.__current = {}
		self.__baseResult = {
			"group": "N/A",
			"remarks": "N/A",
			"loss": 1,
			"ping": -1,
			"gPingLoss": 1,
			"gPing": 0,
			"dspeed": -1,
			"maxDSpeed": -1,
			"trafficUsed": 0,
			"geoIP":{
				"inbound":{
					"address": "N/A",
					"info": "N/A"
				},
				"outbound":{
					"address": "N/A",
					"info": "N/A"
				}
			},
			"rawSocketSpeed": [],
			"rawTcpPingStatus": [],
			"rawGooglePingStatus": []
		}

	def __getBaseResult(self):
		return copy.deepcopy(self.__baseResult)

	def resetStatus(self):
		self.__results = []
		self.__current = {}

	def getResult(self):
		return self.__results
	
	def getCurrent(self):
		return self.__current

	def __geoIPInbound(self,config):
		inboundIP = domain2ip(config["server"])
		inboundInfo = IPLoc(inboundIP)
		inboundGeo = "{} {}, {}".format(
			inboundInfo.get("country","N/A"),
			inboundInfo.get("city","Unknown City"),
			inboundInfo.get("organization","N/A")
		)
		logger.info(
			"Node inbound IP : {}, Geo : {}".format(
				inboundIP,
				inboundGeo
			)
		)
		return (inboundIP,inboundGeo)

	def __geoIPOutbound(self):
		outboundInfo = IPLoc()
		outboundIP = outboundInfo.get("ip","N/A")
		outboundGeo = "{} {}, {}".format(
			outboundInfo.get("country","N/A"),
			outboundInfo.get("city","Unknown City"),
			outboundInfo.get("organization","N/A")
		)
		logger.info(
			"Node outbound IP : {}, Geo : {}".format(
				outboundIP,
				outboundGeo
			)
		)
		return (outboundIP, outboundGeo)
	
	def tcpingOnly(self):
		logger.info("Test mode : tcp ping only.")
		self.__results = []
		config = self.__parser.getNextConfig()
		st = SpeedTest()
		while (True):
			if (config == None):break
			_item = self.__getBaseResult()
			_item["group"] = config["group"]
			_item["remarks"] = config["remarks"]
			self.__current = _item
			config["server_port"] = int(config["server_port"])
			self.__client.startClient(config)
			inboundInfo = self.__geoIPInbound(config)
			_item["geoIP"]["inbound"]["address"] = "{}:{}".format(inboundInfo[0],config["server_port"])
			_item["geoIP"]["inbound"]["info"] = inboundInfo[1]
			time.sleep(1)
			st = SpeedTest()
			latencyTest = st.tcpPing(config["server"],config["server_port"])
			_item["loss"] = 1 - latencyTest[1]
			_item["ping"] = latencyTest[0]
			_item["rawTcpPingStatus"] = latencyTest[2]
			logger.debug(latencyTest)
			if (latencyTest[0] > 0):
				try:
					googlePingTest = st.googlePing()
					_item["gPing"] = googlePingTest[0]
					_item["gPingLoss"] = 1 - googlePingTest[1]
					_item["rawGooglePingStatus"] = googlePingTest[2]
					if (_item["gPing"] > 0):
						outboundInfo = self.__geoIPOutbound()
						_item["geoIP"]["outbound"]["address"] = outboundInfo[0]
						_item["geoIP"]["outbound"]["info"] = outboundInfo[1]
				except:
					logger.exception("")
					pass
			self.__client.stopClient()
			self.__results.append(_item)
			logger.info("[{}] - [{}] - Loss: [{}%] - TCP Ping: [{}] - Google Loss: [{}%] - Google Ping: [{}]".format
				(
					_item["group"],
					_item["remarks"],
					_item["loss"] * 100,
					int(_item["ping"] * 1000),
					_item["gPingLoss"] * 100,
					int(_item["gPing"] * 1000)
				)
			)
			config = self.__parser.getNextConfig()
			time.sleep(1)
		self.__current = {}

	def fullTest(self):
		logger.info("Test mode : speed and tcp ping.Test method : {}.".format(self.__testMethod))
		self.__results = []
		configs = self.__parser.getAllConfig()
		totalConfCount = len(configs)
		config = self.__parser.getNextConfig()
		time.sleep(2)
		curConfCount = 0
		while(True):
			if(not config):break
			_item = self.__getBaseResult()
			_item["group"] = config.get("group","N/A")
			_item["remarks"] = config.get("remarks",config["server"])
			config["server_port"] = int(config["server_port"])
			self.__client.startClient(config)
			curConfCount += 1
			logger.info("Starting test for {} - {} [{}/{}]".format(_item["group"],_item["remarks"],curConfCount,totalConfCount))
			self.__current = _item
			inboundInfo = self.__geoIPInbound(config)
			_item["geoIP"]["inbound"]["address"] = inboundInfo[0]
			_item["geoIP"]["inbound"]["info"] = inboundInfo[1]
			time.sleep(1)
			try:
				st = SpeedTest()
				latencyTest = st.tcpPing(config["server"],config["server_port"])
				if (latencyTest[0] > 0):
					time.sleep(1)
					testRes = st.startTest(self.__testMethod)
					if (int(testRes[0]) == 0):
						logger.warn("Re-testing node.")
						testRes = st.startTest(self.__testMethod)
					_item["dspeed"] = testRes[0]
					_item["maxDSpeed"] = testRes[1]
					try:
						_item["trafficUsed"] = testRes[3]
						_item["rawSocketSpeed"] = testRes[2]
					except:
						pass	
					try:
						googlePingTest = st.googlePing()
						_item["gPing"] = googlePingTest[0]
						_item["gPingLoss"] = 1 - googlePingTest[1]
						_item["rawGooglePingStatus"] = googlePingTest[2]
						if (_item["gPing"] > 0):
							outboundInfo = self.__geoIPOutbound()
							_item["geoIP"]["outbound"]["address"] = outboundInfo[0]
							_item["geoIP"]["outbound"]["info"] = outboundInfo[1]
					except:
						logger.exception("")
						pass
					time.sleep(1)
				self.__client.stopClient()
				time.sleep(1)
				_item["loss"] = 1 - latencyTest[1]
				_item["ping"] = latencyTest[0]
				_item["rawTcpPingStatus"] = latencyTest[2]
				self.__results.append(_item)
				logger.info("[{}] - [{}] - Loss: [{}%] - TCP Ping: [{}] - Google Loss: [{}%] - Google Ping: [{}] - AvgSpeed: [{:.2f}MB/s] - MaxSpeed: [{:.2f}MB/s]".format
					(
						_item["group"],
						_item["remarks"],
						_item["loss"] * 100,
						int(_item["ping"] * 1000),
						_item["gPingLoss"] * 100,
						int(_item["gPing"] * 1000),
						_item["dspeed"] / 1024 / 1024,
						_item["maxDSpeed"] / 1024 / 1024
					)
				)
			#	logger.info(
			#		"{} - {} - Loss:{}%% - TCP_Ping:{} - AvgSpeed:{:.2f}MB/s - MaxSpeed:{:.2f}MB/s".format(
			#			_item["group"],
			#			_item["remarks"],
			#			_item["loss"] * 100,
			#			int(_item["ping"] * 1000),
			#			_item["dspeed"] / 1024 / 1024,
			#			_item["maxDSpeed"] / 1024 / 1024
			#			)
			#		)
			except Exception:
				self.__client.stopClient()
				logger.exception("")
			config = self.__parser.getNextConfig()
		self.__current = {}

