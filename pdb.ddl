

-- Don't run this or it will wipe everything and re-initialize it.

--ignore errors from these statements if this is your first run
DROP TABLE file CASCADE;
DROP TABLE file_inst CASCADE;
DROP TABLE repository CASCADE;


------------------------------------------------------------------

--                  TOP LEVEL TABLES			        --

------------------------------------------------------------------


CREATE TABLE repository (
    id			serial		PRIMARY KEY,
    path		varchar(500)	NOT NULL
);
    


CREATE TABLE file_inst (
    id			serial		PRIMARY KEY,
    name 		text	 	NOT NULL,
    repository_id	int		NOT NULL REFERENCES repository,
    path 		text	 	NOT NULL, -- relative to repository
    deleted_on		date		NOT NULL DEFAULT '',
    marked_delete	boolean		NOT NULL,
    processed		boolean		NOT NULL,
    last_seen		date		NOT NULL,
    added_on		date		NOT NULL DEFAULT now(),
    file_id		int		NOT NULL REFERENCES file
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





CREATE TABLE scene (
    id			serial		PRIMARY KEY,
    wordbag		text		NOT NULL DEFAULT '',
    tsv			tsvector	,
    rating		int		,
    series_id		int		REFERENCES series,
    series_number	int		,
    label_id		int		REFERENCES label,
    display_name	text		,
    confirmed		boolean		NOT NULL DEFAULT 'f'
);

CREATE TABLE alias (
    id			serial		PRIMARY KEY,
    name		text		NOT NULL UNIQUE,
    active		boolean		NOT NULL DEFAULT 't'
);



-- don't like the spelling?   http://grammarist.com/usage/forego-forgo/
CREATE TABLE forgone_file (
    id			serial		PRIMARY KEY,
    repository_id	int		REFERENCES repository,
    path		text		NOT NULL,
    name		text		NOT NULL,
    added_on		date		NOT NULL DEFAULT now(),
    last_seen		date		NOT NULL,
    deleted_on		date		
);



-- -- -- -- -- FACETS -- -- -- -- -- -- -- 

CREATE TABLE tag (
    id			serial		PRIMARY KEY,
    name		varchar(20)	NOT NULL UNIQUE,
    restricted		boolean		NOT NULL DEFAULT 'f'
);

CREATE TABLE star (
    id			serial		PRIMARY KEY,
    name		text		NOT NULL UNIQUE,
    gender		varchar(3)	NOT NULL
);


CREATE TABLE label (
    id			serial		PRIMARY KEY,
    name		name		NOT NULL UNIQUE
);

CREATE TABLE series (
    id			serial		PRIMARY KEY,
    name		text		NOT NULL UNIQUE
);


------------------------------------------------------------------

--                  scene_* mapping tables		        --

------------------------------------------------------------------



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

-- no scene_label or scene_series since scene cannot belong to more than 1 of either

------------------------------------------------------------------

--                  alias* mapping tables		        --

------------------------------------------------------------------


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

CREATE TABLE alias_tag (
    alias_id		int		NOT NULL REFERENCES alias,
    tag_id		int		NOT NULL REFERENCES  tag,
    tentative		boolean		NOT NULL DEFAULT 't',
    negated		boolean		NOT NULL DEFAULT 'f',
    CONSTRAINT alias_tag_series_pkey PRIMARY KEY (alias_id,tag_id)
);


 -- TODO constrain alias table to be referenced in one of the mapping tables


/*
CREATE TABLE alias_rule (
    id			serial		PRIMARY KEY,
    condition		text		NOT NULL,
    condition_type	VARCHAR(10)	NOT NULL,
    alias_id		int		NOT NULL REFERENCES alias,
    active		boolean		NOT NULL DEFAULT 't',
    exclude		boolean		NOT NULL DEFAULT 'f',
    case_sensitive	boolean		NOT NULL DEFAULT 'f',
    CONSTRAINT UNIQUE(condition, condition_type, alias_id)
);
*/

CREATE TABLE facet_implication (
    id			serial		PRIMARY KEY,
    predicate		int		NOT NULL,   
    predicate_type	varchar(20)	NOT NULL,
    target		int		NOT NULL,
    target_type		varchar(20)	NOT NULL,
    operator		varchar(5)	NOT NULL,
    active		boolean		NOT NULL DEFAULT 't',
    CONSTRAINT UNIQUE(predicate, predicate_type, target, target_type, operator)
);

------------------------------------------------------------------

--                  functions & triggers			--

------------------------------------------------------------------

--------------------

--  needed for below
    
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


--  get the set of active scenes

CREATE OR REPLACE FUNCTION active_scenes () RETURNS SETOF scene AS $$
    SELECT * FROM scene
    where EXISTS (
	SELECT * FROM scene
	JOIN scene_file ON (scene_file.scene_id = scene.id)
	JOIN file ON (scene_file.file_id = file.id)
	JOIN file_inst ON (file_inst.file_id = file.id)
	WHERE file_inst.marked_delete = 'f' AND file_inst.deleted_on IS NULL
    )
$$  LANGUAGE sql;   --plpgsql;


--  get the set of active files

CREATE OR REPLACE FUNCTION active_files () RETURNS SETOF file AS $$
    SELECT * FROM file
    WHERE EXISTS(
	SELECT * FROM file JOIN file_inst ON (file_inst.file_id = file.id) 
	    WHERE file_inst.marked_delete = 'f' AND file_inst.deleted_on IS NULL
	)
$$  LANGUAGE sql;   --plpgsql;



-- get the words for a scene

CREATE OR REPLACE FUNCTION get_words_for_scene (int) RETURNS TEXT AS $A$
    SELECT STRING_AGG(file_inst.path, ' ') || ' ' || STRING_AGG(file_inst.name, ' ') 
	|| ' ' || STRING_AGG(file.wordbag, ' ')  ||  scene.display_name
	FROM scene
	JOIN scene_file ON (scene_file.scene_id = scene.id)
	JOIN file ON (file.id = scene_file.file_id)
	JOIN file_inst ON (file_inst.file_id = file.id)
	WHERE scene.id = $1
	GROUP BY scene.wordbag, scene.display_name
$A$ LANGUAGE sql;



-- assign a display name from the agg wordbag if none set

CREATE OR REPLACE FUNCTION update_scene_words () RETURNS TRIGGER AS $A$
    DECLARE 
	words text;
	dn text;
	sceneid int;
	scenes int[];
    BEGIN 
	IF TG_TABLE_NAME = 'scene' THEN
	    scenes := ARRAY[NEW.id];
	ELSIF TG_TABLE_NAME = 'scene_file' THEN
	    scenes := ARRAY[NEW.scene_id];
	ELSIF TG_TABLE_NAME = 'file_inst' THEN
	    EXECUTE $B$
		SELECT ARRAY_AGG(distinct scene_file.scene_id) FROM file_inst
		LEFT JOIN file ON (file.id = file_inst.file_id)
		LEFT JOIN scene_file ON (scene_file.file_id = file.id)
		WHERE file_inst.id = $1 AND file_inst.id IS NOT NULL
	    $B$ INTO scenes USING  NEW.id;
	END IF;

	IF scenes IS NULL THEN
	    return NEW;
	END IF;

	FOREACH sceneid IN ARRAY scenes LOOP
	    IF sceneid IS NOT NULL THEN
		EXECUTE $B$
		    SELECT STRING_AGG(file_inst.path, ' ') || ' ' || STRING_AGG(file_inst.name, ' ') 
			|| ' ' || STRING_AGG(file.wordbag, ' ') || ' ' || scene.display_name 
			FROM scene
			JOIN scene_file ON (scene_file.scene_id = scene.id)
			JOIN file ON (file.id = scene_file.file_id)
			JOIN file_inst ON (file_inst.file_id = file.id)
			WHERE scene.id = $1
			GROUP BY scene.wordbag, scene.display_name
		$B$ INTO words USING sceneid;
		IF TG_TABLE_NAME = 'scene' THEN
		    IF NEW.display_name IS NULL OR  NEW.display_name = '' THEN
			NEW.display_name := words;
		    END IF;
		    NEW.wordbag := words;
		ELSIF TG_TABLE_NAME = 'scene_file' THEN
		    EXECUTE $C$
			SELECT display_name FROM scene WHERE scene.id = $1
		    $C$ INTO dn USING sceneid;
		    IF dn IS NULL OR  dn = '' THEN
		    UPDATE SCENE SET display_name = words where id = sceneid;
		    END IF;
		    UPDATE scene SET wordbag = words WHERE scene.id = sceneid;
		END IF;
	    END IF;
	END LOOP;
	return NEW;
    END;
$A$ LANGUAGE plpgsql;



-- consider dropping the update once all scenes have a display_name

CREATE TRIGGER update_scene_words AFTER 
    INSERT OR UPDATE OF wordbag, display_name ON scene 
FOR EACH ROW EXECUTE PROCEDURE update_scene_words();

CREATE TRIGGER update_scene_words AFTER 
    INSERT OR UPDATE ON scene_file
FOR EACH ROW EXECUTE PROCEDURE update_scene_words();
    
CREATE TRIGGER update_scene_words AFTER 
    INSERT OR UPDATE OF name ON file_inst
FOR EACH ROW EXECUTE PROCEDURE update_scene_words();





CREATE OR REPLACE  FUNCTION update_scene_tsv () RETURNS TRIGGER AS $A$
    DECLARE 
	words text;
	sceneid int[];
	scene int;
    BEGIN
	IF TG_TABLE_NAME = 'scene' THEN
	    sceneid := ARRAY[NEW.id];
	ELSIF TG_TABLE_NAME = 'scene_file' THEN
	    sceneid := ARRAY[NEW.scene_id];
	ELSIF TG_TABLE_NAME = 'file' THEN
	    EXECUTE $B$
		SELECT scene_id FROM scene_file
		WHERE scene_file.file_id = $1
	    $B$ INTO sceneid USING  NEW.id;
	ELSIF TG_TABLE_NAME = 'file_inst' THEN
	    EXECUTE $B$
		SELECT ARRAY_AGG(distinct scene_file.scene_id) FROM file_inst
		LEFT JOIN file ON (file.id = file_inst.file_id)
		LEFT JOIN scene_file ON (scene_file.file_id = file.id)
		WHERE file_inst.id = $1 AND file_inst.id IS NOT NULL
	    $B$ INTO sceneid USING  NEW.id;
	END IF;

	IF sceneid IS NULL THEN
	    return NEW;
	END IF;
	FOREACH scene IN ARRAY sceneid LOOP
	    EXECUTE $B$
		SELECT STRING_AGG(file_inst.path, ' ') || ' ' || STRING_AGG(file_inst.name, ' ') 
		    || ' ' || STRING_AGG(file.wordbag, ' ')  || ' ' || scene.display_name
		    FROM scene
		    JOIN scene_file ON (scene_file.scene_id = scene.id)
		    JOIN file ON (scene_file.file_id = file.id)
		    JOIN file_inst ON (file_inst.file_id = file.id)
		    GROUP BY scene.id, scene.wordbag
		    HAVING scene.id = $1
	    $B$  INTO words USING scene;
	    EXECUTE $B$
		UPDATE scene SET tsv = TO_TSVECTOR($1) WHERE scene.id = $2
	    $B$ USING words, scene;
	END LOOP;
	return NEW;
    END;
$A$ LANGUAGE plpgsql;


CREATE TRIGGER update_scene_tsv AFTER 
    INSERT OR UPDATE OF wordbag ON scene 
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




/*


delete from scene_star;
delete from scene_tag;
delete from scene_file;
delete from scene;

update scene set label_id = NULL, series_id = NULL;
delete from alias_tag;
delete from alias_series;
delete from alias_label;
delete from alias_star;
delete from tag;
delete from star;
delete from series;
delete from label;
delete from facet_implication;
delete from alias;

*/

