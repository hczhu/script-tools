#!/usr/bin/python2.4
#
import sys
import getopt

def main(argv):
  #-f dictionary file
  #-d deliminator
  #-k which field is the key
  try:
    opts,args=getopt.getopt(argv,'f:d:k:')
  except getopt.GetoptError,err:
    sys.stderr.write(str(err))
    sys.exit(2)
  key_file=''
  delim='\t'
  key_field=0
  for o,a in opts:
    if o in ('-f'): key_file=a
    elif o in ('-d'):delim=a
    elif o in (''):key_file=int(a)-1
    else:
      sys.stderr.write('Bad argments:%s %s\n'%(o,a))
      sys.exit(1)
  all_key={}
  for line in file(key_file):
    line=line.strip()
    key=line.split()[0]
    all_key[key]=line[len(key)+1:]
  for line in sys.stdin:
    line=line.strip()
    tok=line.split(delim)
    if len(tok)<=key_field:
      sys.stderr.write('Bad line:%s\n'%(line))
      continue
    key=tok[key_field]
    if tok[key_field] not in all_key:
      sys.stderr.write('Missing key:%s\n'%(key))
      continue
    print '%s%s%s'%(line,delim,all_key[key])

if __name__ == '__main__':
  main(sys.argv[1:])
