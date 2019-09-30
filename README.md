# Updater for opensource projects which don't have buildin update.
## How does it work?
We use RESTful apis to get the lastest release of the project.
Currently using github api and appveyor api. If you want any other api added, feel free to open an issue.
Download is using aria2 via rpc interface, decompress using 7z binary. Current both binary file is not included, but I'm planning to add auto download for both if either of them wasn't found in PATH.
## Config file
As you might noticed, we use json as config file. Though making a config file, you can provide the infromaion that is needed to update your local program.
There are already a few config file I wrote for projects that I use. If you make some others, feel free to make a PR.
## Options
### Must-include options
You must include these options in your config file, otherwise it won't work at all.
* "api_type": Currently you can only use "github" or "appveyor".
* "account_name": the owner account name of the project.
* "project_name": the project name of the project. For github, it is the repository name. Please notice some project use a different repository to release binary like rpcs3.
### Selective options
There is a default value of these options. If you don't previde these, the default value will be used.
#### Build options
These are option to select the build/release to download. 
* "branch": For appveyor api, select build from specific branch. If "None" was given, it will download the lastest build from any branch. The default is "None". This option has no effect to github api.
* "no_pull": For appveyor api. If you specific a branch, and other branch merged a pull request to this branch, it will trigger a build on appveyor. You might not want to use this build. The default is "None". This option has no effect to github api.
#### Download options
These are option that control which file to download when there are more than one file in a build/release. If these are still more than one file after all these options, the first file will be download.
* "keyword": Only download file which its filename includes such keyword. Default is empty.
* "exclude_keyword": Don't download file which its filename includes such keyword. Default is "/" (which is not possible to use in filename).
* "filetype": Only download file which its filename use specific suffix. Default is "7z".
#### Process options
These are option that control how this program behave when the program you want to update is running.
* "image_name": The process name to search for. Default is "project_name" option + ".exe"
* "allow_restart": Control whether you want to auto restart the process to continue update progress. If it set to false, It will wait you manully end the process.
#### Decompress options
These are option that control how to decompress the downloaded file.
* "include_file_type": Only decompress files with specific suffix. Needs to be a list. Default is a empty list [].
* "exclude_file_type": Don't decompress files with specific suffix. Needs to be a list. Default is a empty list [].
* "single_dir": If download file contain only one directory and this is set to true, move files from the directory to upper level directory (which is the program directory). Default is true.
* "keep_download_file": Keep compress file after decompression. If it set to false, compress file will be deleted.

## Usage
Currently you have to modifiy my code to update your program in you disk. That is not user-friendly. So until I change this, no user guide will be written. 


