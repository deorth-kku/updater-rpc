#!/usr/bin/python3
from html import unescape
import re
from utils import Url
from appveyor import FatherApi


class SimpleSpider(FatherApi):
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'}

    def page_regex_url(self, pageurl, regex, index, pagetext=None, try_redirect=False):
        if pagetext == None:
            req = self.requests_obj.get(url=pageurl, headers=self.headers)
            pagetext = req.text
        outurl = re.findall(regex, pagetext)[index]
        outurl = unescape(outurl)
        if outurl.startswith("/"):
            site = Url.sitename(pageurl)
            outurl = Url.join(site, outurl)
        elif not outurl.startswith("http"):
            outurl = Url.join(pageurl, outurl)
        if try_redirect:
            req = self.requests_obj.head(outurl)
            if req.status_code == 302 or req.status_code == 303:
                outurl = req.headers['Location']
        return outurl

    def __init__(self, pageurl: str, headers: dict = None):
        self.pageurl = pageurl
        self.__page = None
        self.dlurl = None
        if headers == None:
            self.headers = self.default_headers
        else:
            self.headers = headers

    @property
    def page(self):
        if not self.__page:
            req = self.requests_obj.get(url=self.pageurl, headers=self.headers)
            self.__page = req.text
        return self.__page

    def getDlUrl(self, regexes, indexs=[], try_redirect=True, dlurl=''):
        if self.dlurl:
            return self.dlurl
        if dlurl != "":
            self.dlurl = dlurl
        else:
            lvlen = len(regexes)
            if indexs == []:
                indexs = [0]*lvlen
            for lv in range(lvlen):
                if lv == 0:
                    url = self.page_regex_url(
                        self.pageurl, regexes[lv], indexs[lv], pagetext=self.page, try_redirect=try_redirect)
                else:
                    url = self.page_regex_url(
                        url, regexes[lv], indexs[lv], try_redirect=try_redirect)
            self.dlurl = url
        return self.dlurl

    def getVersion(self, regex, from_page=False, index=0):
        if from_page:
            version = re.findall(regex, self.page)[index]
        else:
            self.dl_filename = Url.basename(self.dlurl)
            version = re.findall(regex, self.dl_filename)[index]
        return version


if __name__ == "__main__":
    pass
