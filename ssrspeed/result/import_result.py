#coding:utf-8

import json

def importResult(filename):
	fi = None
	with open(filename,"r",encoding="utf-8") as f:
		fi = json.loads(f.read())
		f.close()
	return fi

