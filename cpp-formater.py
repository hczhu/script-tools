#!/usr/bin/python

anchor_token = [
    '==',
    '!=',
    '>=',
    '<=',
    '<<',
    '=',
    '<',
    '>',
    '//',
    ';',
    ',',
    '->',#to avoid adding space
    '+=',#to avoid adding space
    '*=',#to avoid adding space
    '/=',#to avoid adding space
    '-=',#to avoid adding space
]

which_side_space = [
   [1,1], #'==',
   [1,1], #'!='
   [1,1], #'>=',
   [1,1],# '<=',
   [1,1],# '<<',
    [1,1],#'=',
    [1,1],#'<',
    [1,1],#'>',
    [0,1],#'//',
    [0,1],#';',
    [0,1],#',',
    [0,0],#'->'
    [0,0],#'+='
    [0,0],#'*='
    [0,0],#'/='
    [0,0],#'-='
]

insert_space = [
    [' if(',' if ('],
    [' for(',' for ('],
    ['){',' ) {'],
    [' while(',' while ('],
    [' ;',';'],
]

def find_token(text,pos,tokens):
  a,b=len(text),0
  for i in range(len(tokens)):
    tok=tokens[i]
    res=text[pos:].find(tok)
    if 0 <= res and [res+pos,-len(tok)] < [a,-len(tokens[b])]:
      a,b=res+pos,i
  if a == len(text) : a=-1
  return a,b


def join_tokens(tokens):
  res=[]
  cur=''
  cnt=0
  for tok in tokens:
    if len(cur) > 0:
      cur+=' '
    cur+=tok
    cnt+=tok.count('"')
    if 0== (cnt%2):
      res.append(cur)
      cur=''
      cnt=0
  return res



def format_line(line):
  if line.find('#')==0: return line
  if line.find('//')==0: return line
  indent_space=0
  while indent_space < len(line) and line[indent_space]==' ':
    indent_space+=1
  line=line.strip()
  if len(line)==0: return
  add_space=[False]*len(line)
  start_pos=0
  while start_pos>=0:
    pos,idx=find_token(line,start_pos,anchor_token)
    #print pos,anchor_token[idx]
    if pos >= 0:
      end=pos+len(anchor_token[idx])
      if which_side_space[idx][0] > 0  and pos>0 and line[pos-1] != ' ': add_space[pos-1] = True
      if which_side_space[idx][1] > 0 and end < len(line) and line[end] != ' ': add_space[end-1] = True
      start_pos=end
      continue
    break
  #print add_space
  output=''
  add_space[len(line)-1]=False
  for i in range(len(line)):
    output+=line[i]
    if add_space[i]: output+=' '

  #print output
  output=(' '*indent_space)+output
  for tok in insert_space:
    output=output.replace(tok[0],tok[1])
  output=output.strip()

  while True:
    tmp=output.replace('  ','')
    if tmp == output: break
    output=tmp
  output=output.strip()
  lines=''
  token=join_tokens(output.split(' '))
  #print token
  pos=0
  added=False
  while pos < len(token):
    start=True
    lines+=' '*(indent_space)
    line_cnt=indent_space
    while pos < len(token) and (start  or ( line_cnt + len(token[pos]) + 1
                                                 <= 80) ):
      if not start:
        lines+=' '
        line_cnt+=1
      lines+=token[pos]
      line_cnt+=len(token[pos])
      pos+=1
      start=False
    lines+='\n'
    if not added:
      indent_space+=2
      added=True
  return lines

import sys
while True:
  line=sys.stdin.readline()
  if '' == line: break
  line=format_line(line)
  if None != line:
    sys.stdout.write(line)
