#!/usr/bin/env python

import hashlib
import os
import re
import shlex



####### CRAWLER ########

validExts = [".rm", ".avi", ".mpeg", ".mpg", ".divx", ".vob", ".wmv", ".ivx", ".3ivx"
    , ".m4v", ".mkv", ".mov", ".asf", ".mp4", ".flv", ".3gp",".asf", ".divx" ]
 
# re-join filenames to eliminate . in path

def modJoin(*paths):
    return os.path.join(*[x for x in paths if x != '.'])



# take md5 checksum of file

def md5sum(file):
    md5 = hashlib.md5()
    with open(file,'rb') as f:
	for chunk in iter(lambda: f.read(128*md5.block_size),b''):
	    md5.update(chunk)
    return md5.hexdigest()

# get recursive directory size
def get_recursive_size(dir):
   return size = sum(os.path.getsize(f) for f in os.listdir(dir) if os.path.isfile(f)) 


####### TAGGER  #######



# break a string down into words and quote-enclosed phrases
def tokenize(mystring):
    return ['"{0}"'.format(fragment) if ' ' in fragment else fragment for fragment in shlex.split(mystring)]

# return match if single or double-enclosed quote phrase detected
def isQuoteEnclosed(mystring):
    return re.search(r'(["\'])(?:(?=(\\?))\2.)*?\1',mystring)


# break a string down into words (alphanum) and ignore quotes and all other non-alphas
def mulch(mystring):
    # TODO: consider the wisdom of this change... do we ever care about numbers?
    #return re.findall(r'\w+',mystring)
    # needs to filter out ratings && at least
    return re.findall(r'[A-Za-z]+',mystring)

# if small is a subsequence of big, returns (start, end+1) of sequence occurence
def contains(small, big):
    for i in xrange(len(big)-len(small)+1):
        for j in xrange(len(small)):
            if type(big[i+j]) == type('') == type(small[j]):  # not typo, python allows chained ==
                if big[i+j].lower() != small[j].lower():
                    break
            else:
                if big[i+j] != small[j]:
                    break
        else:
            return i, i+len(small)
    return False




# searches for condition in mulched_wordbag
# doesn't just accpet wordbag for efficiency purposes in tagger
def wordmatch(condition, mulched_wordbag):
    if contains(mulch(condition),mulched_wordbag):
        return True
    return False
                






####### VIEWS  #######



# iterate pairwise through a list  "s -> (s0,s1), (s1,s2), (s2, s3), ..."
def pairwise(iterable):
        a, b = tee(iterable)
        next(b, None)
        return izip(a, b)



# turn single-field query results into straight list
def sfrToList(rs):
    return map(lambda l: l[0],rs)
            

# turn a sqlalchemy row into a dict by field-name
row2dict = lambda r: {c.name: getattr(r,c.name) for c in r.__table__.columns}
    

# autocomplete label value dicts to feed jquery
# for when data is in format of [(a,b), (c,d)]
def lvdict(labelsvalues):
    js = []
    for (l,v) in labelsvalues:
        js.append({"label":l,"value":v})
    return js
        
# autocomplete label value dicts to feed jquery
# for when data is in format of [a,b,c,]
def lvdictSingle(mylist):
    js = []
    for v in mylist:
        js.append({"label":v,"value":v})
    return js
        

def is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False



# replace whitespace not enclosed in quotes with % for sql searching
def percentSeparator(str):
    return '%'.join(['"{0}"'.format(fragment) if ' ' in fragment else fragment
        for fragment in shlex.split(str)])


