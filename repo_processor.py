#Purpose: creates a repo-processing script to download the traget github repo if it is not already downloaded
#By: Bharath Nagam, Jul 18

import os
import git
import shutil
from pathlib import Path
import chromadb
import hashlib
from typing import List, Dict, Any

class repo_processor():
    def __init__(self, repo_url:str):
        self.target_repo = repo_url #Address
        self.clone_path = "/home/bcn/Work/PostDoc/"
        self.clone_location = "/home/bcn/Work/PostDoc/turbo_telescope-master/"  #clone location

        #chromadb client
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(name="github_repo")


        # Download repo is it does not exist
        print("!!!!!!! Step 1: Cloning Repo !!!!!!!!!!!!!")
        self.clone_repo()
    
    def clone_repo(self):
        """ Clones the target repository to the specified clone path if it does not already exist.
        """
        if os.path.exists(self.clone_location):
            print("Path already exists: {}".format(self.clone_location))
            print("!!!Cloning Done!!!!")
            return
        print("Processing cloning repo: {} to : {}".format(self.target_repo, self.clone_path))
        git.Repo.clone_from(self.target_repo,self.clone_path)
        print("!!!Cloning Done!!!!")
    
    def should_process_file(self, file_path: Path) -> bool:
        """
        Determines if a file should be processed based on its path and extension.
        Args:
            file_path (Path): The path of the file to check.
        Returns:
            bool: True if the file should be processed, False otherwise.
        """
        # Placeholder for file processing logic
        #print("Processing files in the cloned repository...")
        # Implement file processing logic here
        skip_file_extensions = {
        '.idx', '.pack', '.pyc', '.rev', '.sample',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',  
        '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z',              
        '.mp4', '.avi', '.mov', '.wmv', '.mp3', '.wav',            
        '.exe', '.dll', '.so', '.dylib'                            
        }
        skip_file_folders = {'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env', 'wiki_data'}  

        for part in file_path.parts:
            if part in skip_file_folders:
                print(f"Skipping folder: {part}")
                return False
        if file_path.suffix in skip_file_extensions:
            print(f"Skipping file: {file_path.name}")
            return False    
        return True
    
    def get_file_content(self, file_path: Path) -> str:
        """
        Reads the content of a file.
        Args:
            file_path (Path): The path of the file to read.
        Returns:
            str: The content of the file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except (UnicodeError, FileNotFoundError, PermissionError) as e:
            print(f"Error reading file {file_path}: {e}")
            return ""
    
    def get_chunks(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """
        Splits the content into chunks of a specified size.
        Args:
            content (str): The content to split.
            chunk_size (int): The size of each chunk.
        Returns:
            list[str]: A list of content chunks.
        """
        if len(content) < chunk_size:
            return [content]
        
        start = 0
        chunk_list = []

        while start<len(content):
            if start+chunk_size<len(content):
                current_chunk = content[start:start+chunk_size]
            else:
                current_chunk = content[start:]


            chunk_list.append(current_chunk)
            start = start + chunk_size - overlap

        return chunk_list
    
    def process_repo(self):
        """
        Function: processess all files in a repo and makes it as chunk and
        """
        repo_path = Path(self.clone_location)
        

        print(" Processing repo and storing in chroma db ...................")
        documents = []
        metadatas = []
        ids = []
                 
        for file_path in repo_path.rglob("*"):

            if self.should_process_file(file_path=file_path) and file_path.is_file():
                relative_path  = file_path.relative_to(repo_path)
                content = self.get_file_content(file_path=file_path)
                
                if content.strip():
                    chunks = self.get_chunks(content)
                    for i,chunk in enumerate(chunks):
                        chunk_id = hashlib.md5(f"{relative_path}_{i}_{chunk[:100]}".encode()).hexdigest()
                        documents.append(chunk)
                        metadatas.append({'file_path': str(relative_path),'chunk_index': i, 'filetype': file_path.suffix, 'url': self.target_repo}) #add file_path, chunk_index, filetype, repo_url
                        ids.append(chunk_id)
                
        if documents:
            print(" Storing id, documents, metadatas ...................")
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)        

        print(" Removing clone repo ...................")
        shutil.rmtree(self.clone_location)

    def search_similar_to_query(self,query: str, n_results: int = 5) -> List[Dict[str, Any]]:

        results = self.collection.query(query_texts=[query], n_results=n_results)

        return [{
            'content': document,
            'metadata': metadata,
            'score':id
            }
            for document, metadata, id in zip(results['documents'][0], results['metadatas'][0], results['ids'][0])
        ]
    