#Purpose: creates a repo-processing script to download the traget github repo if it is not already downloaded
#By: Bharath Nagam, Jul 18

import os
import git
import shutil
from pathlib import Path
class repo_processor():
    def __init__(self):
        self.target_repo = "https://github.com/patkel/turbo_telescope" #Address
        self.clone_path = "/home/bcn/Work/PostDoc/"
        self.clone_location = "/home/bcn/Work/PostDoc/turbo_telescope-master/"  #clone location


        # Download repo is it does not exist
        print("!!!!!!! Step 1: Cloning Repo !!!!!!!!!!!!!")
        self.clone_repo()
    
    def clone_repo(self):
        if os.path.exists(self.clone_location):
            print("Path already exists: {}".format(self.clone_location))
            print("!!!Cloning Done!!!!")
            return
        print("Processing cloning repo: {} to : {}".format(self.target_repo, self.clone_path))
        git.Repo.clone_from(self.target_repo,self.clone_path)
        print("!!!Cloning Done!!!!")
    
    def should_process_file(self, file_path: Path) -> bool:
        # Placeholder for file processing logic
        print("Processing files in the cloned repository...")
        # Implement file processing logic here
        skip_file_extension = {'.idx', '.pack', '.pyc', '.rev', '.sample'} # I read through the repo and found these files were not reuired
        skip_file_folders = {'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env'}  # Folders to skip

        for part in file_path.parts:
            if part in skip_file_folders:
                print(f"Skipping folder: {part}")
                return False
        if file_path.suffix in skip_file_extension:
            print(f"Skipping file: {file_path.name}")
            return False    
        return True

    
