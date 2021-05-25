# To enable tab-completion for ellsync in bash, source this file, like so:
#   . /path/to/ellsync/script/ellsync_tabcomplete.sh
# You might want to do this in your bash startup script.

function _ellsync_tabcomplete_()
{
    local cmd="${1##*/}"
    local word=${COMP_WORDS[COMP_CWORD]}
    local line=${COMP_LINE}

    IFS=' ' read -raargv<<< "$line"
    local argc=${#argv[@]}

    if [ $argc -eq 2 ]; then
      COMPREPLY=($(compgen -o default "${word}"))
    elif [ $argc -eq 3 ]; then
      COMPREPLY=($(compgen -W "list sync rename" "${word}"))
    elif [ $argc -gt 3 ]; then
      local router="${argv[1]}"
      local streams=`ellsync $router list --stream-name-only`
      COMPREPLY=($(compgen -W "${streams}" "${word}"))
    fi
}

complete -F _ellsync_tabcomplete_ ellsync
