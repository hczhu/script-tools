filetype plugin on
syntax on
set foldmethod=indent
"au FileType cc,lex,cpp,h,proto,borg,y set foldmethod=indent
au FileType cc,lex,cpp highlight Folded guibg=blue guifg=green
"set foldlevelstart=30
set scrolloff=40
"Use clipboard as default copy
set clipboard=unnamedplus
" mystuff
au FileType cc,lex,cpp,c,java,python imap "" ""<Esc>ha
au FileType cc,lex,cpp,c,java,python imap () ()<Esc>ha
au FileType cc,lex,cpp,c,java,python imap [] []<Esc>ha
au FileType cc,lex,cpp,c,java,python imap <> <><Esc>ha
au FileType cc,lex,cpp,c,java,python imap '' ''<Esc>ha
au FileType cc,lex,cpp,c,java imap { {<CR>}<Esc>O
"au FileType cpp,c,java,python map <C-r> :!gedit %<CR>
map <F6> <Esc>elDyyp0dwi<BS> = vars.<Esc>j
au FileType cpp,python map <F3> <Esc>0dwi<BS><Esc>
au FileType cpp,python map <F4> 0dwi<BS><CR><Esc>


"au FileType cpp map <C-u> :w<CR>:!g++ -o %:r -g -O0 -Wall -lprofiler -lpthread %
au FileType cpp map <C-u> :w<CR>:!g++ -o %:r -g -O0 -Wall %<CR>
"au FileType c map <C-u> :w<CR>:!gcc -o %:r -g -O0 -Wall -lpthread %
au FileType cpp,c map <F5> :!./%:r
au FileType python map <F5> :!./%
"
"au FileType cpp map <C-u> :w<CR>:!g++ -o %:r -O2 -DNDEBUG -lprofiler -lpthread %;echo "No debug\!\!\!"
"au FileType cpp map <C-u> :w<CR>:!g++ -o %:r -O2 -DNDEBUG %;echo "No debug\!\!\!"<CR>
"au FileType c map <C-u> :w<CR>:!gcc -o %:r -O2 -DNDEBUG -lpthread %;echo "No debug\!\!\!"


"au FileType java map <C-u> :w<CR>:!javac %<CR>
au FileType java map <F6> :!java -enableassertions -Xmx1024M %:r
" check spell
"
"au FileType tex map <C-b> :w<CR>:!pdflatex %<CR>
"au FileType tex map <C-r> :w<CR>:!acroread %:r.pdf<CR>
"au FileType tex imap {} {}<Esc>ha
"au FileType tex imap [] []<Esc>ha
"au FileType tex imap () ()<Esc>ha
"au FileType tex imap $$ $$<Esc>ha
"au FileType tex set spell
autocmd BufNewFile,BufRead *.html,*htm set spell
"
" 
command RemoveCtrlM %,%s/
command GenerateTags !ctags -R *
command Cs !look <cword>
" Create a variable name for type: AaaBbbCaa ===> aaa_bbb_ccc
map Va wbveyea <CR><Esc>O<Esc>p:.s/\([a-z]\)\([A-Z]\)/\1_\2/g<CR>VuA <Esc>JkJ
"map <C-s> :!look <cword>
"command Backup !suffix=`date | tr ' ' '-'`; echo $suffix; cp % .%-$suffix 

"" When editing a file, always jump to the last known cursor position.
"" Don't do it when the position is invalid or when inside an event handler
"" (happens when dropping a file on gvim).
au BufReadPost * if line("'\"") > 0|if line("'\"") <= line("$")|exe("norm'\"")|else | exe "norm $" | endif | endif 

map <F1> <C-l>

"hilight too long line
au FileType cc,h set colorcolumn=81,82,83,84
" So what, I can't type...
nmap :W :w
nmap :X :x
nmap :Q :q

" Don't use Ex mode, use Q for formatting
map Q gq

"set spell

"set path
"set path+=../
"set path+=./
"Only search current directory.
"let g:ctrlp_working_path_mode = 'c'
let g:ctrlp_working_path_mode = ''
let g:ctrlp_user_command = 'echo %s > /dev/null; find . -type f -not -name ".*"'
let g:ctrlp_clear_cache_on_exit = 0

"Auto save the file which is being edited when vim loses focus.
au FocusLost * silent! wa
