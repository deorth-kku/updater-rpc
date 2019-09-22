#!/usr/bin/python3
from utils import *
from appveyor import *
import json
import shutil
from distutils import dir_util

CONF={
    "branch": None,
    "keyword":"",
    "no_keyword":"/",
    "filetype":"7z",
    "no_pull":False,
    "allow_restart":False,
    "include_file_type":[],
    "exclude_file_type":[],
    "single_dir":True,
    "keep_download_file": True

}




class Updater:
    def __init__(self,name,path):
        self.path=path
        self.name=name

        self.conf=dict(CONF)
        try:
            self.newconf=loadconfig(name)
        except IOError:
            print(self.name+".json配置文件不存在，请检查")
            sys.exit(1)

        for key in loadconfig(name):
            self.conf.update({key:self.newconf[key]})
        try:
            self.conf["image_name"]
        except KeyError:
            self.conf.update({"image_name":self.name+".exe"})
        
        if self.conf["api_type"]=="github":
            self.api=GithubApi(self.conf["account_name"],self.conf["project_name"])
        elif self.conf["api_type"]=="appveyor":
            self.api=AppveyorApi(self.conf["account_name"],self.conf["project_name"],self.conf["branch"])

        self.dlurl=self.api.getDlUrl(self.conf["keyword"],self.conf["no_keyword"],self.conf["filetype"],self.conf["no_pull"])
        self.filename=os.path.basename(self.dlurl)   

    def checkIfUpdateIsNeed(self):
        self.version=self.api.getVersion()
        self.versionfile_path=os.path.join(self.path,'VERSION')
        try:
            self.versionfile = open(self.versionfile_path, 'r')   
            self.oldversion = self.versionfile.read()
            self.versionfile.close()
        except:
            self.oldversion = ""     
                
        return not self.version==self.oldversion
        
    def download(self):
        self.dldir=os.path.join(self.path,"downloads")
        if not os.path.exists(self.dldir):
            os.makedirs(self.dldir)
        wget(self.dlurl,self.dldir)

    def extract(self):
        self.fullfilename=os.path.join(self.dldir,self.filename)
        f=Py7z(self.fullfilename)
        filelist0=f.getFileList()
        if self.conf["include_file_type"]==[] and self.conf["exclude_file_type"]==[]:
            f.extractAll(self.path)         
        else:
            if self.conf["include_file_type"]!=[]:
                filelist1=[]
                for file in filelist0:
                    for include in self.conf["include_file_type"]:
                        if file.split(r".")[-1]==include:
                            filelist1.append(file)
            else:
                filelist1=list(filelist0)
            filelist0=[]
            for file in filelist1:
                flag=False
                for exclude in self.conf["exclude_file_type"]:
                    type0=file.split(r".")[-1]
                    if type0==exclude:
                          flag=True
                if not flag:
                    filelist0.append(file)
            f.extractFiles(filelist0,self.path)
        prefix=f.getPrefixDir()
        if self.conf["single_dir"] and prefix!="":
            for file in os.listdir(os.path.join(self.path,prefix)):
                new=os.path.join(self.path,prefix,file)
                try:
                    shutil.copy(new,self.path)
                except (IsADirectoryError,PermissionError):
                    old=os.path.join(self.path,file)
                    dir_util.copy_tree(new,old)
            shutil.rmtree(os.path.join(self.path,prefix))
        if not self.conf["keep_download_file"]:
            os.remove(self.fullfilename)

        



    def updateVersionfile(self):
        with open(self.versionfile_path, 'w') as self.versionfile:
            self.versionfile.write(self.version)
        self.versionfile.close()


    def run(self,force=False):
        if self.checkIfUpdateIsNeed() or force:
            self.download()
            self.proc=ProcessCtrl(self.conf["image_name"])
            if self.conf["allow_restart"]:
                self.proc.stopProc()
                self.extract()
                self.proc.startProc()
            
            else:
                while self.proc.checkProc():
                    print("请先关闭正在运行的"+self.name,end="\r")
                    time.sleep(1)
                self.extract()
            self.updateVersionfile()
        else:
            print("当前%s已是最新，无需更新！"%(self.name))




        
        

    

if __name__=="__main__":
    #update=Updater("pd_loader","/root/pdaft")
    #update=Updater(sys.argv[1],sys.argv[2])
    #update.run()
    if sys.platform=="win32":
        citra_path=r"D:\citra"
        rpcs3_path=r"D:\rpcs3"
        pd_loader_path=r"F:\GAMES\Hatsune Miku Project DIVA Arcade Future Tone"
        ds4_path=r"D:\Program Files\DS4Windows"
    else:
        citra_path="/root/citra"
        rpcs3_path="/root/rpcs3"
        pd_loader_path="/root/pdaft"
        ds4_path="/root/ds4"

    '''
    ds4=Updater("ds4windows",ds4_path)
    ds4.run()

    citra=Updater("citra",citra_path)
    citra.run()
    rpcs3=Updater("rpcs3",rpcs3_path)
    rpcs3.run()
    '''
    pdl=Updater("pd_loader",pd_loader_path)
    pdl.run(True)
    
        
