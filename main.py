#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys,os
import click
from updater import Updater
from utils import LoadConfig,mergeDict,setRequestsArgs


class Main:
    default={
                "aria2": {
                    "ip": "127.0.0.1",
                    "rpc-listen-port": "6800",
                    "rpc-secret": ""
                },
                "binarys":{
                    "aria2c":"aria2c",
                    "7z":"7z"
                },
                "requests":{
                    "proxy":"",
                    "timeout":30,
                    "retry":5
                },
                "projects": [],
                "defaults": {}
            }
    def __init__(self,conf="config.json"):
        os.chdir(sys.path[0])
        self.configpath=conf
        if not os.path.exists(self.configpath):
            configdir_upper=os.getenv("APPDATA")
            if configdir_upper==None:
                configdir_upper=os.path.join(os.getenv("HOME"),".config")
            configdir=os.path.join(configdir_upper,"updater-rpc")
            try:
                os.makedirs(configdir)
            except FileExistsError:
                pass
            self.configpath=os.path.join(configdir,"config.json")
        self.configfile = LoadConfig(self.configpath)
        self.config = self.configfile.config
        
        if "projects" in self.config and type(self.config["projects"])==dict:
            new_projects=[]
            for pro in self.config["projects"]:
                new_pro={
                    "name":pro,
                    "path":self.config["projects"][pro]
                }
                new_projects.append(new_pro)
            self.config.update({"projects":new_projects})

        if "proxy" in self.config:
            self.config["requests"]["proxy"]=self.config["proxy"]
            self.config.pop("proxy")

        self.config = mergeDict(self.default,self.config)
        self.configfile.dumpconfig(self.config)


        Updater.setBins(self.config["binarys"]["aria2c"],self.config["binarys"]["7z"])
        Updater.setAria2Rpc(self.config["aria2"]["ip"], self.config["aria2"]
                            ["rpc-listen-port"], self.config["aria2"]["rpc-secret"])
        Updater.setDefaults(self.config["defaults"])
        setRequestsArgs(self.config["requests"]["proxy"],self.config["requests"]["retry"],self.config["requests"]["timeout"])
        if self.config["aria2"]["ip"] == "127.0.0.1" or self.config["aria2"]["ip"] == "localhost" or self.config["aria2"]["ip"] == "127.1":
            pass
        else:
            try:
                Updater.setRemoteAria2(self.config["aria2"]["remote-dir"],self.config["aria2"]["local-dir"])
            except KeyError:
                raise KeyError("you must set remote-dir and local-dir to use remote aria2")

    def addProject(self, project, path, add2conf=False):
        pro={
            "name":project,
            "path":path
        }
        self.config["projects"].append(pro)
        if add2conf:
            self.configfile.dumpconfig(self.config)

    def runUpdate(self, projects=None, force=False):
        updaters = []

        for pro in self.config["projects"]:
            if projects==None or pro["name"] in projects:
                obj = Updater(pro["name"], pro["path"])
                updaters.append(obj)

        for pro in updaters:
            pro.run(force)
        Updater.quitAriaRpc()


@click.command()
@click.argument('projects', nargs=-1)
@click.option('--path', type=str, help='the path you want to add')
@click.option('-c',"--conf", type=str, help='using specific config file',default="config.json")
@click.option(
    '--force', '-f', default=False,
    type=click.BOOL, is_flag=True,
    help='force update')
@click.option(
    '--add2conf', '-a', default=False,
    type=click.BOOL, is_flag=True,
    help='add current project path to conf')
@click.option(
    '--wait', '-w', default=False,
    type=click.BOOL, is_flag=True,
    help='wait to exit')
def main(projects, path, force, wait, conf, add2conf):
    
    start = Main(conf=conf)
    if len(projects) == 0:
        start.runUpdate(force=force)
    if not path:
        start.runUpdate(projects=projects, force=force)
    else:
        if len(projects) == 1:
            start.addProject(projects[0], path, add2conf)
            start.runUpdate(projects=projects, force=force)
        else:
            print("error")
    
    if wait:
        os.system("pause")

if __name__ == '__main__':
    main()
