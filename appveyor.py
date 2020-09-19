#!/usr/bin/python3
import requests
from requests.adapters import HTTPAdapter
import re
import os
from utils import Url


class FatherApi:
    @staticmethod
    def filename_check(filename, keywords, no_keywords, filetype):
        for keyword in keywords:
            type_flag=type(keyword)
            if type_flag==str:
                if keyword not in filename:
                    return False
            elif type_flag==list:
                exist_flag=False
                for keyword_sub in keyword:
                    if keyword_sub in filename:
                        exist_flag=True
                if not exist_flag:
                    return False
            else:
                raise TypeError("keyword must be a str or a list.")

        for no_keyword in no_keywords:
            if no_keyword in filename:
                return False
        if not filename.endswith(filetype):
            return False
        return True

    def setRequestsArgs(self,proxy,times,tmout):
        self.requests_obj=requests.Session()
        self.tmout=tmout
        self.requests_obj.mount('http://', HTTPAdapter(max_retries=times))
        self.requests_obj.mount('https://', HTTPAdapter(max_retries=times))
        if proxy!="":
            proxies={
                "http":proxy,
                "https":proxy
            }
            self.requests_obj.proxies.update(proxies)

    def getJson(self,url):
        try:
            request = self.requests_obj.get(url=url,timeout=self.tmout)
        except (requests.exceptions.ConnectTimeout,requests.exceptions.ConnectionError):
            raise
        return request.json()


class AppveyorApi(FatherApi):
    apiurl = "https://ci.appveyor.com/api"

    def __init__(self, account_name, project_name, branch=None):
        if branch == None:
            self.branch = ""
        else:
            self.branch = "&branch="+branch
        self.account_name = account_name
        self.project_name = project_name

    def getHistory(self):
        self.historyurl = Url.join(self.apiurl, "projects", self.account_name,
                                  self.project_name, "history?recordsNumber=100"+self.branch)
        self.json = self.getJson(self.historyurl)
        for build in self.json["builds"]:
            yield build["version"]
    
    
    def getVersion(self,no_pull=False):
        for version in self.getHistory():
            self.version = version
            self.buildurl = Url.join(
                self.apiurl, "projects", self.account_name, self.project_name, "build", self.version)
            self.buildjson = self.getJson(self.buildurl)
            if no_pull:
                try:
                    self.buildjson['build']['pullRequestId']
                    continue
                except KeyError:
                    pass
            jobs=self.buildjson["build"]["jobs"]
            if len(jobs)>1:
                for job in jobs:
                    if "elease" in job["name"]:
                        self.jobid=job["jobId"]
            elif len(jobs)==1:
                self.jobid=jobs[0]["jobId"]
            else:
                continue
            
            self.artifactsurl = Url.join(
                self.apiurl, "buildjobs", self.jobid, "artifacts")
            self.artifactsjson = self.getJson(self.artifactsurl)
            if len(self.artifactsjson) == 0:
                continue
            return self.version

    def getDlUrl(self, keyword=[], no_keyword=[], filetype="7z",index=0):
        try:
            match_urls=[]
            for fileinfo in self.artifactsjson:
                filename = fileinfo["fileName"]
                if self.filename_check(filename,keyword,no_keyword,filetype):
                    dlurl = Url.join(
                        self.apiurl, "buildjobs", self.jobid, "artifacts", filename)
                    match_urls.append(dlurl)
            return match_urls[index]
        except AttributeError:
            raise #AttributeError("you must run getVersion before you run getDlUrl")



class GithubApi(FatherApi):
    apiurl = "https://api.github.com/repos"

    def __init__(self, account_name, project_name, branch=None):
        self.account_name = account_name
        self.project_name = project_name

    def getReleases(self):
        self.releasesurl = Url.join(
            self.apiurl, self.account_name, self.project_name, "releases")
        releases=self.getJson(self.releasesurl)
        if "message" in releases:
            raise ValueError(releases["message"])
        return releases

    def getDlUrl(self, keyword=[], no_keyword=[], filetype="7z",index=0):
        try:
            if len(self.release["assets"]) != 0:
                match_urls=[]
                for file in self.release["assets"]:
                    if self.filename_check(file["name"],keyword,no_keyword,filetype):
                        match_urls.append(file["browser_download_url"])
                return match_urls[index]
            elif filetype == "zip":
                return self.release["zipball_url"]
            elif filetype == "tar.gz":
                return self.release["tarball_url"]
        except AttributeError:
            raise #AttributeError("you must run getVersion before you run getDlUrl")


    def getVersion(self, no_pull=False):
        for release in self.getReleases():
            if release["name"] != None and release["name"] != "":
                self.version = release["name"]
            else:
                self.version = release["tag_name"]
            self.release=release
            return self.version


if __name__ == "__main__":
    pass
