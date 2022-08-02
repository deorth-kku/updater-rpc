#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import os
import click
from updater import Updater
from utils import JsonConfig
import logging
from utils import my_log_settings


class Main:
    default = {
        "aria2": {
            "ip": "127.0.0.1",
            "rpc-listen-port": "6800",
            "rpc-secret": ""
        },
        "binarys": {
            "aria2c": "aria2c",
            "libarchive": None
        },
        "requests": {
            "proxy": "",
            "timeout": 30,
            "retry": 5
        },
        "projects": [],
        "defaults": {}
    }

    def __init__(self, conf="config.json"):
        os.chdir(sys.path[0])
        self.configpath = conf
        if not os.path.exists(self.configpath):
            configdir_upper = os.getenv("APPDATA")
            if configdir_upper == None:
                configdir_upper = os.path.join(os.getenv("HOME"), ".config")
            configdir = os.path.join(configdir_upper, "updater-rpc")
            try:
                os.makedirs(configdir)
            except FileExistsError:
                pass
            self.configpath = os.path.join(configdir, "config.json")
        self.config = JsonConfig(self.configpath)

        if "projects" in self.config and type(self.config["projects"]) == dict:
            new_projects = []
            for pro in self.config["projects"]:
                new_pro = {
                    "name": pro,
                    "path": self.config["projects"][pro]
                }
                new_projects.append(new_pro)
            self.config.update({"projects": new_projects})

        if "proxy" in self.config:
            self.config["requests"]["proxy"] = self.config["proxy"]
            self.config.pop("proxy")

        self.config.set_defaults(self.default)
        self.config.dumpconfig()

        Updater.setBins(self.config["binarys"]
                        ["aria2c"], self.config["binarys"]["libarchive"])
        Updater.setAria2Rpc(self.config["aria2"]["ip"], self.config["aria2"]
                            ["rpc-listen-port"], self.config["aria2"]["rpc-secret"])
        Updater.setDefaults(self.config["defaults"])
        Updater.setRequestsArgs(
            self.config["requests"]["retry"], self.config["requests"]["timeout"])

        if self.config["aria2"]["ip"] == "127.0.0.1" or self.config["aria2"]["ip"] == "localhost" or self.config["aria2"]["ip"] == "127.1":
            pass
        else:
            try:
                Updater.setRemoteAria2(
                    self.config["aria2"]["remote-dir"], self.config["aria2"]["local-dir"])
            except KeyError:
                raise KeyError(
                    "you must set remote-dir and local-dir to use remote aria2")

    def addProject(self, project, path, add2conf=False):
        for pro in self.config["projects"]:
            if pro["name"] == project:
                self.config["projects"].remove(pro)
                break
        pro = {
            "name": project,
            "path": path
        }
        self.config["projects"].append(pro)
        if add2conf:
            self.config.dumpconfig()

    def runUpdate(self, projects=None, force=False):
        # always update libarchive_win first to avoid update failure cause by file occupation
        for pro in self.config["projects"]:
            if pro["name"] == "libarchive_win":
                self.config["projects"].remove(pro)
                self.config["projects"].insert(0, pro)

        for pro in self.config["projects"]:
            try:
                if pro["hold"] and not force:
                    continue
            except KeyError:
                pass
            try:
                pro["currentVersion"]
            except KeyError:
                pro.update({"currentVersion": ""})
            if projects == None or pro["name"] in projects:
                try:
                    pro_proxy = pro["proxy"]
                except KeyError:
                    pro_proxy = self.config["requests"]["proxy"]
                obj = Updater(pro["name"], pro["path"],
                              pro_proxy, self.config["requests"]["retry"], pro.get("override", {}))
                try:
                    new_version = obj.run(force, pro["currentVersion"])
                except Exception as e:
                    logging.error(
                        "update for %s failed, see log below" % obj.name)
                    logging.exception(e)
                    if logging.root.isEnabledFor(logging.DEBUG):
                        raise e
                    else:
                        continue
                if new_version:
                    pro_index = self.config["projects"].index(pro)
                    self.config["projects"][pro_index].update(
                        {"currentVersion": new_version})
                    self.config.dumpconfig()
                    try:
                        for line in pro["post-cmds"]:
                            line = line.replace("%PATH", '"%s"' % pro["path"])
                            line = line.replace("%NAME", pro["name"])
                            os.system(line)
                    except KeyError:
                        pass

    def __del__(self):
        logging.debug("__del__ method for Main obj %s has been called" % self)
        Updater.aria2.quit()


@click.command()
@click.argument('projects', nargs=-1)
@click.option('--path', "--install-path", type=click.Path(), help='the install path for added project')
@click.option('-c', "--conf", type=click.Path(), help='using specific config file', default="config.json")
@click.option('-l', "--log-file", type=click.Path(), help='using specific log file', default=None)
@click.option("--log-level", type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False), help='using specific log level', default="INFO")
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
def main(projects, path, force, wait, conf, add2conf, log_file, log_level):
    my_log_settings(log_file, log_level)

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
