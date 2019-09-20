#!/usr/bin/python3
# encoding=utf-8
from zipfile import ZipFile
from utils import *
from appveyor import AppveyorApi

def pd_loader_extract(pd_path, filename):
    fullname=os.path.join(pd_path,filename)
    zip=ZipFile(fullname,"r")
    for file in zip.namelist():
        if file[-4:]==".dll" or file[-4:]==".dva":
            zip.extract(file,path=pd_path)



pdaft_dir="/root/pdaft/"
if not os.path.exists(pdaft_dir):
    os.makedirs(pdaft_dir)

if __name__=="__main__":
    pd_loader=AppveyorApi("nastys","pd-loader")
    dlurl=pd_loader.getDlUrl()
    filename=os.path.basename(dlurl)
    wget(dlurl,pdaft_dir)
    pd_loader_extract(pdaft_dir,filename)
    os.remove(os.path.join(pdaft_dir,filename))

    
