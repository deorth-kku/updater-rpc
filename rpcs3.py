#!/usr/bin/python3
import urllib
import urllib.request
import re
import sys
import os
import time
import psutil
import win32com.client


def check_exsit(imagename):

    pids = psutil.pids()
    for pid in pids:
        ppp = psutil.Process(pid)
        if ppp:
            if ppp.name() == imagename:
                return 1
    return 0 

def CheckProcExistByPN(process_name):
  try:
    WMI = win32com.client.GetObject('winmgmts:') 
    processCodeCov = WMI.ExecQuery('select * from Win32_Process where Name="%s"' % process_name)
  except Exception as e:
    print(process_name + "error : ", e);
  if len(processCodeCov) > 0:
    return 1
  else:
    return 0
    
class GetUrl:
    def __init__(self, url):
        html = self.getHtml(url)
        self.url = self.getdlurl(html)[0]
    def getHtml(self, url):
        headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'}
        req = urllib.request.Request(url=url, headers=headers)
        try:
            page = urllib.request.urlopen(req).read()
        except urllib.error.URLError:
            print ("网络不可用！")
            os.system('pause')
            sys.exit()
        html = page.decode()
        return html

    def getdlurl(self, html):
        reg = '<a href=\'(https://.+?win64.7z)\' download>'
        #<a href='https://github.com/RPCS3/rpcs3-binaries-win/releases/download/build-56e24f8993d70ff19f69ae0fda3f8b9db720ece4/rpcs3-v0.0.6-7802-56e24f89_win64.7z' download>
        imglist = re.findall(reg,html)
        return imglist

class SearchFile:
    def searchFile(self, filename, version):
        self.version = version.encode()
        try:
            fo = open(filename, "rb")
        except IOError:
            return 2

            
        data = fo.read()
        fo.close()
        key = re.findall(self.version,data)
        del data
        if key:
            #print (re.findall(self.version,data))
            return 1
        else:
            return 0
			
if __name__ == '__main__':
    print("正在获取下载地址")
    temp = GetUrl('https://rpcs3.net/download')
    #print(temp.url)
    filename = os.path.basename(temp.url)
    version = re.findall(, temp.url)[0][1:7]
    obj = SearchFile()
    temp.update = obj.searchFile("rpcs3.exe", version)
    if temp.update == 1:
        print ("当前版本已是最新")
        os.system('pause')
        sys.exit()
    elif temp.update == 2:
        print("找不到rpsc3.exe文件！")
        os.system('pause')
        sys.exit()
    if not os.path.exists("downloads"):
        os.mkdir("downloads")
    print("正在开始下载")
    if os.system('aria2c.exe -s16 -x16 -k 1M --auto-file-renaming=false -o downloads/'+filename+' '+temp.url):
        print("下载失败")
        os.system('pause')
        sys.exit()
    while CheckProcExistByPN('rpcs3.exe'):
        print("请先关闭正在运行的rpcs3")
        time.sleep(10)
    os.system("7z.exe x -y -o./ downloads/"+filename)

    
