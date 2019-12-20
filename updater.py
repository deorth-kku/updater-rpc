#!/usr/bin/python3
from utils import *
from appveyor import *
import json
import shutil
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
            "keyword": "",
            "exclude_keyword": "/",
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
        cls.aria2 = Aria2Rpc(ip, port, passwd,args)

    @classmethod
    def quitAriaRpc(cls):
        while cls.count!=0:
            time.sleep(1)
        cls.aria2.quit()

    @classmethod
    def setDefaults(cls, defaults):
        cls.CONF = mergeDict(cls.CONF, defaults)

    def __init__(self, name, path):
        self.count += 1
        self.path = path
        self.name = name

        self.newconf = LoadConfig("config/%s.json" % name).config
        self.conf = mergeDict(self.CONF, self.newconf)

        try:
            self.conf["process"]["image_name"]
        except KeyError:
            self.conf["process"].update({"image_name": self.name+".exe"})
        
        apistr=self.conf["basic"]["api_type"].capitalize()+"Api"
        self.api = eval(apistr)(
                self.conf["basic"]["account_name"], self.conf["basic"]["project_name"], self.conf["build"]["branch"])

    def getDlUrl(self):
        try:
            self.dlurl = self.api.getDlUrl(self.conf["download"]["keyword"], self.conf["download"]["exclude_keyword"], self.conf["download"]["filetype"], self.conf["build"]["no_pull"])
        except requests.exceptions.ConnectionError:
            print("连接失败")
            raise
        try:
            self.filename = os.path.basename(self.dlurl)
        except TypeError:
            raise ValueError("Can't get download url!")

    def checkIfUpdateIsNeed(self):
        self.version = self.api.getVersion()
        if self.conf["version"]["use_exe_version"]:
            self.addversioninfo = False
            version = re.sub('[^0-9\.\-]', '', self.version)
            version = version.replace(r"-", r".")
            version = version.split(r".")
            self.versiontuple = []
            for num in version:
                try:
                    self.versiontuple.append(int(num))
                except ValueError:
                    self.versiontuple.append(0)
            while len(self.versiontuple) < 4:
                self.versiontuple.append(0)
            self.versiontuple = tuple(self.versiontuple)

            self.exepath = os.path.join(
                self.path, self.conf["process"]["image_name"])
            try:
                pe = PE(self.exepath)
            except FileNotFoundError:
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
            return not (self.versiontuple == filever or self.versiontuple == prodver)
        else:
            versionfile = self.name+".VERSION"
            self.versionfile_path = os.path.join(self.path, versionfile)
            try:
                self.versionfile = open(self.versionfile_path, 'r')
                oldversion = self.versionfile.read()
                self.versionfile.close()
            except:
                oldversion = ""
            return not self.version == oldversion

    def download(self):
        self.dldir = os.path.join(self.path, "downloads")
        if not os.path.exists(self.dldir):
            os.makedirs(self.dldir)

        if self.conf["download"]["add_version_to_filename"]:
            temp_num=-len(self.conf["download"]["filetype"])-1
            self.filename=self.filename[0:temp_num]+"_"+self.version+self.filename[temp_num:]

        self.aria2.wget(self.dlurl, self.dldir, self.filename)

    def extract(self):
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

    def updateVersionFile(self): #not working for now
        if self.conf["version"]["use_exe_version"]:
            if self.addversioninfo:
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
            with open(self.versionfile_path, 'w') as self.versionfile:
                self.versionfile.write(self.version)
            self.versionfile.close()

    def run(self, force=False):
        self.getDlUrl()
        if self.checkIfUpdateIsNeed() or force:
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