#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import os
import click
from updater import Updater
from utils import JsonConfig
import logging
from typing import Iterable
from utils import MyLogSettings, ExceptionLogger, InstanceLock


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
        "repository": [],
        "defaults": {}
    }

    @staticmethod
    def sel_conf_json():
        configpath = os.path.join(sys.path[0], "config.json")
        if not os.path.exists(configpath):
            configdir_upper = os.getenv("APPDATA")
            if configdir_upper == None:
                configdir_upper = os.path.join(os.getenv("HOME"), ".config")
            configdir = os.path.join(configdir_upper, "updater-rpc")
            try:
                os.makedirs(configdir)
            except FileExistsError:
                pass
            configpath = os.path.join(configdir, "config.json")
        return configpath

    def __init__(self, conf="config.json"):
        os.chdir(sys.path[0])
        self.config = JsonConfig(conf)

        # compatibility code, will remove in the future
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
            self.config["requests"]["retry"], self.config["requests"]["timeout"], self.config["requests"]["proxy"])
        Updater.setLocalConfigDir(os.path.join(
            os.path.dirname(conf), "config"))

        # build-in repo
        if self.config["repository"] == []:
            self.config["repository"] += [
                "https://raw.githubusercontent.com/deorth-kku/updater-config/master"]

        Updater.addRepos(*self.config["repository"])

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

    def runUpdate(self, projects: Iterable[str] = None, force: bool = False) -> None:
        # always update libarchive_win first to avoid update failure cause by file occupation
        for pro in self.config["projects"]:
            if pro["name"] == "libarchive_win":
                self.config["projects"].remove(pro)
                self.config["projects"].insert(0, pro)

        if projects == None:
            run_projects = self.config["projects"]
        else:
            projects = list(projects)
            run_projects = []
            for pro in self.config["projects"]:
                if pro["name"] in projects:
                    run_projects.append(pro)
                    projects.remove(pro["name"])
            for name in projects:
                logging.warning(
                    "\"%s\" not found in config.json, skipping" % name)

        for pro in run_projects:
            pro: dict
            if pro.get("hold", False) and not force:
                logging.info(
                    "%s has been set to hold, skipping update" % pro["name"])
                continue

            pro_proxy = pro.get("proxy", self.config["requests"]["proxy"])

            try:
                obj = Updater(pro["name"], pro["path"],
                              pro_proxy, self.config["requests"]["retry"], pro.get("override", {}))
                new_version = obj.run(force, pro.get("currentVersion", ""))
            except Exception as e:
                logging.error(
                    "update for \"%s\" failed, cause: %s" % (pro["name"], e))
                if logging.root.isEnabledFor(logging.DEBUG):
                    logging.exception(e)
                    raise e
                else:
                    continue
            if new_version:
                pro_index = self.config["projects"].index(pro)
                self.config["projects"][pro_index].update(
                    {"currentVersion": new_version})
                self.config.dumpconfig()

                for line in pro.get("post-cmds", tuple()):
                    line = line.replace("%PATH", '"%s"' % pro["path"])
                    line = line.replace("%NAME", pro["name"])
                    line = line.replace("%DL_FILENAME", obj.fullfilename)
                    os.system(line)

    def __del__(self):
        logging.debug("__del__ method for Main obj %s has been called" % self)
        Updater.aria2.quit()


@click.command()
@click.argument('projects', nargs=-1)
@click.option('--path', "--install-path", type=click.Path(), help='the install path for added project')
@click.option('-c', "--conf", type=click.Path(), help='using specific config file', default=Main.sel_conf_json(), show_default=True)
@MyLogSettings()
@click.option(
    '--force', '-f', default=False,
    type=click.BOOL, is_flag=True,
    help='force update', show_default=True)
@click.option(
    '--add2conf', '-a', default=False,
    type=click.BOOL, is_flag=True,
    help='add current project path to conf', show_default=True)
@click.option(
    '--wait', '-w', default=False,
    type=click.BOOL, is_flag=True,
    help='wait to exit', show_default=True)
@ExceptionLogger()
@InstanceLock(None, sys.exit, 1)
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
