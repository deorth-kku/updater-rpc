#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import click
from updater import Updater
from utils import LoadConfig


class Main:
    def __init__(self):
        self.configfile = LoadConfig("config.json")
        self.config = self.configfile.config
        if self.config == {}:
            self.config = {
                "aria2": {
                    "ip": "127.0.0.1",
                    "rpc-listen-port": "6800",
                    "rpc-secret": ""
                },
                "projects": {},
                "defaults": {}
            }
            self.configfile.dumpconfig(self.config)

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
def main(projects, path, force):

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


if __name__ == '__main__':
    main()
