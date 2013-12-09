pdb
===


A DDL and python crawler to build a database of video files.  

The system comprises:

  - Repository:  a location of your files.  You can change the location of a Repository if you, e.g., move a drive.
  
  - FileInst:  a particular file at a particular location with a specific name
  
  - File: as defined by a filesize and md5checksum. Thus a File may have multiple FileInsts in different Repositories.
  

During a crawl, FileInsts that are no longer present are markded deleted, but the FileInst and File record remain to detect future duplicates.

The resultant database will allow searches across multiple libraries on different volumes, allow easy detection of potential duplicate files across those volumes, and serve as a base upon which to build a richer metadata layer.
