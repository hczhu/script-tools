#personal alias
alias chinese='LANG=zh.utf8'
#alias arena='killall scim; /usr/lib/jvm/java-6-openjdk/jre/bin/javaws.real ~/mycode/topcoder/ContestAppletProd.jnlp &'
alias vim='vim -X'
alias emacs='emacs -nw'
alias vir='vim -R -X'
alias 'ls'='ls --color=auto'
alias 'll'='ls -l'
alias cl='clear'
alias 'grep'='grep --color'
alias portfolio='cat ~/stock-txn/*csv | stock.py 2> /dev/null'

# personal export
export PATH=$PATH:$HOME/tools/

# Memorize historical commands.
export HISTCONTROL=erasedups
export HISTTIMEFORMAT="%Y-%m-%d %H:%M:%S"
# bash history related
export HISTCONTROL=ignoredups
export HISTFILESIZE=1000000000
export HISTSIZE=10000000
# append historical commands to .bash_history instead of overwriting.
shopt -s histappend
# Append each command to ~/.bash_history immediately after executing that
# command.
PROMPT_COMMAND="history -a; $PROMPT_COMMAND"

# for tmux window titles.
settitle() {
  title=$(basename $PWD)
  printf "\033k$title\033\\"
}
PROMPT_COMMAND="settitle; $PROMPT_COMMAND"

# Input method
#export XIM="SCIM"
#export XMODIFIERS=@im=SCIM  #设置scim为xim默认输入法
#export GTK_IM_MODULE="scim-bridge"  #设置scim-bridge为gtk程序默认的输入法
#export QT_IM_MODULE=xim   #设置xim为qt程序默认的输入法
#export XIM_PROGRAM="scim -d" #使可以自动启动

#For Weka
export WEKAROOT='/home/hczhu/open-source-package/weka-3-6-4'
export CLASSPATH=$CLASSPATH:.:$WEKAROOT/weka.jar:/home/hczhu/open-source-package/weka-3-6-4-gui/weka-3-6-4/weka.jar:/home/hczhu/open-source-package/weka-3-6-4-gui/weka-3-6-4/WLSVM/lib/libsvm.jar:/home/hczhu/open-source-package/weka-3-6-4-gui/weka-3-6-4/WLSVM/lib/wlsvm.jar
alias weka-lr='java weka.classifiers.functions.LinearRegression'
alias weka-lg='java -Xmx2028m weka.classifiers.functions.Logistic'
alias weka='java -Xmx2024m -jar /home/build/static/projects/experimental/mledu/weka/weka.jar'

#Start a single workrave
if [[ -e workrave && $(pgrep workrave | wc -l) = "0" ]]
then
  workrave &
fi
