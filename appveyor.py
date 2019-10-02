#!/usr/bin/python3
import requests
import re
import os
from utils import getJson, urljoin


class AppveyorApi:
    def __init__(self, account_name, project_name, branch=None):
        if branch == None:
            self.branch = ""
        else:
            self.branch = "&branch="+branch
        self.apiurl = "https://ci.appveyor.com/api"
        self.account_name = account_name
        self.project_name = project_name

    def getJson(self, url):
        self.request = requests.get(url=url)
        return self.request.json()

    def getHistory(self):
        self.historyurl = urljoin(self.apiurl, "projects", self.account_name,
                                  self.project_name, "history?recordsNumber=100"+self.branch)
        self.json = getJson(self.historyurl)
        for build in self.json["builds"]:
            yield build["version"]

    def getDlUrl(self, keyword="", no_keyword="/", filetype="7z", no_pull=False):
        for version in self.getHistory():
            self.version = version
            self.buildurl = urljoin(
                self.apiurl, "projects", self.account_name, self.project_name, "build", self.version)
            self.buildjson = getJson(self.buildurl)
            if no_pull:
                try:
                    self.buildjson['build']['pullRequestId']
                    continue
                except KeyError:
                    pass
            self.jobid = self.buildjson["build"]["jobs"][0]["jobId"]
            self.artifactsurl = urljoin(
                self.apiurl, "buildjobs", self.jobid, "artifacts")
            self.artifactsjson = getJson(self.artifactsurl)
            if len(self.artifactsjson) == 0:
                continue
            for fileinfo in self.artifactsjson:
                filename = fileinfo["fileName"]
                if keyword in filename and no_keyword not in filename and filename[-len(filetype):] == filetype:
                    self.filename = filename
                    self.dlurl = urljoin(
                        self.apiurl, "buildjobs", self.jobid, "artifacts", self.filename)
                    return self.dlurl

    def getVersion(self):
        return self.version


class GithubApi:
    def __init__(self, account_name, project_name):
        self.apiurl = "https://api.github.com/repos"
        self.account_name = account_name
        self.project_name = project_name
        self.releasesurl = urljoin(
            self.apiurl, self.account_name, self.project_name, "releases")

    def getReleases(self):
        return getJson(self.releasesurl)

    def getDlUrl(self, keyword="", no_keyword="/", filetype="7z", no_pull=False):
        for release in self.getReleases():
            if release["name"] != None:
                self.version = release["name"]
            else:
                self.version = release["tag_name"]
            if len(release["assets"]) != 0:
                for file in release["assets"]:
                    if keyword in file["name"] and no_keyword not in file["name"] and file["name"][-len(filetype):] == filetype:
                        return file["browser_download_url"]
            elif filetype == "zip":
                return release["zipball_url"]
            elif filetype == "tar.gz":
                return release["tarball_url"]

    def getVersion(self):
        return self.version


class GithubSpider:
    def __init__(self, account_name, project_name):
        self.account_name = account_name
        self.project_name = project_name
        self.domain = "https://github.com"
        self.releasesurl = self.domain+"/" + \
            self.account_name+"/"+self.project_name+"/releases"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'}

    def getDlUrl(self, keyword="", no_keyword="/", filetype="7z", no_pull=False):
        self.request = requests.get(url=self.releasesurl, headers=self.headers)
        self.reg = '<a href="(/.+?\.%s)" rel="nofollow"' % (filetype)
        self.imglist = re.findall(self.reg, self.request.text)
        for url in self.imglist:
            filename = os.path.basename(url)
            if keyword in filename and no_keyword not in filename:
                return self.domain+url


if __name__ == "__main__":
    # pd_loader=AppveyorApi("nastys","pd-loader")
    # print(pd_loader.getDlUrl(filetype="zip"))


    kod = GithubApi("kalcaddle", "KodExplorer")
    #print(kod.getDlUrl(filetype="tar.gz"))
    #print(kod.getVersion())

    # rpcs3=AppveyorApi("rpcs3","rpcs3")
    # print(rpcs3.getDlUrl(keyword="rpcs3",no_keyword="sha256",no_pull=True))
    # print(rpcs3.getVersion())

    # citra=AppveyorApi("bunnei","citra")
    # print(citra.getDlUrl(keyword="mingw"))
    # print(citra.getVersion())

    # citra=GithubApi("citra-emu","citra-nightly")
    # print(citra.getDlUrl(keyword="mingw"))
    # print(citra.getVersion())

    # citra=GithubSpider("citra-emu","citra-nightly")
    # print(citra.getDlUrl(keyword="mingw"))

    # DS=GithubSpider("somewhatlurker","DivaSound")
    # print(DS.getDlUrl(filetype="zip"))
