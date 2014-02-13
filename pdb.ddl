

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
    --tsv			tsvector	,
    wordbag		text		NOT NULL DEFAULT '',
    display_name	varchar(200)	NOT NULL,
    size		bigint		NOT NULL,
    last_crawled	date		NOT NULL,
    CONSTRAINT file_hash_size_unique UNIQUE(md5hash,size)
);



CREATE TABLE file_inst (
    id			serial		PRIMARY KEY,
    name 		text	 	NOT NULL,
    repository		int		NOT NULL REFERENCES repository,
    path 		text	 	NOT NULL, -- relative to repository
    deleted_on		date		NOT NULL DEFAULT '',
    marked_delete	boolean		NOT NULL,
    processed		boolean		NOT NULL,
    last_seen		date		NOT NULL,
    file		int		NOT NULL REFERENCES file
);



CREATE TABLE scene (
    id			serial		PRIMARY KEY,
    wordbag		text		NOT NULL,
    tsv			tsvector	,
    rating		int		,
    series		text		,
    series_number	int		,
    label		text		
);



CREATE TABLE tag (
    id			serial		PRIMARY KEY,
    name		varchar(20)	NOT NULL,
    restricted		boolean		NOT NULL
);

CREATE TABLE star (
    id			serial		PRIMARY KEY,
    name		text		NOT NULL,
    gender		varchar(3)	NOT NULL
);

CREATE TABLE scene_file (
    scene_id		int		NOT NULL REFERENCES scene,
    file_id		int		REFERENCES file,
    scene_number	int		,
    tentative		boolean		NOT NULL DEFAULT 't',
    negated		boolean		NOT NULL DEFAULT 'f',
    CONSTRAINT scene_file_pkey PRIMARY KEY (scene_id, file_id)
);

CREATE TABLE scene_tag (
    scene_id		int		NOT NULL REFERENCES scene,
    tag_id		int		NOT NULL REFERENCES tag,
    tentative		boolean		NOT NULL DEFAULT 't',
    negated		boolean		NOT NULL DEFAULT 'f',
    CONSTRAINT scene_tag_pkey PRIMARY KEY (scene_id, tag_id)
);


CREATE TABLE scene_star (
    scene_id		int		NOT NULL REFERENCES scene,
    star_id		int		NOT NULL REFERENCES star,
    tentative		boolean		NOT NULL DEFAULT 't',
    negated		boolean		NOT NULL DEFAULT 'f',
    CONSTRAINT scene_star_pkey PRIMARY KEY (scene_id,star_id)
);

CREATE TABLE alias (
    id			serial		PRIMARY KEY,
    name		text		NOT NULL
);

CREATE TABLE label (
    id			serial		PRIMARY KEY,
    name		name		NOT NULL
);

CREATE TABLE series (
    id			serial		PRIMARY KEY,
    name		text		NOT NULL
);

CREATE TABLE alias_star (
    alias_id		int		NOT NULL REFERENCES alias,
    star_id		int		NOT NULL REFERENCES  star,
    tentative		boolean		NOT NULL DEFAULT 't',
    negated		boolean		NOT NULL DEFAULT 'f',
    CONSTRAINT alias_star_pkey PRIMARY KEY (alias_id,star_id)
);


CREATE TABLE alias_label (
    alias_id		int		NOT NULL REFERENCES alias,
    label_id		int		NOT NULL REFERENCES  label,
    tentative		boolean		NOT NULL DEFAULT 't',
    negated		boolean		NOT NULL DEFAULT 'f',
    CONSTRAINT alias_lsabel_pkey PRIMARY KEY (alias_id,label_id)
);

CREATE TABLE alias_series (
    alias_id		int		NOT NULL REFERENCES alias,
    series_id		int		NOT NULL REFERENCES  series,
    tentative		boolean		NOT NULL DEFAULT 't',
    negated		boolean		NOT NULL DEFAULT 'f',
    CONSTRAINT alias_series_pkey PRIMARY KEY (alias_id,series_id)
);

 -- TODO constrain alias table to be referenced in one of the mapping tables



