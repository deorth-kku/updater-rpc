#!/usr/bin/python3
# -*- coding: utf-8 -*-
import xmlrpc.client
import sys
import os
import time
import re
import requests
from requests.adapters import HTTPAdapter
import json
import psutil
import subprocess
import platform
from copy import copy,deepcopy


def urljoin(*args):
    """
    Joins given arguments into an url. Trailing but not leading slashes are
    stripped for each argument.
    """
    return "/".join(map(lambda x: str(x).rstrip('/'), args))


def mergeDict(a, b):
    newdict = deepcopy(a)
    for key in b:
        typeflag = type(b[key])
        if typeflag == dict:
            newvalue = mergeDict(a[key], b[key])
        elif typeflag == set:
            newvalue = deepcopy(a[key])
            for bb in b[key]:
                newvalue.add(bb)
        elif typeflag == list or typeflag == tuple:
            newvalue = a[key]+b[key]
        else:
            newvalue = b[key]
        newdict.update({key: newvalue})
    return newdict


class LoadConfig:
    @staticmethod
    def replace(config,var_key,var_value):
        typeflag = type(config)
        if typeflag==str:
            if config==var_key:
                return var_value
            else:
                return config
        elif typeflag==int or typeflag==float or typeflag==bool:
            return config
        elif typeflag==dict:
            for key in config:
                newvalue = LoadConfig.replace(config[key],var_key, var_value)
                config.update({key:newvalue})
            return config
        else:
            new=[]
            for key in config:
                new_key = LoadConfig.replace(key,var_key,var_value)
                new.append(new_key)
            return typeflag(new)

    
    def __init__(self, file):
        self.file = file
        try:
            with open(file, 'r',encoding='utf-8') as f:
                self.config = json.load(f)
        except (IOError, json.decoder.JSONDecodeError):
            self.config = {}


    def var_replace(self,key,value):
        self.config=self.replace(self.config,key,value)


    def dumpconfig(self, config):
        with open(self.file, "w",encoding='utf-8') as f:
            json.dump(config, f, sort_keys=True,
                      indent=4, separators=(',', ': '),ensure_ascii=False)

def setRequestsArgs(improxy,times,tmout): 
    global requests_obj
    global time_out
    global proxy_str
    proxy_str=improxy
    time_out=tmout

    requests_obj=requests.Session()
    requests_obj.mount('http://', HTTPAdapter(max_retries=times))
    requests_obj.mount('https://', HTTPAdapter(max_retries=times))
    if improxy!="":
        proxies={
            "http":improxy,
            "https":improxy
        }
        requests_obj.proxies.update(proxies)



def getJson(url):
    try:
        request = requests_obj.get(url=url,timeout=time_out)
    except (requests.exceptions.ConnectTimeout,requests.exceptions.ConnectionError):
        raise
    return request.json()


