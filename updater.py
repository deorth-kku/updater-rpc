#!/usr/bin/python3
from utils import *
from appveyor import *
import json
import shutil
import platform
try:
    from pefile import PE
except ImportError:
    pass
from distutils import dir_util


class Updater:
    CONF = {
        "basic": {},
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
            "add_version_to_filename": False
        },
        "process":
        {
            "allow_restart": False
        },
        "decompress":
        {
            "include_file_type": [],
            "exclude_file_type": [],
            "single_dir": True,
            "keep_download_file": True
        },
        "version":
        {
            "use_exe_version": False
        }
    }

    platform_info=platform.platform().split("-")
    OS=platform_info[0].lower()
    supported_arch=("arm","aarch64","i386","i686","amd64","mips","mips64","mipsle","mips64le","ppc64","ppc64le","s390x")
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
        args=[
            "--log=%s"%log,
            "--log-level=notice",#TODO:Global log level
            "--max-connection-per-server=16",
            "--min-split-size=1M",
            "--split=16",
            "--continue=true"
        ]
        try:
            cls.aria2 = Aria2Rpc(ip, port, passwd,args)
        except xmlrpc.client.Fault:
            print("aria2 rpc密码错误")
            raise

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
            if newversion[i]>oldversion[i]:
                return False
        return True

    def __init__(self, name, path):
        self.count += 1
        self.path = path
        self.name = name
        self.versionfile_path = os.path.join(self.path, self.name+".VERSION")

        self.addversioninfo = False

        config=LoadConfig("config/%s.json" % name)

        for key in self.config_vars:
            config.var_replace(key,self.config_vars[key])
        self.newconf = config.config
        self.conf = mergeDict(self.CONF, self.newconf)

        for key in ("keyword","update_keyword","exclude_keyword"):
            if type(self.conf["download"][key])==str:
                self.conf["download"][key]=[self.conf["download"][key]]

        if "image_name" not in self.conf["process"]:
            self.conf["process"].update({"image_name": self.name})
        if self.OS[0]=="win" and not self.conf["process"]["image_name"].endswith(".exe"):
            self.conf["process"].update({"image_name": self.conf["process"]["image_name"]+".exe"})
            
        
        apistr=self.conf["basic"]["api_type"].capitalize()+"Api"
        self.api = eval(apistr)(
                self.conf["basic"]["account_name"], self.conf["basic"]["project_name"], self.conf["build"]["branch"])

    def getDlUrl(self):  
        try:
            if self.install or self.conf["download"]["update_keyword"]==[]:
                self.dlurl = self.api.getDlUrl(self.conf["download"]["keyword"], self.conf["download"]["exclude_keyword"]+self.conf["download"]["update_keyword"], self.conf["download"]["filetype"])
            else:
                self.dlurl = self.api.getDlUrl(self.conf["download"]["update_keyword"], self.conf["download"]["exclude_keyword"], self.conf["download"]["filetype"])
        except requests.exceptions.ConnectionError:
            print("连接失败")
            raise
        try:
            self.filename = os.path.basename(self.dlurl)
        except TypeError:
            raise ValueError("Can't get download url!")

    def checkIfUpdateIsNeed(self):
        self.install=False
        self.version = self.api.getVersion(self.conf["build"]["no_pull"])
        if self.conf["version"]["use_exe_version"]:
            version = re.sub('[^0-9\.\-]', '', self.version)
            version = version.replace(r"-", r".")
            version = version.split(r".")
            self.versiontuple = []
            for num in version:
                try:
                    self.versiontuple.append(int(num))
                except ValueError:
                    self.versiontuple.append(0)

            self.exepath = os.path.join(
                self.path, self.conf["process"]["image_name"])
            try:
                pe = PE(self.exepath)
            except FileNotFoundError:
                self.install=True
                return True
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
            
        else:
            try:
                versionfile = open(self.versionfile_path, 'r')
                oldversion = versionfile.read()
                versionfile.close()
            except FileNotFoundError:
                self.install=True
                return True
            return not self.version == oldversion

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

        self.aria2.wget(self.dlurl, self.dldir, self.filename)

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
        prefix = f.getPrefixDir()
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
            with open(self.versionfile_path, 'w') as versionfile:
                versionfile.write(self.version)
            versionfile.close()

    def run(self, force=False):
        if  self.checkIfUpdateIsNeed() or force:
            print("开始更新%s"%self.name)
            try:
                self.getDlUrl()
            except ValueError:
                print("cannot get dlurl, skipping")
                return
            self.download()
            self.proc = ProcessCtrl(self.conf["process"]["image_name"])
            if self.conf["process"]["allow_restart"]:
                self.proc.stopProc()
                self.extract()
                self.updateVersionFile()
                self.proc.startProc()

            else:
                while self.proc.checkProc():
                    print("请先关闭正在运行的"+self.name, end="\r")
                    time.sleep(1)
                self.extract()
                self.updateVersionFile()
            self.count-=1
        else:
            # TODO:Use log instead of print
            print("当前%s已是最新，无需更新！" % (self.name))


if __name__ == "__main__":
    pass