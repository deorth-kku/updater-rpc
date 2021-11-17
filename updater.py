#!/usr/bin/python3
from utils import *
from appveyor import *
from simpleapi import *
import time
import shutil
try:
    from pefile import PE
except ImportError:
    pass
from distutils import dir_util
from copy import copy
from codecs import open
import os
class Updater:
    CONF = {
        "basic": {
        },
        "build":
        {
            "branch": None,
            "no_pull": False
        },
        "download":
        {
            "keyword": [],
            "update_keyword":[],
            "exclude_keyword": [],
            "filetype": "7z",
            "add_version_to_filename": False,
            "regexes":[],
            "index":0,
            "indexes":[],
            "try_redirect":True,
            "filename_override":"",
            "url":""
        },
        "process":
        {
            "allow_restart": False,
            "service": False,
            "restart_wait":3
        },
        "decompress":
        {
            "include_file_type": [],
            "exclude_file_type": [],
            "exclude_file_type_when_update":[],
            "single_dir": True,
            "keep_download_file": True
        },
        "version":
        {
            "use_exe_version": False,
            "use_cmd_version": False,
            "from_page":False,
            "index":0
        }
    }
    platform_info=ProcessCtrl.platform_info
    OS=copy(ProcessCtrl.OS)
    supported_arch=("arm","aarch64","i386","i686","amd64","mips","mips64","mipsle","mips64le","ppc64","ppc64le","s390x","x86_64")
    if OS=="windows":
        if platform.architecture()[0]=="64bit":
            arch="64"
        else:
            arch=["86","32"]
        OS="win"
    elif OS=="linux":
        for a in supported_arch:
            if a in platform_info:
                arch=a
        if arch=="aarch64":
            arch=["arm64","arch64","armv8"]
        elif arch=="x86_64":
            arch="64"
    else:
        arch=""
        print("Not supported OS %s, vars will not working."%OS)

    OS=[OS,OS.capitalize()]
    
    config_vars={
        r"%arch":arch,
        r"%OS": OS
    }

    count = 0

    @classmethod
    def setAria2Rpc(cls, ip="127.0.0.1", port="6800", passwd=""):
        log="log/aria2.log"
        try:
            os.makedirs("log")
        except FileExistsError:
            pass
        try:
            os.remove(log)
        except IOError:
            pass
        args={
            "log":log,
            "log-level":"notice",#TODO:Global log level
            "max-connection-per-server":"16",
            "min-split-size":"1M",
            "split":"16",
            "continue":"true"
        }
        try:
            cls.aria2 = Aria2Rpc(ip, port, passwd,args)
        except xmlrpc.client.Fault:
            print("aria2 rpc密码错误")
            raise
    @classmethod
    def setRequestsArgs(cls,times,tmout):
        cls.times=times
        cls.tmout=tmout

    @classmethod
    def setRemoteAria2(cls,remote_dir,local_dir):
        cls.remote_dir=remote_dir
        cls.local_dir=local_dir

    @classmethod
    def quitAriaRpc(cls):
        while cls.count!=0:
            time.sleep(1)
        cls.aria2.quit()

    @classmethod
    def setDefaults(cls, defaults):
        cls.CONF = mergeDict(cls.CONF, defaults)
    @classmethod
    def setBins(cls,bin_aria2c,bin_7z):
        Aria2Rpc.setAria2Bin(bin_aria2c)
        Py7z.set7zBin(bin_7z)
    
    @staticmethod
    def version_compare(newversion,oldversion):
        count=min(len(newversion),len(oldversion))
        for i in range(count):
            aa=newversion[i]
            bb=oldversion[i]
            if aa>bb:
                return False
            elif aa<bb:
                return True
        return True

    def __init__(self, name, path, proxy=""):
        self.count += 1
        self.path = path
        self.name = name
        self.proxy = proxy
        self.versionfile_path = os.path.join(self.path, self.name+".VERSION")

        self.addversioninfo = False

        self.conf=JsonConfig("config/%s.json" % name)

        for key in self.config_vars:
            self.conf.var_replace(key,self.config_vars[key])

        self.conf.set_defaults(self.CONF)

        for key in ("keyword","update_keyword","exclude_keyword"):
            if type(self.conf["download"][key])==str:
                self.conf["download"][key]=[self.conf["download"][key]]

        if "image_name" not in self.conf["process"]:
            self.conf["process"].update({"image_name": self.name})
        if self.OS[0]=="win" and not self.conf["process"]["image_name"].endswith(".exe"):
            self.conf["process"].update({"image_name": self.conf["process"]["image_name"]+".exe"})


            
        self.simple=False
        if self.conf["basic"]["api_type"]=="github":
            self.api = GithubApi(self.conf["basic"]["account_name"], self.conf["basic"]["project_name"], self.conf["build"]["branch"])
        elif self.conf["basic"]["api_type"]=="appveyor":
            self.api = AppveyorApi(self.conf["basic"]["account_name"], self.conf["basic"]["project_name"], self.conf["build"]["branch"])
        elif self.conf["basic"]["api_type"]=="simplespider" or self.conf["basic"]["api_type"]=="staticlink":
            self.api = SimpleSpider(self.conf["basic"]["page_url"])
            self.simple = True
        else:
            raise ValueError("No such api %s"%self.conf["basic"]["api_type"])

        self.api.setRequestsArgs(self.proxy,self.times,self.tmout)

    def getDlUrl(self):  
        try:
            if self.simple:
                self.dlurl = self.api.getDlUrl(regexes=self.conf["download"]["regexes"],indexs=self.conf["download"]["indexes"],try_redirect=self.conf["download"]["try_redirect"],dlurl=self.conf["download"]["url"])
            elif self.install or self.conf["download"]["update_keyword"]==[]:
                self.dlurl = self.api.getDlUrl(self.conf["download"]["keyword"], self.conf["download"]["exclude_keyword"]+self.conf["download"]["update_keyword"], self.conf["download"]["filetype"],self.conf["download"]["index"])
            else:
                self.dlurl = self.api.getDlUrl(self.conf["download"]["update_keyword"], self.conf["download"]["exclude_keyword"], self.conf["download"]["filetype"],self.conf["download"]["index"])
        except requests.exceptions.ConnectionError:
            print("连接失败")
            raise
        if self.conf["download"]["filename_override"]=="":
            try:
                self.filename = Url.basename(self.dlurl)
            except TypeError:
                raise ValueError("Can't get download url!")
        else:
            self.filename=self.conf["download"]["filename_override"]

    def checkIfUpdateIsNeed(self,currentVersion):
        self.exepath = os.path.join(self.path, self.conf["process"]["image_name"])
        if currentVersion=="" and not self.conf["version"]["use_exe_version"]:
            self.install=True
        elif self.conf["version"]["use_exe_version"] and not os.path.exists(self.exepath):
            self.install=True
        else:
            self.install=False
        #self.install=currentVersion=="" and not self.conf["version"]["use_exe_version"] and not os.path.exists(self.exepath)
        if self.simple:
            self.getDlUrl()
            self.version = self.api.getVersion(self.conf["version"]["regex"],self.conf["version"]["from_page"],self.conf["version"]["index"])
        else:
            self.version = self.api.getVersion(self.conf["build"]["no_pull"])
        self.conf.var_replace("%VER",self.version)
        if self.install:
            return True
        elif self.conf["version"]["use_exe_version"]:
            version = re.sub('[^0-9\.\-]', '', self.version)
            version = version.replace(r"-", r".")
            version = version.split(r".")
            self.versiontuple = []
            for num in version:
                try:
                    self.versiontuple.append(int(num))
                except ValueError:
                    self.versiontuple.append(0)

            pe = PE(self.exepath)
            if not 'VS_FIXEDFILEINFO' in pe.__dict__:
                #raise NameError("ERROR: Oops, %s has no version info. Can't continue."%self.exepath)
                self.addversioninfo = True
                pe.close()
                return True
            if not pe.VS_FIXEDFILEINFO:
                #raise NameError("ERROR: VS_FIXEDFILEINFO field not set for %s. Can't continue."%self.exepath)
                pe.close()
                return True

            verinfo = pe.VS_FIXEDFILEINFO[0]
            filever = (verinfo.FileVersionMS >> 16, verinfo.FileVersionMS & 0xFFFF,
                       verinfo.FileVersionLS >> 16, verinfo.FileVersionLS & 0xFFFF)
            prodver = (verinfo.ProductVersionMS >> 16, verinfo.ProductVersionMS & 0xFFFF,
                       verinfo.ProductVersionLS >> 16, verinfo.ProductVersionLS & 0xFFFF)
            pe.close()
            return not (self.version_compare(self.versiontuple,filever) or self.version_compare(self.versiontuple,prodver))
        elif self.conf["version"]["use_cmd_version"]:
            try:
                pass
            except IndexError:
                pass
        else:
            return not self.version == currentVersion

    def download(self):
        try:
            self.dldir=self.remote_dir+"/"+self.name
        except AttributeError:
            self.dldir = os.path.join(self.path, "downloads")
            if not os.path.exists(self.dldir):
                os.makedirs(self.dldir)

        if self.conf["download"]["add_version_to_filename"]:
            temp_name=os.path.splitext(self.filename)
            self.filename=temp_name[0]+"_"+self.version+temp_name[-1]

        self.aria2.wget(self.dlurl, self.dldir, self.filename, proxy=self.proxy)

    def extract(self):
        try:
            self.fullfilename= os.path.join(self.local_dir,self.name,self.filename)
        except AttributeError:
            self.fullfilename = os.path.join(self.dldir, self.filename)
        times = 5
        sucuss = False
        while times>0 and not sucuss:
            try:
                f = Py7z(self.fullfilename)
                sucuss = True
            except FileBrokenError:
                os.remove(self.fullfilename)
                self.download()
                times -= 1
        
        filelist0 = f.getFileList()

        if type(self.conf["decompress"]["single_dir"])==bool:
            prefix = f.getPrefixDir()
        else:
            filelist1=deepcopy(filelist0)
            prefix = self.conf["decompress"]["single_dir"]
            for file in filelist0:
                booo=file.startswith(os.path.join(prefix,""))
                if not booo:
                    filelist1.remove(file)
            filelist0=filelist1
        
        if not self.install:
            self.conf["decompress"]["exclude_file_type"]=self.conf["decompress"]["exclude_file_type"]+self.conf["decompress"]["exclude_file_type_when_update"]
        
        if self.conf["decompress"]["include_file_type"] == [] and self.conf["decompress"]["exclude_file_type"] == []:
            f.extractAll(self.path)
    
        else:
            if self.conf["decompress"]["include_file_type"] != []:
                filelist1 = []
                for file in filelist0:
                    for include in self.conf["decompress"]["include_file_type"]:
                        if file.split(r".")[-1] == include:
                            filelist1.append(file)
            else:
                filelist1 = list(filelist0)
            filelist0 = []
            for file in filelist1:
                flag = False
                for exclude in self.conf["decompress"]["exclude_file_type"]:
                    type0 = file.split(r".")[-1]
                    if type0 == exclude:
                        flag = True
                if not flag:
                    filelist0.append(file)
            f.extractFiles(filelist0, self.path)

        if self.conf["decompress"]["single_dir"] and prefix != "":
            for file in os.listdir(os.path.join(self.path, prefix)):
                new = os.path.join(self.path, prefix, file)
                try:
                    shutil.copy(new, self.path)
                except (IsADirectoryError, PermissionError):
                    old = os.path.join(self.path, file)
                    dir_util.copy_tree(new, old)
            shutil.rmtree(os.path.join(self.path, prefix))
        if not self.conf["decompress"]["keep_download_file"]:
            os.remove(self.fullfilename)

    def updateVersionFile(self): 
        if self.conf["version"]["use_exe_version"]:
            if self.addversioninfo: #not working for now
                pass
            '''
            FileVersionMS=self.versiontuple[0]*0xFFFF+self.versiontuple[1]
            FileVersionLS=self.versiontuple[2]*0xFFFF+self.versiontuple[3]
            pe = PE(self.exepath)
            pe.VS_FIXEDFILEINFO[0].FileVersionMS=FileVersionMS
            pe.VS_FIXEDFILEINFO[0].FileVersionLS=FileVersionLS
            pe.write(self.exepath)
            '''
        else:
            with open(self.versionfile_path, 'w',encoding="utf8") as versionfile:
                versionfile.write(self.version)
            versionfile.close()

    def run(self, force=False,currentVersion=""):
        if  self.checkIfUpdateIsNeed(currentVersion) or force:
            print("开始更新%s"%self.name)
            try:
                self.getDlUrl()
            except IndexError:
                print("cannot get dlurl, skipping")
                return
            self.download()
            self.proc = ProcessCtrl(self.conf["process"]["image_name"],self.conf["process"]["service"])
            if self.conf["process"]["allow_restart"]:
                self.proc.stopProc()
                time.sleep(self.conf["process"]["restart_wait"])
                self.extract()
                self.proc.startProc()

            else:
                while self.proc.checkProc():
                    print("请先关闭正在运行的"+self.name, end="\r")
                    time.sleep(1)
                self.extract()
            self.count-=1
            return self.version
        else:
            # TODO:Use log instead of print
            print("当前%s已是最新，无需更新！" % (self.name))
            return False


if __name__ == "__main__":
    pass