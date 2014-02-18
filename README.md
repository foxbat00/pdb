pdb
===


A DDL and python crawler to build a database of video files, and a python/flask/pjax/jquery website to browse, view, and organize the fies.

The database allows searches across multiple libraries on different volumes, allow easy detection of potential duplicate files across those volumes, and serve as a base upon which to build a richer metadata layer of scenes.

The flexible mapping of Scenes to Files allows for both multiple files belonging to a single scene, and a single file containing multiple scenes.

Star, label, tag, and series metadata categorize the Scenes and provide for faceted searching.

Provided is:

crawler.py:	crawls sections of filesystem (Repositories) to add FileInsts and Files. Also generates
		Scenes for Files.  Files are defined by unique (file size, md5).  The Scene - File relationship
		is many-to-many.
db.py:          holds db connections and table definitions
testdb.py:      loads the db and leaves you with interactive prompt to run queries and debug
psearch.py:     search filenames across db from command line
app:		flask / pjax web app for browsingk, tagging, managing, etc.
tagger.py:	uses Alias to associates Stars, Labels, Series with various Scenes.  Also applies Implications.
rules-loader.py:  loads specially formatted rules defintion 




The system comprises:

  - Repository:  a location of your files.  You can change the location of a Repository if you, e.g., move a drive.
  
  - FileInst:  a particular file at a particular location with a specific name
  
  - File: as defined by a filesize and md5checksum. Thus a File may have multiple FileInsts in different Repositories.
  
  - Scene:  in a many-to-many relationship with File. Scenes have a Label, Series, and may be associated with many Tags and/or Stars

  - Stars, Tags, Labels, Series (i.e. the facets).  Each has a name, and a primary table, pluas Alias[Facet] table to indicate association with an alias, and an Scene[Facet] table to indicate association with a Scene.

  - FacetImplic:  allows one facet (tag, star, etc.) to automatically imply association of a specific value for another facet.  E.g. star  "Jet Li" implies tag:Action  or  star "Carrie Fisher" implies series:"Star Wars"



During a crawl, FileInsts that are no longer present are markded deleted, but the FileInst and File record remain to detect future duplicates.




