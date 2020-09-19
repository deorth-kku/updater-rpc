#!/usr/bin/python3
import requests
from html import unescape
import re
import os
from utils import Url
from appveyor import FatherApi

class SimpleSpider(FatherApi):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'}
    def __init__(self,pageurl,page_regex=False,index=0):
        self.pageurl=pageurl
        self.page_regex=page_regex
        self.page_index=index

    def getPage(self):
        req=self.requests_obj.get(url=self.pageurl,headers=self.headers)
        if self.page_regex:
            page=req.text
            page2url=re.findall(self.page_regex,page)[self.page_index]
            if page2url.startswith("/"):
                site=Url.sitename(self.pageurl)
                page2url=Url.join(site,page2url)
            elif not page2url.startswith("http"):
                page2url=Url.join(self.pageurl,page2url)
            req=self.requests_obj.get(url=page2url,headers=self.headers)
            self.page2url=page2url
        self.page=req.text

    def getDlUrl(self,regex,index=0,try_redirect=True):
        self.getPage()
        imglist=re.findall(regex,self.page)
        self.dlurl=imglist[index]
        self.dlurl=unescape(self.dlurl)
        if self.dlurl.startswith("/"):
            site=Url.sitename(self.pageurl)
            self.dlurl=Url.join(site,self.dlurl)
        elif not self.dlurl.startswith("http"):
            self.dlurl=Url.join(self.pageurl,self.dlurl)
        if try_redirect:
            req=self.requests_obj.head(self.dlurl)
            if req.status_code==302 or req.status_code==303:
                self.dlurl=req.headers['Location']
        return self.dlurl

    def getVersion(self,regex,from_page=False,index=0):
        if from_page:
            version=re.findall(regex,self.page)[index]
        else:
            self.dl_filename=Url.basename(self.dlurl)
            version=re.findall(regex,self.dl_filename)[index]
        return version
        




if __name__ == "__main__":
    pass
