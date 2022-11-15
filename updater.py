#!/usr/bin/python3
from apijson import ApiJson
from utils import *
from appveyor import *
from simpleapi import *
from sourceforge import *
import time
import shutil
import platform
try:
    from pefile import PE
except ImportError:
    pass
from distutils import dir_util
from copy import copy
from codecs import open
import os
import logging
from datetime import datetime
from typing import Iterable, Generator


class MissingConfig(RuntimeError):
    pass


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
            "path": [],
            "keyword": [],
            "update_keyword": [],
            "exclude_keyword": [],
            "filetype": "7z",
            "add_version_to_filename": False,
            "regexes": [],
            "index": 0,
            "indexes": [],
            "try_redirect": True,
            "filename_override": "",
            "url": ""
        },
        "process":
        {
            "allow_restart": False,
            "service": False,
            "restart_wait": 3,
            "stop_cmd": "",
            "start_cmd": ""
        },
        "decompress":
        {
            "skip": False,
            "include_file_type": [],
            "exclude_file_type": [],
            "exclude_file_type_when_update": [],
            "single_dir": True,
            "keep_download_file": True,
            "use_builtin_zipfile": False
        },
        "version":
        {
            "path": [],
            "use_exe_version": False,
            "use_cmd_version": False,
            "from_page": False,
            "index": 0
        },
        "jsonver": "1.0.0"
    }
    platform_info = ProcessCtrl.platform_info
    OS = copy(ProcessCtrl.OS)
    supported_arch = ("arm", "aarch64", "i386", "i686", "amd64", "mips",
                      "mips64", "mipsle", "mips64le", "ppc64", "ppc64le", "s390x", "x86_64")

    OS = [OS, OS.capitalize()]
    if OS[0] == "windows":
        if platform.architecture()[0] == "64bit":
            arch = ["x86_64", "amd64", "x64", "windows-64"]
        else:
            arch = ["win32", "86", "windows-32"]
        OS = "win"
    elif OS[0] == "linux":
        # dirty workaround for nihui's *-ncnn-vulkan projects
        OS.append("ubuntu")
        for a in supported_arch:
            if a in platform_info:
                arch = a
        if arch == "aarch64":
            arch = ["arm64", "aarch64", "armv8"]
        elif arch == "x86_64":
            arch = ["x86_64", "amd64", "x64", "linux-64"]
        elif arch in ("i386", "i686"):
            arch = [arch, "linux-32","x86"]
    else:
        arch = ""
        logging.warning("Not supported OS %s, vars will not working." % OS)

    config_vars = {
        r"%arch": arch,
        r"%OS": OS
    }

    count = 0

    @classmethod
    def setAria2Rpc(cls, ip="127.0.0.1", port="6800", passwd=""):
        log = "log/aria2.log"
        try:
            os.makedirs("log")
        except FileExistsError:
            pass
        try:
            os.remove(log)
        except IOError:
            pass
        args = {
            "log": log,
            "log-level": "notice",  # TODO:Global log level
            "max-connection-per-server": "16",
            "min-split-size": "1M",
            "split": "16",
            "continue": "true"
        }
        cls.aria2 = Aria2Rpc(ip, port, passwd, **args)

    metadata = {}

    @classmethod
    def addRepos(cls, *repos):
        cls.requests_obj = requests.Session()
        cls.requests_obj.mount('http://', HTTPAdapter(max_retries=cls.times))
        cls.requests_obj.mount('https://', HTTPAdapter(max_retries=cls.times))
        cls.requests_obj.proxies.update(cls.proxies)
        for repo in repos:
            metadata_url = Url.join(repo, "metadata.json")
            try:
                j = cls.requests_obj.get(
                    metadata_url, timeout=cls.tmout).json()
            except Exception as e:
                logging.warning(
                    "getting metadata from repo %s failed, cause: %s .skipping" % (repo, e))
                if logging.root.isEnabledFor(logging.DEBUG):
                    logging.exception(e)
                continue

            for project in j:
                url = Url.join(repo, j[project]["config_path"])
                new_value = j[project]
                new_value.update({"url": url})
                cls.metadata.update({
                    project: new_value
                })
        if cls.metadata == {}:
            msg = "cannot get metadata from any repo, please check you repository configuration"
            logging.error(msg)
            raise ValueError(msg)

    @classmethod
    def setLocalConfigDir(cls, local_config_dir):
        os.makedirs(local_config_dir, exist_ok=True)
        cls.config_dir = local_config_dir

    @classmethod
    def setRequestsArgs(cls, times, tmout, proxy):
        cls.times = times
        cls.tmout = tmout
        cls.proxies = {
            "http": proxy,
            "https": proxy
        }

    @classmethod
    def setRemoteAria2(cls, remote_dir, local_dir):
        cls.remote_dir = remote_dir
        cls.local_dir = local_dir

    @classmethod
    def quitAriaRpc(cls):
        while cls.count != 0:
            time.sleep(1)
        cls.aria2.quit()

    @classmethod
    def setDefaults(cls, defaults):
        cls.CONF = JsonConfig.mergeDict(cls.CONF, defaults)

    @classmethod
    def setBins(cls, bin_aria2c, bin_libarchive):
        Aria2Rpc.setAria2Bin(bin_aria2c)
        if bin_libarchive:
            Decompress.setLibarchive(bin_libarchive)

    @staticmethod
    def version_compare(newversion: Iterable[int], oldversion: Iterable[int]):
        """
        if newversion > oldversion, return False. else return True
        """
        count = min(len(newversion), len(oldversion))
        for i in range(count):
            aa = newversion[i]
            bb = oldversion[i]
            if aa > bb:
                return False
            elif aa < bb:
                return True
        return True

    @staticmethod
    def version_convert(version: str):
        version = re.sub('[^0-9\.\-]', '', version)
        version = version.replace(r"-", r".")
        version = version.split(r".")
        versiontuple = []
        for num in version:
            try:
                versiontuple.append(int(num))
            except ValueError:
                versiontuple.append(0)
        return versiontuple

    @staticmethod
    def file_sel(filelist: Iterable[str], include_filetype: Iterable[str], exclude_filetype: Iterable[str], prefix: str) -> Generator:
        for file in filelist:
            if not file.startswith(prefix):
                continue

            flag = False
            for filetype in exclude_filetype:
                if file.endswith(filetype):
                    flag = True
            if flag:
                continue

            if include_filetype != []:
                for filetype in include_filetype:
                    if file.endswith(filetype):
                        yield file
            else:
                yield file

    def __init__(self, name: str, path: str, proxy: str = "", retry: int = 5, override: dict = {}):
        self.count += 1
        self.path = path
        self.name = name
        self.proxy = proxy
        self.retry = retry
        self.versionfile_path = os.path.join(self.path, self.name+".VERSION")

        self.addversioninfo = False

        config_filename = os.path.join(self.config_dir, "%s.json" % name)
        if os.path.exists(config_filename):
            if name in self.metadata:
                logging.debug(
                    "config file for %s exist in local and metadata, check for update" % self.name)
                local_config_time = datetime.utcfromtimestamp(
                    os.path.getmtime(config_filename))
                remote_config_time = datetime.strptime(
                    self.metadata[name]["date"], "%Y-%m-%d %H:%M:%S.%f")
                if local_config_time < remote_config_time:
                    logging.debug(
                        "config file for %s needs downloading" % self.name)
                    download_new_config = True
                else:
                    logging.debug("config file for %s is latest" % self.name)
                    download_new_config = False
            else:
                logging.debug(
                    "config file for %s exist in local but not in metadata, use local config" % self.name)
                download_new_config = False
        else:
            if name in self.metadata:
                logging.debug(
                    "config file for %s not exist, needs downloading" % self.name)
                download_new_config = True
            else:
                msg = "config for \"%s\" not exist in local and remote" % self.name
                logging.error(msg)
                raise MissingConfig(msg)
        if download_new_config:
            self.conf = JsonConfig(config_filename, "w")
            j = self.requests_obj.get(self.metadata[self.name]["url"]).json()
            self.conf.dumpconfig(j)

        self.conf = JsonConfig(config_filename, "r")
        if not self.version_compare(self.version_convert(self.conf.get("jsonver", "999")), self.version_convert(self.CONF["jsonver"])):
            if "jsonver" in self.conf:
                msg = "config file %s jsonver %s is newer than program supported %s, please update this program" % (
                    config_filename, self.conf["jsonver"], self.CONF["jsonver"])
            else:
                msg = "no jsonver in config file %s, exiting" % config_filename
            raise ValueError(msg)
        self.conf: JsonConfig = JsonConfig.mergeDict(self.conf, override)

        for key in self.config_vars:
            self.conf.var_replace(key, self.config_vars[key])

        self.conf.set_defaults(self.CONF)

        # compatibility code, will remove in the future
        for key in ("keyword", "update_keyword", "exclude_keyword"):
            if type(self.conf["download"][key]) == str:
                self.conf["download"][key] = [self.conf["download"][key]]

        if "image_name" not in self.conf["process"]:
            self.conf["process"].update({"image_name": self.name})
        if self.OS[0] == "win" and not self.conf["process"]["image_name"].endswith(".exe"):
            self.conf["process"].update(
                {"image_name": self.conf["process"]["image_name"]+".exe"})

        self.simple = False
        if self.conf["basic"]["api_type"] == "github":
            self.api = GithubApi(self.conf["basic"]["account_name"],
                                 self.conf["basic"]["project_name"], self.conf["build"]["branch"])
        elif self.conf["basic"]["api_type"] == "appveyor":
            self.api = AppveyorApi(
                self.conf["basic"]["account_name"], self.conf["basic"]["project_name"], self.conf["build"]["branch"])
        elif self.conf["basic"]["api_type"] == "sourceforge":
            self.api = SourceforgeApi(self.conf["basic"]["project_name"])
        elif self.conf["basic"]["api_type"] == "apijson":
            self.api = ApiJson(self.conf["basic"]["api_url"])
        elif self.conf["basic"]["api_type"] in ("simplespider", "staticlink"):
            self.api = SimpleSpider(self.conf["basic"]["page_url"])
            self.simple = True
        else:
            raise ValueError("No such api %s" % self.conf["basic"]["api_type"])

        self.api.setRequestsArgs(self.proxy, self.times, self.tmout)

    def getDlUrl(self):
        try:
            if self.conf["basic"]["api_type"] == "apijson":
                self.dlurl = self.api.getDlUrl(self.conf["download"]["path"])
            elif self.simple:
                self.dlurl = self.api.getDlUrl(regexes=self.conf["download"]["regexes"], indexs=self.conf["download"]
                                               ["indexes"], try_redirect=self.conf["download"]["try_redirect"], dlurl=self.conf["download"]["url"])
            elif self.install or self.conf["download"]["update_keyword"] == []:
                self.dlurl = self.api.getDlUrl(self.conf["download"]["keyword"], self.conf["download"]["exclude_keyword"] +
                                               self.conf["download"]["update_keyword"], self.conf["download"]["filetype"], self.conf["download"]["index"])
            else:
                self.dlurl = self.api.getDlUrl(self.conf["download"]["update_keyword"], self.conf["download"]
                                               ["exclude_keyword"], self.conf["download"]["filetype"], self.conf["download"]["index"])
        except requests.exceptions.ConnectionError:
            logging.error("network failed")
            raise
        if self.conf["download"]["filename_override"] == "":
            try:
                self.filename = Url.basename(self.dlurl)
            except TypeError:
                raise ValueError("Can't get download url!")
        else:
            self.filename = self.conf["download"]["filename_override"]

    def checkIfUpdateIsNeed(self, currentVersion):
        self.exepath = os.path.join(
            self.path, self.conf["process"]["image_name"])
        if currentVersion == "" and not self.conf["version"]["use_exe_version"]:
            self.install = True
        elif self.conf["version"]["use_exe_version"] and not os.path.exists(self.exepath):
            self.install = True
        else:
            self.install = False

        if self.conf["basic"]["api_type"] == "apijson":
            self.version = self.api.getVersion(self.conf["version"]["path"])
        elif self.simple:
            self.getDlUrl()
            self.version = self.api.getVersion(
                self.conf["version"]["regex"], self.conf["version"]["from_page"], self.conf["version"]["index"])
        elif self.conf["basic"]["api_type"] == "sourceforge":
            self.getDlUrl()
            self.version = self.api.getVersion()
        else:
            self.version = self.api.getVersion(self.conf["build"]["no_pull"])
        self.conf.var_replace("%VER", self.version)
        if self.install:
            logging.info("Running on install mode")
            return True
        elif self.conf["version"]["use_exe_version"]:
            self.versiontuple = self.version_convert(self.version)

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
            return not (self.version_compare(self.versiontuple, filever) or self.version_compare(self.versiontuple, prodver))
        elif self.conf["version"]["use_cmd_version"]:
            try:
                # Not impletment yet
                pass
            except IndexError:
                pass
        else:
            return not self.version == currentVersion

    def download(self):
        try:
            self.dldir = self.remote_dir+"/"+self.name
        except AttributeError:
            self.dldir = os.path.join(self.path, "downloads")
            if not os.path.exists(self.dldir):
                os.makedirs(self.dldir)

        if self.conf["download"]["add_version_to_filename"]:
            temp_name = os.path.splitext(self.filename)
            temp_version = str(self.version)
            for disallow in (r"<", r">", r"/", "\\", r"|", r":", r"*", r"?"):
                temp_version = temp_version.replace(disallow, " ")
            self.filename = temp_name[0]+"_"+temp_version+temp_name[-1]

        self.aria2.wget(self.dlurl, self.dldir, self.filename,
                        proxy=self.proxy, retry=self.retry)

    def extract(self):
        if self.conf["decompress"]["skip"]:
            return
        try:
            self.fullfilename = os.path.join(
                self.local_dir, self.name, self.filename)
        except AttributeError:
            self.fullfilename = os.path.join(self.dldir, self.filename)
        times = 5
        sucuss = False
        while times > 0 and not sucuss:
            try:
                f = Decompress(self.fullfilename,
                               self.conf["decompress"]["use_builtin_zipfile"])
                sucuss = True
            except Exception as e:
                raise  # I'm pretty sure compress file validation is broken now. It will need fixing on the utils._Decompress side
                logging.error(
                    "downloaded file %s is broken, trying re-download now")
                logging.exception(e)
                os.remove(self.fullfilename)
                self.download()
                times -= 1

        filelist0 = list(f.getFileList())

        if type(self.conf["decompress"]["single_dir"]) == bool:
            prefix = f.getPrefixDir()
        else:
            prefix = self.conf["decompress"]["single_dir"]

        if not self.install:
            self.conf["decompress"]["exclude_file_type"] = self.conf["decompress"]["exclude_file_type"] + \
                self.conf["decompress"]["exclude_file_type_when_update"]

        selected_files = list(self.file_sel(
            filelist0, self.conf["decompress"]["include_file_type"], self.conf["decompress"]["exclude_file_type"], prefix))

        if self.conf["decompress"]["single_dir"] and prefix != "":
            extract_path = os.path.join(InstanceLock.get_temp(), self.name)
            os.makedirs(extract_path, exist_ok=True)
            os.makedirs(self.path, exist_ok=True)
        else:
            extract_path = self.path

        if selected_files == filelist0:
            f.extractAll(extract_path)
        else:
            f.extractFiles(selected_files, extract_path)

        if self.conf["decompress"]["single_dir"] and prefix != "":
            for file in os.listdir(os.path.join(extract_path, prefix)):
                new = os.path.join(extract_path, prefix, file)
                try:
                    shutil.copy(new, self.path)
                except (IsADirectoryError, PermissionError) as e:
                    if logging.root.isEnabledFor(logging.DEBUG):
                        logging.debug("this is a debug exception logging")
                        logging.exception(e)
                    old = os.path.join(self.path, file)
                    dir_util.copy_tree(new, old)
            shutil.rmtree(extract_path)
        elif len(selected_files) == 1:  # quick workaround for gpu-z
            main_program_file = os.path.join(
                self.path, self.conf["process"]["image_name"])
            extracted_file = os.path.join(extract_path, selected_files[0])
            if os.path.exists(main_program_file):
                os.remove(main_program_file)
            os.rename(extracted_file, main_program_file)

        if not self.conf["decompress"]["keep_download_file"]:
            os.remove(self.fullfilename)

        logging.info("update %s successed" % self.name)

    def updateVersionFile(self):
        if self.conf["version"]["use_exe_version"]:
            if self.addversioninfo:  # not working for now
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
            with open(self.versionfile_path, 'w', encoding="utf8") as versionfile:
                versionfile.write(self.version)
            versionfile.close()

    def run(self, force=False, currentVersion="", popup=False):
        if self.checkIfUpdateIsNeed(currentVersion) or force:
            logging.info("starting update %s" % self.name)

            self.getDlUrl()
            self.download()
            self.proc = ProcessCtrl(
                self.conf["process"]["image_name"], self.conf["process"]["service"])
            if self.conf["process"]["allow_restart"]:
                if self.conf["process"]["stop_cmd"] == "":
                    self.proc.stopProc()
                else:
                    # should add %PATH support sometime
                    os.system(self.conf["process"]["stop_cmd"])
                time.sleep(self.conf["process"]["restart_wait"])
                self.extract()
                if self.conf["process"]["start_cmd"] == "":
                    self.proc.startProc()
                else:
                    os.system(self.conf["process"]["start_cmd"])

            else:
                if self.proc.checkProc():
                    msg = "waiting for program %s to stop so we can update it" % self.name
                    logging.warning(msg)
                    ProcessCtrl.popup_msg(msg)
                    self.proc.waitProc()
                self.extract()
            self.count -= 1
            return self.version
        else:
            logging.info(
                "%s is already updated, no need for update" % (self.name))
            return False


if __name__ == "__main__":
    pass
