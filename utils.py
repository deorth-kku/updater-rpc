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


if sys.platform=="win32":
    import win32com.client
    def CheckProcExistByPN(process_name):
        try:
            WMI = win32com.client.GetObject('winmgmts:') 
            processCodeCov = WMI.ExecQuery('select * from Win32_Process where Name="%s"' % process_name)
        except Exception as e:
            print(process_name + "error : ", e)
        if len(processCodeCov) > 0:
            return True
        else:
            return False
else:
    def CheckProcExistByPN(process_name):
        return False


def urljoin(*args):
    """
    Joins given arguments into an url. Trailing but not leading slashes are
    stripped for each argument.
    """
    return "/".join(map(lambda x: str(x).rstrip('/'), args))

def loadconfig(name):
    with open('config/%s.json'%(name), 'r') as f:
        config = json.load(f)
    return config

def getJson(url):
    request = requests.get(url=url)
    return request.json()



def searchFile(filename, version):
    version = version.encode()
    try:
        fo = open(filename, "rb")
    except IOError:
        print(filename+"文件不存在，请检查")
        sys.exit(1)
    data = fo.read()
    fo.close()
    key = re.findall(version,data)
    del data
    if key:
        return True
    else:
        return False

def wget(url, pwd): #TODO: Make a aria2 rpc class, with download exception
    secret='token:pandownload' 
    opts = dict(dir=pwd)
    s = xmlrpc.client.ServerProxy('http://127.0.0.1:6800/rpc')
    req=s.aria2.addUri(secret,[url],opts)
    r = s.aria2.tellStatus(secret,req)
    status = r['status']
    try:
        while status=='active':
            time.sleep(0.1)
            r = s.aria2.tellStatus(secret,req)
            status = r['status']
            progressBar(int(r['completedLength']),int(r['totalLength']),int(r['downloadSpeed']))
    except KeyboardInterrupt:
        print(' will shutdown the display, but the download is still running in aria2    ')
        sys.exit(1)
    #print('\n')

def progressBar(current, total, speed):
    if total==0:
        total=1
    if current>total:
        current=total
    current = current
    total = total
    if speed<1048756:
        speed = str(int(speed/1024))+"KB/S "
    else:
        speed = str(round(speed/1048756, 2))+"MB/S"
    per = round(current/total*100, 1)
    percent = str(per)+"%"
    n = int(per/5)
    i = int(per%5)
    list = ['  ','▍ ','▊ ','█ ','█▍']
    if per == 100:
        bar =  " |"+"██"*n+"| "
    else:
        bar =  " |"+"██"*n+list[i]+"  "*(19-n)+"| "
    print(bar+percent+"  "+str(round(current/1048756, 1))+"MB/"+str(round(total/1048756, 1))+"MB "+speed+"      ", end="\r")



class Py7z: #TODO: Throw exception when decompress error
    def __init__(self,filename):
        if subprocess.call("7z",stdout=subprocess.PIPE,stderr=subprocess.PIPE):
            print("PLease check if 7z is installed")
            sys.exit(2)

        self.filename=filename


    def getFileList(self):
        try:
            return self.filelist
        except AttributeError:
            self.filelist=[]
            with subprocess.Popen(["7z","l",self.filename],stdout=subprocess.PIPE,bufsize=1,universal_newlines=True) as p:
                for line in p.stdout:
                    line=line.strip()
                    try:
                        if line[20:25]==r"....A":
                            filename=line[53:] 
                            self.filelist.append(filename)
                    except IndexError:
                        pass
            return self.filelist

    def getPrefixDir(self):
        dir=os.path.commonprefix(self.filelist)
        return dir
    
    def extractFiles(self,filenames,outdir):
        cmd=["7z","x","-y","-o"+outdir,self.filename]+filenames
        subprocess.call(cmd)


    def extractAll(self,outdir):
        cmd=["7z","x","-y","-o"+outdir,self.filename]
        subprocess.call(cmd)



class ProcessCtrl:
    def __init__(self,process_name):
        self.process_name=process_name
        self.flushProc()
        

    def flushProc(self):
        self.procs=[]
        for proc in psutil.process_iter():
            if proc.name() == self.process_name:
                self.procs.append(proc)

    def checkProc(self):
        self.flushProc()
        if len(self.procs)!=0:
            return True
        else:
            return False

    def stopProc(self):
        self.flushProc()
        self.cmds=[]
        for proc in self.procs:
            self.cmds.append((proc.cmdline(),proc.cwd()))
            proc.kill()

    def startProc(self):
        for cmd in self.cmds:
            subprocess.Popen(cmd[0],cwd=cmd[1])
    
    def restartProc(self):
        self.stopProc()
        self.startProc()
        





    

if __name__ == "__main__":
    f=Py7z("/root/citra/downloads/citra-windows-mingw-20190903-8c2a335.7z")
    f.getFileList()

    #f.extractFiles(f.filelist,"/root/rpcs3")
    #p=ProcessCtrl("chromium")
    #p.restartProc()
    '''
    if len(sys.argv)>1:
        if sys.argv[1][0:4]!="http":
            print(sys.argv[1][0:3])
            url="http://"+sys.argv[1]
        else:
            url=sys.argv[1]
        if len(sys.argv)>2:
            if sys.argv[2][0]!="/":
                pwd=os.path.abspath(sys.argv[2])
            else:
                pwd=sys.argv[2]
        else:
            pwd = os.getcwd()
    else:
        print("no url")
        sys.exit(1)
    wget(url,pwd)
    '''
