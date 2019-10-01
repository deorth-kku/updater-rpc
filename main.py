#!/usr/bin/python3
# -*- coding: utf-8 -*-

from updater import *

        
        
if __name__ == '__main__':
    update=Updater(sys.argv[1],sys.argv[2])
    update.run(True)
