#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys,os
import click
from updater import Updater
from utils import LoadConfig,mergeDict,setProxy


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
                "proxy":"",
                "projects": {},
                "defaults": {}
            }
    def __init__(self):
        os.chdir(sys.path[0])
        self.configpath="config.json"
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
        self.config = mergeDict(self.default,self.config)
        self.configfile.dumpconfig(self.config)

        setProxy(self.config["proxy"])

        Updater.setBins(self.config["binarys"]["aria2c"],self.config["binarys"]["7z"])
        Updater.setAria2Rpc(self.config["aria2"]["ip"], self.config["aria2"]
                            ["rpc-listen-port"], self.config["aria2"]["rpc-secret"])
        Updater.setDefaults(self.config["defaults"])

    def addProject(self, project, path):
        self.config["projects"].update({project: path})
        self.configfile.dumpconfig(self.config)

    def runUpdate(self, projects=None, force=False):
        updaters = []
        if projects == None:
            for pro in self.config["projects"]:
                obj = Updater(pro, self.config["projects"][pro])
                updaters.append(obj)
        else:
            for pro in projects:
                obj = Updater(pro, self.config["projects"][pro])
                updaters.append(obj)

        for pro in updaters:
            pro.run(force)
        Updater.quitAriaRpc()


@click.command()
@click.argument('projects', nargs=-1)
@click.option('--path', type=str, help='the path you want to add')
@click.option(
    '--force', '-f', default=False,
    type=click.BOOL, is_flag=True,
    help='force update')
@click.option(
    '--wait', '-w', default=False,
    type=click.BOOL, is_flag=True,
    help='wait to exit')
def main(projects, path, force, wait):
    
    start = Main()
    if len(projects) == 0:
        start.runUpdate(force=force)
    if not path:
        start.runUpdate(projects=projects, force=force)
    else:
        if len(projects) == 1:
            start.addProject(projects[0], path)
            start.runUpdate(projects=projects, force=force)
        else:
            print("error")
    
    if wait:
        os.system("pause")

if __name__ == '__main__':
    main()
