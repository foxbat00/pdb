

-- Don't run this or it will wipe everything and re-initialize it.

--ignore errors from these statements if this is your first run
DROP TABLE file CASCADE;
DROP TABLE file_inst CASCADE;
DROP TABLE repository CASCADE;

CREATE TABLE repository (
    id			serial		PRIMARY KEY,
    path		varchar(500)	NOT NULL
);
    


CREATE TABLE file (
    id			serial		PRIMARY KEY,
    md5hash		varchar(200)	NOT NULL,
    comb_raw_tokens	varchar(500)	,
    display_name	varchar(200)	NOT NULL,
    size		bigint		NOT NULL,
    last_crawled	date		NOT NULL,
    CONSTRAINT file_hash_size_unique UNIQUE(md5hash,size)
);



CREATE TABLE file_inst (
    id			serial		PRIMARY KEY,
    name 		varchar(200) 	NOT NULL,
    repository		int		REFERENCES repository,
    path 		varchar(500) 	, -- relative to repository
    deleted_on		date		,
    marked_delete	boolean		NOT NULL,
    processed		boolean		NOT NULL,
    last_seen		date		NOT NULL,
    file		int		REFERENCES file
);




