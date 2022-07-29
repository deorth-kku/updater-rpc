#!/bin/python3
import pefile
import libarchive

if __name__ == "__main__":
    file = "/mnt/updater-download/7-zip_win/7z2107-x64.exe"
    
    file = "/mnt/updater-download/git4windows/PortableGit-2.36.1-64-bit.7z.exe"
    file = "/mnt/download/512.95-desktop-win10-win11-64bit-international-dch-whql.exe"
    from utils import Decompress,my_log_settings
    my_log_settings()
    Decompress(file).extractAll("/mnt/temp/decompress")
