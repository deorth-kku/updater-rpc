#!/usr/bin/python3
import os,re,sys
import utils

filename = os.path.basename(temp.url)
version = re.findall('-.......\.7z', filename)[0][1:7]
#print(version)
#os.system('pause')

obj = SearchFile()
temp.update = obj.searchFile("citra.exe", version)
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
if os.path.exists("downloads\\"+filename) and not os.path.exists("downloads\\"+filename+"\.aria2"):
    if os.system("7z.exe x -y -o./ downloads/"+filename):
        os.system("del downloads\\"+filename)
        os.system('rd /s /q ".\\'+ch+'-mingw\\"')
    else:
        os.system('xcopy /e /y /s ".\\'+ch+'-mingw\\*" .\\')
        os.system('rd /s /q ".\\'+ch+'-mingw\\"')
        os.system('pause')
        sys.exit()
print("正在开始下载")
if os.system('aria2c.exe -s16 -x16 -k 1M --file-allocation=falloc -o downloads/'+filename+' '+temp.url):
    print("下载失败")
    os.system('pause')
    sys.exit()
while CheckProcExistByPN('citra-qt.exe'):
    
    time.sleep(10)
os.system("7z.exe x -y -o./ downloads/"+filename)

