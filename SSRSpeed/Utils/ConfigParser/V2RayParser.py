#coding:utf-8

import urllib.parse
import logging
import requests
import json
logger = logging.getLogger("Sub")

from SSRSpeed.Utils.ConfigParser.BaseParser import BaseParser
from SSRSpeed.Utils.ConfigParser.V2RayParsers.ClashParser import ParserV2RayClash
from SSRSpeed.Utils.ConfigParser.V2RayParsers.V2RayNParser import ParserV2RayN
from SSRSpeed.Utils.ConfigParser.V2RayParsers.QuantumultParser import ParserQuantumult
import SSRSpeed.Utils.ConfigParser.BaseConfig.V2RayBaseConfig as V2RayConfig
import SSRSpeed.Utils.b64plus as b64plus

class V2RayParser(BaseParser):
	def __init__(self):
		super(V2RayParser,self).__init__()

	def __generateConfig(self,config):
		_config = V2RayConfig.getConfig()

		_config["inbounds"][0]["listen"] = self._getLocalConfig()[0]
		_config["inbounds"][0]["port"] = self._getLocalConfig()[1]

		#Common
		_config["remarks"] = config["remarks"]
		_config["group"] = config.get("group","N/A")
		_config["server"] = config["server"]
		_config["server_port"] = config["server_port"]

		#stream settings
		streamSettings = _config["outbounds"][0]["streamSettings"]
		streamSettings["network"] = config["network"]
		if (config["network"] == "tcp"):
			if (config["type"] == "http"):
				tcpSettings = V2RayConfig.getTcpSettingsObject()
				tcpSettings["header"]["request"]["path"] = config["path"].split(",")
				tcpSettings["header"]["request"]["headers"]["Host"] = config["host"].split(",")
				streamSettings["tcpSettings"] = tcpSettings
		elif (config["network"] == "ws"):
			webSocketSettings = V2RayConfig.getWebSocketSettingsObject()
			webSocketSettings["path"] = config["path"]
			webSocketSettings["headers"]["Host"] = config["host"]
			for h in config.get("headers",[]):
				webSocketSettings["headers"][h["header"]] = h["value"]
			streamSettings["wsSettings"] = webSocketSettings
		elif(config["network"] == "h2"):
			httpSettings = V2RayConfig.getHttpSettingsObject()
			httpSettings["path"] = config["path"]
			httpSettings["host"] = config["host"].split(",")
			streamSettings["httpSettings"] = httpSettings
		elif(config["network"] == "quic"):
			quicSettings = V2RayConfig.getQuicSettingsObject()
			quicSettings["security"] = config["host"]
			quicSettings["key"] = config["path"]
			quicSettings["header"]["type"] = config["type"]
			streamSettings["quicSettings"] = quicSettings

		streamSettings["security"] = config["tls"]
		if (config["tls"] == "tls"):
			tlsSettings = V2RayConfig.getTlsSettingsObject()
			tlsSettings["allowInsecure"] = True if (config.get("allowInsecure","false") == "true") else False
			tlsSettings["serverName"] = config["tls-host"]
			streamSettings["tlsSettings"] = tlsSettings

		_config["outbounds"][0]["streamSettings"] = streamSettings

		outbound = _config["outbounds"][0]["settings"]["vnext"][0]
		outbound["address"] = config["server"]
		outbound["port"] = config["server_port"]
		outbound["users"][0]["id"] = config["id"]
		outbound["users"][0]["alterId"] = config["alterId"]
		outbound["users"][0]["security"] = config["security"]
		_config["outbounds"][0]["settings"]["vnext"][0] = outbound
		return _config

	def _parseLink(self,link):

		if (link[:8] != "vmess://"):
			logger.error("Unsupport link : %s" % link)
			return None
		pv2rn = ParserV2RayN()
		cfg = pv2rn.parseSubsConfig(link)
		if (not cfg):
			pq = ParserQuantumult()
			cfg = pq.parseSubsConfig(link)
		if (not cfg):
			logger.error("Parse link {} failed.".format(link))
			return None
		return self.__generateConfig(cfg)
	
	def readSubscriptionConfig(self,url):
		header = {
			"User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
		}
		rep = requests.get(url,headers = header,timeout=15)
		rep.encoding = "utf-8"
		rep = rep.content.decode("utf-8")
		try:
			linksArr = (b64plus.decode(rep).decode("utf-8")).split("\n")
			for link in linksArr:
				link = link.strip()
			#	print(link)
				cfg = self._parseLink(link)
				if (cfg):
				#	print(cfg["remarks"])
					self._configList.append(cfg)
		except ValueError:
			logger.info("Try V2Ray Clash Parser.")
			pv2rc = ParserV2RayClash()
			for cfg in pv2rc.parseSubsConfig(rep):
				self._configList.append(self.__generateConfig(cfg))
		logger.info("Read %d node(s)" % len(self._configList))
	
	def readGuiConfig(self,filename):
		pv2rc = ParserV2RayClash()
		v2rnp = ParserV2RayN()
		rawGuiConfigs = pv2rc.parseGuiConfig(filename)
		if (rawGuiConfigs == False):
			logger.info("Not Clash Config.")
			rawGuiConfigs = v2rnp.parseGuiConfig(filename)
			if (rawGuiConfigs == False):
				logger.info("Not V2RayN Config.")
				logger.critical("Gui config parse failed.")
				rawGuiConfigs = []

		for _dict in rawGuiConfigs:
			_cfg = self.__generateConfig(_dict)
		#	logger.debug(_cfg)
			self._configList.append(_cfg)
		logger.info("Read %d node(s)" % len(self._configList))
	#	logger.critical("V2RayN configuration file will be support soon.")
		



