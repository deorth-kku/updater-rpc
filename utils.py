#!/usr/bin/python3
# -*- coding: utf-8 -*-
import xmlrpc.client
import sys
import os
import time
import re
import requests
import json
import psutil
import subprocess

def urljoin(*args):
    """
    Joins given arguments into an url. Trailing but not leading slashes are
    stripped for each argument.
    """
    return "/".join(map(lambda x: str(x).rstrip('/'), args))


class LoadConfig:
    def __init__(self,file):
        self.file = file
        try:
            with open(file, 'r') as f:
                self.config = json.load(f)
        except (IOError,json.decoder.JSONDecodeError):
            self.config = {}



    def dumpconfig(self,config):
        with open(self.file,"w") as f:
            json.dump(config,f,sort_keys=True, indent=4, separators=(',', ': '))


def getJson(url):
    request = requests.get(url=url)
    return request.json()

class Aria2Rpc:
    def __init__(self,ip,port="6800",passwd=""):
        self.connection = xmlrpc.client.ServerProxy("http://%s:%s/rpc"%(ip,port))
        self.secret = "token:"+passwd
        self.tasks = []
        

    def download(self, url, pwd): 
        opts = dict(dir=pwd)
        req = self.connection.aria2.addUri(self.secret, [url], opts)
        self.tasks.append(req)
        return req

    def getProgress(self,req):
        return self.connection.aria2.tellStatus(self.secret, req)

    def wget(self,url,pwd):
        req = self.download(url, pwd)
        status=self.getProgress(req)['status']
        while status == 'active' or status == 'paused':
            time.sleep(0.1)
            r = self.getProgress(req)
            status = r['status']
            progressBar(int(r['completedLength']), int(r['totalLength']), int(r['downloadSpeed']))
        if status != 'complete':
            raise DownloadError(status)

class DownloadError(Exception):
    def __init__(self,status):
        Exception.__init__(self)
        self.message="Download is not complete, Download task is %s"%status
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
    print(bar+percent+"  "+str(round(current/1048756, 1))+"MB/"+str(round(total/1048756, 1))+"MB "+speed+"      ", end="\r")


class Py7z:  # TODO: Throw exception when decompress error
    def __init__(self, filename):
        if subprocess.call("7z", stdout=subprocess.PIPE, stderr=subprocess.PIPE):
            print("PLease check if 7z is installed")
            sys.exit(2)
    
        self.filename = filename

        cmd = ["7z","t",self.filename]
        code = subprocess.call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if code != 0:
            raise FileBrokenError(self.filename)

    def getFileList(self):
        try:
            return self.filelist
        except AttributeError:
            self.filelist = []
            with subprocess.Popen(["7z", "l", self.filename], stdout=subprocess.PIPE, bufsize=1, universal_newlines=True) as p:
                for line in p.stdout:
                    line = line.strip()
                    try:
                        if line[20:25] == r"....A":
                            filename = line[53:]
                            self.filelist.append(filename)
                    except IndexError:
                        pass
            return self.filelist

    def getPrefixDir(self):
        dir = os.path.commonprefix(self.filelist)
        return dir

    def extractFiles(self, filenames, outdir):
        cmd = ["7z", "x", "-y", "-o"+outdir, self.filename]+filenames
        subprocess.call(cmd)

    def extractAll(self, outdir):
        cmd = ["7z", "x", "-y", "-o"+outdir, self.filename]
        subprocess.call(cmd)


class FileBrokenError(Exception):
    def __init__(self,filename):
        Exception.__init__(self)
        self.message="%s is not a correct compress file"%filename
    def __str__(self):
        return repr(self.message)


class ProcessCtrl:
    def __init__(self, process_name):
        self.process_name = process_name
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
        self.flushProc()
        self.cmds = []
        for proc in self.procs:
            self.cmds.append((proc.cmdline(), proc.cwd()))
            proc.kill()

    def startProc(self):
        for cmd in self.cmds:
            subprocess.Popen(cmd[0], cwd=cmd[1])

    def restartProc(self):
        self.stopProc()
        self.startProc()


if __name__ == "__main__":
    #f = Py7z("/root/citra/downloads/citra-windows-mingw-20190903-8c2a335.7z")
    #f.getFileList()
    f = Py7z("foo")

    # f.extractFiles(f.filelist,"/root/rpcs3")
    # p=ProcessCtrl("chromium")
    # p.restartProc()

    #d=Aria2Rpc("127.0.0.1",passwd="pandownload")
    #d.wget("https://test123.com","./")