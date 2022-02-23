#!/usr/bin/python3
import re
import requests
import xmltodict
from pprint import pprint
from datetime import datetime
from appveyor import FatherApi
from utils import Url

class SourceforgeApi(FatherApi):
    rss_source="https://sourceforge.net/projects/%s/rss?path=/"
    download_site="https://download.sourceforge.net/"
    def __init__(self,project_name):
        self.project_name = project_name
        self.rssurl=self.rss_source%project_name
        self.download_prefix=Url.join(self.download_site,project_name)
    
    def getFileList(self):
        req=self.requests_obj.get(self.rssurl)
        for file in  xmltodict.parse(req.text)["rss"]["channel"]["item"]:
            dt=datetime.strptime(file["pubDate"],"%a, %d %b %Y %H:%M:%S UT")
            yield {
                "file":file["title"],
                "date":dt
            }

    def getDlUrl(self,keyword=[], no_keyword=[], filetype="7z",index=0):
        match=0
        for file_info in self.getFileList():
            if self.filename_check(file_info["file"],keyword,no_keyword,filetype):
                if match==index:
                    dlurl=Url.join(self.download_prefix,file_info["file"].lstrip("/"))
                    self.version=str(file_info["date"])
                    return dlurl
                else:
                    match+=1
            

    def getVersion(self):
        return self.version


if __name__=="__main__":
    jj=SourceforgeApi("sevenzip")
    
    print(jj.getDlUrl(filetype="exe"))
    print(jj.getVersion())
    #jb=JsonConfig("./tt.json")
    #jb.data=dict(jj)
    #jb.dumpconfig()

    
    
    
        


