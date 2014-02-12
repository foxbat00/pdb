

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
    tokens		tsvector	,
    wordbag		text		NOT NULL DEFAULT '',
    display_name	varchar(200)	NOT NULL,
    size		bigint		NOT NULL,
    last_crawled	date		NOT NULL,
    CONSTRAINT file_hash_size_unique UNIQUE(md5hash,size)
);



CREATE TABLE file_inst (
    id			serial		PRIMARY KEY,
    name 		text	 	NOT NULL,
    repository		int		REFERENCES repository,
    path 		text	 	NOT NULL, -- relative to repository
    deleted_on		date		NOT NULL DEFAULT '',
    marked_delete	boolean		NOT NULL,
    processed		boolean		NOT NULL,
    last_seen		date		NOT NULL,
    file		int		REFERENCES file
);



CREATE TABLE scene (
    id			serial		PRIMARY KEY,
    wordbag		text		NOT NULL,
    rating		int		,
    series		text		,
    series_number	int		,
    label		text		,

)



CREATE TABLE tag (
    id			serial		PRIMARY KEY,
    name		varchar(20)	NOT NULL,
    restricted		boolean		NOT NULL
)

CREATE TABLE star (
    id			serial		PRIMARY KEY,
    name		varchar(40)	NOT NULL,
    gender		varchar(3)	NOT NULL
)

CREATE TABLE scene_file (
    scene_id		int		REFERENCES scene,
    file_id		int		REFERENCES file,
    scene_number	int		,
    tentative		boolean		NOT NULL,
    negated		boolean		NOT NULL,
    CONSTRAINT scene_file_pkey PRIMARY KEY (scene_id, file_id)
)

CREATE TABLE scene_tag (
    scene_id		int		REFERENCES scene,
    tag_id		int		REFERENCES tag,
    tentative		boolean		NOT NULL,
    negated		boolean		NOT NULL,
    CONSTRAINT scene_tag_pkey PRIMARY KEY (scene_id, tag_id)
)


CREATE TABLE scene_star (
    scene_id		int		REFERENCES scene,
    star_id		int		REFERENCES star,
    tentative		boolean		NOT NULL,
    negated		boolean		NOT NULL,
    CONSTRAINT scene_star_pkey PRIMARY KEY (scene_id,star_id)
)

CREATE TABLE alias (
    id			serial		PRIMARY KEY,
    alias		varchar(200)	NOT NULL
)

CREATE TABLE label (
    id			serial		PRIMARY KEY,
    label		varchar(200)	NOT NULL
)

CREATE TABLE series (
    id			serial		PRIMARY KEY,
    series		varchar(200)	NOT NULL
)

CREATE TABLE alias_star (
    alias_id		int		REFERENCES alias,
    star_id		int		REFERENCES  star,
    tentative		boolean		NOT NULL,
    negated		boolean		NOT NULL,
    CONSTRAINT alias_star_pkey PRIMARY KEY (alias_id,star_id)
)


CREATE TABLE alias_label (
    alias_id		int		REFERENCES alias,
    label_id		int		REFERENCES  label,
    tentative		boolean		NOT NULL,
    negated		boolean		NOT NULL,
    CONSTRAINT alias_lsabel_pkey PRIMARY KEY (alias_id,label_id)
)

CREATE TABLE alias_series (
    alias_id		int		REFERENCES alias,
    series_id		int		REFERENCES  series,
    tentative		boolean		NOT NULL,
    negated		boolean		NOT NULL,
    CONSTRAINT alias_series_pkey PRIMARY KEY (alias_id,series_id)
)

 -- TODO constrain alias table to be referenced in one of the mapping tables


--------------------

    

--  get the set of active files

CREATE FUNCTION active_scenes () RETURNS SET OF scene AS '
    SELECT DISTINCT * FROM scene
    JOIN scene_file ON (scene_file.scene_id = scene.id)
    JOIN file ON (scene_file.file_id = file.id)
    JOIN file_inst ON (file_inst.file = file.id)
    WHERE file_inst.marked_delete = 'f' AND file_inst.deleted_on IS NULL
'  LANGUAGE sql;   --plpgsql;


--  get the set of active files

CREATE FUNCTION active_files () RETURNS SET OF file AS '
    SELECT DISTINCT * FROM file
    JOIN file_inst ON (file_inst.file = file.id)
    WHERE file_inst.marked_delete = 'f' AND file_inst.deleted_on IS NULL
'  LANGUAGE sql;   --plpgsql;



--------------------

CREATE FUNCTION update_tsv () AS '
    UPDDATE file SET tokens = to_tsvector(s.tokens)
    FROM (
	SELECT file.id, STRING_AGG(file_inst.path, ' ') || ' ' || STRING_AGG(file_inst.name, ' ') 
	    || file.wordbag tokens
	FROM file
	INNER JOIN file_inst ON(file_inst.file = file.id)
	GROUP BYfile.id
    ) s WHERE file.id = s.id
'  LANGUAGE sql;
