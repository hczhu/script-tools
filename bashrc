#personal alias
alias chinese='LANG=zh.utf8'
#alias arena='killall scim; /usr/lib/jvm/java-6-openjdk/jre/bin/javaws.real ~/mycode/topcoder/ContestAppletProd.jnlp &'
alias vim='vim -X'
alias emacs='emacs -nw'
alias vir='vim -R -X'
alias 'ls'='ls --color=auto'
alias 'll'='ls -lh'
alias cl='clear'
alias 'grep'='grep --color'
alias portfolio='$HOME/mycode/script-tools/smart-stocker.py 2> /tmp/stock.log'

# personal export
export PATH=$PATH:$HOME/tools/

export HISTTIMEFORMAT="%Y-%m-%d %H:%M:%S"
export HISTCONTROL=ignoredups:erasedups  # no duplicate entries
export HISTSIZE=100000                   # big big history
export HISTFILESIZE=100000               # big big history
shopt -s histappend                      # append to history, don't overwrite it
# Save and reload the history after each command finishes
export PROMPT_COMMAND="history -a; history -c; history -r;"

# for tmux window titles.
settitle() {
  title=$(basename $PWD)
  printf "\033k$title\033\\"
}

PROMPT_COMMAND="settitle; $PROMPT_COMMAND"

set_git_branch() {
  export GIT_BRANCH=$(get_git_branch)
}

get_git_branch() {
  if [ -r '.git' ]; then 
    echo "($(git branch 2> /dev/null | grep \* | cut -d' ' -f2))"
  elif [ -r '.hgignore' ]; then
    echo "($(hg bookmark 2> /dev/null | grep \* | cut -d' ' -f3))"
  fi
}

# PROMPT_COMMAND="set_git_branch; $PROMPT_COMMAND"
# PROMPT_COMMAND=""

export PS1='[\u@\h \w$(get_git_branch)] '

# Input method
#export XIM="SCIM"
#export XMODIFIERS=@im=SCIM  #设置scim为xim默认输入法
#export GTK_IM_MODULE="scim-bridge"  #设置scim-bridge为gtk程序默认的输入法
#export QT_IM_MODULE=xim   #设置xim为qt程序默认的输入法
#export XIM_PROGRAM="scim -d" #使可以自动启动

#For Weka
export WEKAROOT='$HOME/packages/weka-3-6-12'
export CLASSPATH="$CLASSPATH:.:$WEKAROOT/weka.jar"
alias weka-lr='java weka.classifiers.functions.LinearRegression'
alias weka-lg='java -Xmx2028m weka.classifiers.functions.Logistic'
alias weka-svm='java -Xmx2028m weka.classifiers.functions.LibSVM'
alias weka='java -Xmx2024m -jar $WEKAROOT/weka.jar'

#Start a single workrave
if [[ -e workrave && $(pgrep workrave | wc -l) = "0" ]]
then
  workrave &
fi

# access the last output by $(L)
alias L='tmux capture-pane; tmux showb -b 0 | tail -n 3 | head -n 1'

alias tmux-new='tmux new -s'

#alias tmux='export TMPDIR=/home/hcz/tmux-sessions && tmux'
tmux attach -t working

alias ds='date +%F'

alias git-new-br='git checkout --track origin/master -b'

# record screen output
#if [ "$SCREEN_RECORDED" = "" ]; then
#  export SCREEN_RECORDED=1
#  script -t -a 2> /tmp/terminal-record-time-$$.txt /tmp/terminal-record-$$.txt
#fi

VimBinaryDiff() {
  vimdiff <(xxd $1) <(xxd $2)
}

alias vimbdiff='VimBinaryDiff'

ShowThreadInfo() {
  # expect an input pid.
  pid=$1
  top  -b -H -p $pid -n1 | tail -n+8 |  cut -d':' -f2 \
    | cut -d' ' -f2 | sed  's/[0-9]\+$/*/' \
    | sort | uniq -c  | sort -k1 -n | sed 's/^ \+/    /'
}

# edit command line in bash by vi
# set -o vi
