#Purpose: creates a repo-processing script to download the traget github repo if it is not already downloaded
#By: Bharath Nagam, Jul 18

import os
import git

class repo_processor():
    def __init__(self):
        self.target_repo = "https://github.com/patkel/turbo_telescope" #Address
        self.clone_location = "home/bcn/Work/PostDoc/turbo_telescope-master"  #clone location


        # Download repo is it does not exist
        self.download_repo()
    
