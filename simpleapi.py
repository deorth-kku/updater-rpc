#!/usr/bin/python3
import requests
from html import unescape
import re
import os
from utils import urljoin
from appveyor import FatherApi

class SimpleSpider(FatherApi):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'}
    def __init__(self,pageurl):
        self.pageurl=pageurl

    def getPage(self):
        req=self.requests_obj.get(url=self.pageurl,headers=self.headers)
        self.page=req.text

    def getDlUrl(self,regex,index=0,try_redirect=True):
        self.getPage()
        imglist=re.findall(regex,self.page)
        self.dlurl=imglist[index]
        self.dlurl=unescape(self.dlurl)
        if not self.dlurl.startswith("http"):
            self.dlurl=urljoin(self.pageurl,self.dlurl)
        if try_redirect:
            req=self.requests_obj.head(self.dlurl)
            if req.status_code==302:
                self.dlurl=req.headers['Location']
        return self.dlurl

    def getVersion(self,regex,from_page=False,index=0):
        if from_page:
            version=re.findall(regex,self.page)[index]
        else:
            self.dl_filename=os.path.basename(self.dlurl)
            version=re.findall(regex,self.dl_filename)[index]
        return version
        




if __name__ == "__main__":
    pass
