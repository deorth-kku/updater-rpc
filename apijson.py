#!/usr/bin/python3
import logging
import requests
from requests.adapters import HTTPAdapter
from appveyor import FatherApi
from utils._Url import Url


class ApiJson(FatherApi):
    @staticmethod
    def dict_path_get(input: dict, path: list):
        output = input
        for lv in path:
            output = output[lv]
        return output

    def __init__(self, api_url: str) -> None:
        self.api_url = api_url

    def getVersion(self, version_path: list) -> str:
        if not hasattr(self, "json"):
            self.json = self.getJson(self.api_url)
        return self.dict_path_get(self.json, version_path)

    def getDlUrl(self, dlurl_path_join: list) -> str:
        if not hasattr(self, "json"):
            self.json = self.getJson(self.api_url)
        dlurl_list = []
        for arg in dlurl_path_join:
            if type(arg) == str:
                dlurl_list.append(arg)
            elif type(arg) in (list, set, tuple):
                dlurl_list.append(self.dict_path_get(self.json, arg))
            else:
                logging.warning("not supported dlurl_path arg %s" % arg)
        return Url.join(*dlurl_list)