class Aria2Rpc:
    bin_path="aria2c"
    @classmethod
    def setAria2Bin(cls,bin_path):
        cls.bin_path=bin_path

    def __init__(self, ip, port="6800", passwd="",args={}):
        connection = xmlrpc.client.ServerProxy(
            "http://%s:%s/rpc" % (ip, port))
        self.aria2 = connection.aria2
        self.secret = "token:"+passwd
        self.tasks = []
        self.methodname = None
        try:
            self.aria2.getVersion(self.secret)
        except ConnectionRefusedError:
            if ip == "127.0.0.1" or ip == "localhost" or ip == "127.1":
                cmd = [
                    self.bin_path,
                    "--enable-rpc=true",
                    "--rpc-allow-origin-all=true",
                    "--rpc-listen-port=%s" % port
                ]
                for arg in args:
                    if len(arg)!=1:
                        arg_str="--%s=%s"%(arg,args[arg])
                    else:
                        arg_str="-%s=%s"%(arg,args[arg])
                    cmd.append(arg_str)

                if passwd != "":
                    cmd.append("--rpc-secret=%s" % passwd)
                self.process = subprocess.Popen(cmd,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                raise
    
    def __getattr__(self, name):
        self.methodname = name
        return self.__defaultMethod


    def __defaultMethod(self,*args):
        if self.methodname != None:
            newargs = (self.secret,) + args
            method = getattr(self.aria2, self.methodname)
            self.methodname = None
            return method(*newargs)

    
    def download(self, url, pwd, filename=None):
        opts={"dir":pwd}
        try:
            opts.update({"all-proxy":proxy_str})
        except NameError:
            pass
        if filename!=None:
            opts.update({"out":filename})

        req = self.addUri([url], opts)
        self.tasks.append(req)
        return req

    def wget(self, url, pwd, filename=None,retry=5):
        full_retry=copy(retry)
        while True:
            req = self.download(url, pwd, filename)
            status = self.tellStatus(req)['status']
            while status == 'active' or status == 'paused':
                time.sleep(0.1)
                r = self.tellStatus(req)
                status = r['status']
                progressBar(int(r['completedLength']), int(
                    r['totalLength']), int(r['downloadSpeed']))
            if status != 'complete':
                if retry<=0:
                    raise DownloadError(r["errorMessage"])
                else:
                    retry-=1
                    print("%s, gonna retry %s/%s"%(r["errorMessage"],full_retry-retry,full_retry))
                    time.sleep(1)
                    continue
            else:
                break

            
    def quit(self):
        try:
            self.process.terminate()
            self.process.wait()
        except AttributeError:
            pass



class DownloadError(Exception):
    def __init__(self, status):
        Exception.__init__(self)
        self.message = "Download failed, Download task is %s" % status

    def __str__(self):
        return repr(self.message)


def progressBar(current, total, speed):
    if total == 0:
        total = 1
    if current > total:
        current = total
    current = current
    total = total
    if speed < 1048756:
        speed = str(int(speed/1024))+"KB/S "
    else:
        speed = str(round(speed/1048756, 2))+"MB/S"
    per = round(current/total*100, 1)
    percent = str(per)+"%"
    n = int(per/5)
    i = int(per % 5)
    list = ['  ', '▍ ', '▊ ', '█ ', '█▍']
    if per == 100:
        bar = " |"+"██"*n+"| "
    else:
        bar = " |"+"██"*n+list[i]+"  "*(19-n)+"| "
    print(bar+percent+"  "+str(round(current/1048756, 1))+"MB/" +
          str(round(total/1048756, 1))+"MB "+speed+"      ", end="\r")


class Py7z: 
    bin_path="7z"
    @classmethod
    def set7zBin(cls,bin_path):
        cls.bin_path=bin_path
    def __init__(self, filename):
        if subprocess.call(self.bin_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
            print("PLease check if 7z is installed")
            sys.exit(2)

        self.filename = filename

        self.getFileList()

    def getFileList(self):
        try:
            return self.filelist
        except AttributeError:
            self.filelist = []
            p=subprocess.Popen([self.bin_path, "l", self.filename], stdout=subprocess.PIPE, bufsize=1, universal_newlines=True)
            for line in p.stdout:
                line = line.strip()
                try:
                    if line[20:24] == r"....":
                        filename = line[53:]
                        self.filelist.append(filename)
                except IndexError:
                    pass
            p.wait()
            if p.returncode!=0:
                raise FileBrokenError(self.filename)
            return self.filelist

    def getPrefixDir(self):
        dir = os.path.commonprefix(self.filelist)
        return dir

    def extractFiles(self, filenames, outdir):
        cmd = [self.bin_path, "x", "-y", "-o"+outdir, self.filename]+filenames
        subprocess.call(cmd)

    def extractAll(self, outdir):
        cmd = [self.bin_path, "x", "-y", "-o"+outdir, self.filename]
        subprocess.call(cmd)


class FileBrokenError(Exception):
    def __init__(self, filename):
        Exception.__init__(self)
        self.message = "%s is not a correct compress file" % filename

    def __str__(self):
        return repr(self.message)


class ProcessCtrl:
    platform_info=platform.platform().split("-")
    OS=platform_info[0].lower()

    if OS=="windows":
        service_type="windows"
    elif OS=="linux":
        if os.path.exists("/usr/bin/systemd"):
            service_type="systemd"
        else:
            service_type="init"
    else:
        print("not supported OS type %s"%OS)

    @staticmethod
    def Service(service_name,command):
        if ProcessCtrl.service_type=="windows":
            cmd=["net",command,service_name]
        elif ProcessCtrl.service_type=="init":
            cmd=["service",service_name,command]
        elif ProcessCtrl.service_type=="systemd":
            cmd=["systemctl",command,service_name]
        
        subprocess.call(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

    def __init__(self, process_name, service=False):
        self.process_name = process_name
        self.service = service
        if service:
            pass
        else:
            self.flushProc()

    def flushProc(self):
        self.procs = []
        for proc in psutil.process_iter():
            if proc.name() == self.process_name:
                self.procs.append(proc)

    def checkProc(self):
        self.flushProc()
        if len(self.procs) != 0:
            return True
        else:
            return False

    def stopProc(self):
        if self.service:
            self.Service(self.process_name,"stop")
        else:
            self.flushProc()
            self.cmds = []
            for proc in self.procs:
                self.cmds.append((proc.cmdline(), proc.cwd()))
                proc.kill()

    def startProc(self):
        if self.service:
            self.Service(self.process_name,"start")
        else:
            for cmd in self.cmds:
                subprocess.Popen(cmd[0], cwd=cmd[1])

    def restartProc(self):
        self.stopProc()
        self.startProc()


if __name__ == "__main__":
    pass