# English
Updater for opensource projects which don't have buildin update.
## How does it work?
We use RESTful apis to get the lastest release of the project.  
Currently using github api and appveyor api. If you want any other api added, feel free to open an issue.  
Download is using aria2 via rpc interface, decompress using 7z binary. Current both binary file is not included, but I'm planning to add auto download for both if either of them wasn't found in PATH.
## Dependency
### Python
Python 3 with "requests", "psutil" and "click" installed. To use "use_exe_version", you'll also need "pefile".
### Binary program
aria2 and 7z binary in your $PATH. Or you can set the full path in config.json.  
## Config file
As you might noticed, we use json as config file. Though making a config file, you can provide the infromaion that is needed to update your local program.  
There are already a few config file I wrote for projects that I use. If you make some others, feel free to make a PR.
## Options
### "basic": Must-include options 
You must include these options in your config file, otherwise it won't work at all.  
* "api_type": Currently you can only use "github" or "appveyor".
* "account_name": the owner account name of the project.  
* "project_name": the project name of the project. For github, it is the repository name. Please notice some project use a different repository to release binary like rpcs3.
### Selective options
There is a default value for these options. If you don't previde any, the default value will be used.  
#### "build": Build/release options
These are option to select the build/release to download. 
* "branch": For appveyor api, select build from specific branch. If "None" was given, it will download the lastest build from any branch. The default is "None". This option has no effect to github api.
* "no_pull": For appveyor api. If you specific a branch, and other branch merged a pull request to this branch, it will trigger a build on appveyor. You might not want to use this build. The default is "None". This option has no effect to github api.
#### "download": Download options
These are option that control which file to download when there are more than one file in a build/release. If these are still more than one file after all these options, the first file will be download.
* "keyword": Only download file which its filename includes such keywords. Default is a empty list.
* "update_keyword": Some project provide a update-only pack. Use this to download it instead of downloading full pack. If not set, will always download the full pack. 
* "exclude_keyword": Don't download file which its filename includes such keywords. Default is a empty list.
* "filetype": Only download file which its filename use specific suffix. Default is "7z".
* "add_version_to_filename": Add version to download filename. for some project doesn't contain version in there release file. Default is False.    
#### "process": Process options
These are option that control how this program behave when the program you want to update is running.
* "image_name": The process name to search for. Default is the name of config file + ".exe"
* "allow_restart": Control whether you want to auto restart the process to continue update progress. If it set to false, It will wait you manully end the process.
#### "decompress": Decompress/extract options
These are option that control how to decompress the downloaded file.
* "include_file_type": Only decompress files with specific suffix. Needs to be a list. Default is a empty list [].
* "exclude_file_type": Don't decompress files with specific suffix. Needs to be a list. Default is a empty list [].
* "exclude_file_type_when_update": Don't decompress files with specific suffix when updating. Needs to be a list. Default is a empty list [].
* "single_dir": If download file contain only one directory and this is set to true, move files from the directory to upper level directory (which is the program directory). If you want only one directory form the compressed file, set this to the directory name. Default is true.
* "keep_download_file": Keep compress file after decompression. If it set to false, compress file will be deleted. Default is true.
#### "version": Version contorl options
* "use_exe_version": Use win32 PE(Portable Executable) version info instead of version file. Won't work on projects unless its exe contain win32 PE version info. I made this for DS4windows. Default is false.
### config vars
You can use some vars in config file in order to use the same config file for different platform. Experimental, currently the best way to support different platfrom is to use different config file.
* %OS : The operate system of current platform. On Windows it will shows "windows" and on Linux it will shows "linux". Haven't tested on other systems.  
* %arch : The cpu architecture of current platform. Windows will shows "x86" and "x64", on Linux will shows as your uname. Won't work on other systems.
## Command-line interface
We use main.py as a command-line interface. For Windows, use "python main.py". For other OS, just use "./main.py".
## Add a local folder and project to project list:
`python main.py [project_name] --path=[local_folder]`  
You must have the correct config file named [project_name].json in ./config dir.  
After adding the project in your project list, it will automaticly update the project.
## Update all the projects in your project list:
Just run  
`python main.py`
## Update only specific projects:
`python main.py [project_name] [another_project_name] [some_more_project_name] ...`  
These project names must already included in your project list.
## TODOs
* Global log level
* Muti-thread
* Sourceforge support
* version selection
* Muti-language
* self-update
* Static url
* search same download quest before adding
* restart command override
* show release notes



