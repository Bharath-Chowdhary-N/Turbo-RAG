#Purpose: creates a repo-processing script to download the traget github repo if it is not already downloaded
#By: Bharath Nagam, Jul 18

import os
import git
import shutil

class repo_processor():
    def __init__(self):
        self.target_repo = "https://github.com/patkel/turbo_telescope" #Address
        self.clone_path = "home/bcn/Work/PostDoc/"
        self.clone_location = "home/bcn/Work/PostDoc/turbo_telescope-master"  #clone location


        # Download repo is it does not exist
        print("!!!!!!! Step 1: Cloning Repo !!!!!!!!!!!!!")
        self.clone_repo()
    
    def clone_repo(self):
        if os.path.exists(self.clone_location):
            shutil.rmtree(self.clone_location)
        print("Processing cloning repo: {} to : {}".format(self.target_repo), self.clone_path)
        git.Repo.clone_from(self.clone_repo,self.clone_location)
        print("!!!Cloning Done!!!!")

    