CREATE TABLE tag_rules (
    id			serial		PRIMARY KEY,
    condition		text		NOT NULL,
    condition_type	VARCHAR(10)	NOT NULL,
    tag_id		int		NOT NULL REFERENCES tag,
    active		boolean		NOT NULL DEFAULT 't',
    exclude		boolean		NOT NULL DEFAULT 'f'
);


CREATE TABLE tag_implications (
    id			serial		PRIMARY KEY,
    predicate		int		NOT NULL REFERENCES tag,
    implied		int		NOT NULL REFERENCES tag,
    active		boolean		NOT NULL DEFAULT 't'
);


--------------------

    

--  get the set of active scenes

CREATE FUNCTION active_scenes () RETURNS SETOF scene AS $$
    SELECT * FROM scene
    where EXISTS (
	SELECT * FROM scene
	JOIN scene_file ON (scene_file.scene_id = scene.id)
	JOIN file ON (scene_file.file_id = file.id)
	JOIN file_inst ON (file_inst.file = file.id)
	WHERE file_inst.marked_delete = 'f' AND file_inst.deleted_on IS NULL
    )
$$  LANGUAGE sql;   --plpgsql;


--  get the set of active files

CREATE FUNCTION active_files () RETURNS SETOF file AS $$
    SELECT * FROM file
    WHERE EXISTS(
	SELECT * FROM file JOIN file_inst ON (file_inst.file = file.id) 
	    WHERE file_inst.marked_delete = 'f' AND file_inst.deleted_on IS NULL
	)
$$  LANGUAGE sql;   --plpgsql;


CREATE FUNCTION get_words_for_scene (int) RETURNS TEXT AS $A$
    SELECT STRING_AGG(file_inst.path, ' ') || ' ' || STRING_AGG(file_inst.name, ' ') 
	|| ' ' || STRING_AGG(file.wordbag, ' ')  || ' ' || scene.wordbag
	FROM scene
	JOIN scene_file ON (scene_file.scene_id = scene.id)
	JOIN file ON (scene_file.file_id = file.id)
	JOIN file_inst ON (file_inst.file = file.id)
	WHERE scene.id = $1
	GROUP BY scene.wordbag
$A$ LANGUAGE sql;
    


CREATE OR REPLACE FUNCTION concat_tsvectors(tsv1 tsvector, tsv2 tsvector)
RETURNS tsvector AS $$
BEGIN
  RETURN coalesce(tsv1, to_tsvector('default', ''))
      || coalesce(tsv2, to_tsvector('default', ''));
END;
$$ LANGUAGE plpgsql;
 
CREATE AGGREGATE tsvector_agg (
  BASETYPE = tsvector,
  SFUNC = concat_tsvectors,
  STYPE = tsvector,
  INITCOND = ''
);



CREATE FUNCTION update_scene_tsv () RETURNS TRIGGER AS $A$
    DECLARE 
	words text;
    BEGIN
    EXECUTE $B$
	SELECT STRING_AGG(file_inst.path, ' ') || ' ' || STRING_AGG(file_inst.name, ' ') 
	    || ' ' || STRING_AGG(file.wordbag, ' ')  || ' ' || OLD.wordbag
	    FROM scene, scene_file, file, file_inst
	    WHERE scene.id = scene_file.scene_id 
	    AND file.id = scene_file.file_id
	    AND file_inst.file = file.id
    $B$  into words;
    NEW.tsv = to_tsvector(words);
    return NEW;
    END;
$A$ LANGUAGE plpgsql;





CREATE TRIGGER update_scene_tsv AFTER 
    INSERT OR UPDATE ON scene 
FOR EACH ROW EXECUTE PROCEDURE update_scene_tsv();

CREATE TRIGGER update_scene_tsv AFTER 
    INSERT OR UPDATE ON scene_file
FOR EACH ROW EXECUTE PROCEDURE update_scene_tsv();

CREATE TRIGGER update_scene_tsv AFTER 
    INSERT OR UPDATE OF wordbag ON file
FOR EACH ROW EXECUTE PROCEDURE update_scene_tsv();

CREATE TRIGGER update_scene_tsv AFTER 
    INSERT OR UPDATE OF file ON file_inst
FOR EACH ROW EXECUTE PROCEDURE update_scene_tsv();


