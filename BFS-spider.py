#!/usr/bin/python
import urllib2
import Queue
import sets
import time
import sys
start_tag='<div class="name-list">'
end_tag='</div>'
tag='<a href='
prefix='http://renlifang.msra.cn/name/'
suffix='/index.html'
seen={}
qq=Queue.Queue()
qq.put('')
used=sets.Set(['197','462','209','34','417','463','140','472','379','364','50','53','55','58','60','64','66','65','59','98','141','242','259','51','334','67','474','443','59','31','208','312','359','347','251','418','385','404','362','363'])
for i in range(465):
  used=used|sets.Set([str(i)])
print used
for step in range(3):
  size=qq.qsize()
  for i in range(size):
    name=qq.get()
    sys.stderr.write('Got '+name+'\n')
    content=''
    url=prefix+name
    if url.find('html')==-1: url+=suffix
    try:
      content=urllib2.urlopen(url).read()
    except:
      sys.stderr.write('Request error at '+name+'\n')
      continue
    filename='msra_'+str(step)+'_'+name.replace('/','+')
    f=open(filename,'w')
    f.write(content)
    f.close()
    pos=0
    while True:
      shift=content[pos:].find(start_tag)
      if shift==-1: break
      start=pos+shift+len(start_tag)
      end=content[start:].find(end_tag)+start
      ptr=start;
      while ptr<end:
        shift=content[ptr:].find(tag)
        if shift==-1 or shift+ptr+len(tag)>=end: break
        ptr+=shift+len(tag)
        url_start=ptr
        while content[ptr]!='>': ptr+=1
        new_name=content[url_start:ptr]
        new_start=new_name.find(suffix)
        if new_start!=-1: new_name=new_name[0:new_start]
        if new_name[0]=='.': new_name=new_name[1:]
        if new_name[0]=='/': new_name=new_name[1:]
        if step!=0: new_name=name+'/'+new_name
        if new_name in seen: continue
        if step==0 and ( new_name in used): continue
        seen[new_name]=1
        qq.put(new_name)
        sys.stderr.write('Parsed a new name '+new_name+'\n')
#        if qq.qsize()>1: break
#      if qq.qsize()>1: break
      pos=end
#    break
    time.sleep(2)

