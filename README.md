# WARNING
This is a self-use purpose project with all kinds of problems including but no limited:
* Lack of testing
* Not documented feature/behavior
* Grammar error/typo  
So long these problems do not effect my daliy uses, I'm lack of the willpower to fix them.
# Interduction
Updater for opensource projects which don't have buildin update.
## How does it work?
We use RESTful apis to get the lastest release of the project.  
Currently using github api and appveyor api. If you want any other api added, feel free to open an issue.  
Download is using aria2 via rpc interface, ~~decompress using 7z binary~~. Current both binary file is not included, but I'm planning to add auto download for both if either of them wasn't found in PATH.
## Dependency
### Python
Python 3.9+ with "requests", "psutil", "libarchive-c" and "click" installed. To use "use_exe_version", you'll also need "pefile". To use sourceforge, you'll need "xmltodict". Install them with pip. 
### Binary program
aria2 and ~~7z~~ libarchive binary  in your $PATH. Or you can set the full path in config.json. Suggested way to install them is through the package manager from your distro. 
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
* ~~fix libarchive update~~
* fix corrupted download file detection
* ~~Global log level~~
* Multi-thread
* ~~Sourceforge support~~
* ~~Static url (version by regex maybe)~~
* rollback (via local file or redownload)
* get version via command line
* search same download quest before adding
* ~~restart command override~~
* show release notes
* ~~skip decompress(single file mode)~~
* ~~user override config~~
* ~~create F-droid repository for android update~~(use offical fdroidserver program instead)
* global download dir for local aria2
* add --allow-overwrite
* ~~popup message on windows when restart process is not allowed~~
* pypi packaging
* update this readme. tons of new feature is not documented
* add sourceforge search path
* fix amd driver decompress
### online config downloading (which require to store configs json elsewhere)
* ~~metadata.json: contain version(date) of the project-config.json, use project-name as key?~~
* ~~project-config.json: needs a config_json_ver (and check it before runs update)~~
* ~~dir structure: may want to add a categroy dir, so it will need to storage full path of project-config.json in metadata.json as well.~~
* ~~local metadata: storage in config.json? but this will not be very convenient when it comes to pass the project-config.json ver. ~~
* ~~create a new repo for project config and move project config in readme to it.~~
* redownload on broken config file
* ~~handle exception during updater__init__ in Main~~
### utils rework
* ~~utils as a submodule~~
* ~~improve JsonConfig for file not exist/invalid behavior~~
* ~~rework Py7z using native python library~~
### long-term (maybe on 0.0.3)
* GUI (probably pyQT)
* version selection
* Muti-language
* self-update
* rework command line interface: use sub-command




