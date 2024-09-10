### How this shell translates a line of input that a user enters into a command which is executed in the command line
The line of input entered by the user is stored into a string variable inside the shell program. This string then is splitted into a list of arguments by the `split` function which is mostly similar to the module `shlex`. The first argument represents the command name, which provides information for the program to know what command to run. Every arguments of the input are passed to the command as the command's arguments. Executing the command can be done by using either `os.execvp()` or `os.execv()` based on whether the command given is a local executable or a program in the system's `PATH`.

---
### The logic that this shell performs to find and substitute environment variables in user input. How it handles the user escaping shell variables with a backslash `\` so that they are interpreted as literal strings
The logic of substituting environment variables of this shell is performed by the `subvar` function and works as below:
- create an empty dictionary, this dictionary will store the information about substitutions inside the command string entered by user
- iterate the string from left to right:
  - if the current character is `{` and there is a `$` character to its left, store its index to, say $op$
  - if the current character is `}` and there was a open curly bracket found before (its index was stored):
    - if there is a backslash `\` to the left of the `$` character (its index is $op-1$), which means this is an escaped shell variable: add the pair $(op-2, -1)$ with $op-2$ as the index of the backslash `\` character to the dictionary
    - if there is no backslash `\` to the left of the `$` character, store the substring in between the brackets, this is our variable name and it should be substituted: add the pair $(op-1, (i, var))$ to the dictionary with $i$ as the current index and $var$ as the variable name
- create an empty string, say $ans$, this string will represent the input command after all variables substitution
- iterate throught the elements of the dictionary with the same order as when they were added
- we will insert substrings of the original command to complete $ans$, let's call $index$ to denote the largest index of the original command which we have inserted to $ans$, initially $index = -1$:
  - the element of a dictionary is represented as a pair of $(key, value)$ if $value$ is a tuple:
    - insert the substring $[index+1,key-1]$ (inclusive) to $ans$
    - set $index$ to $val[0]$ with $val[0]$ as the original index of `{`
    - insert the value of the variable to $ans$ if it exists
  - otherwise, insert the substring $[index+1, key-1]$ (inclusive) to $ans$ and set $index = key$

---
### How this shell handles pipelines as part of its execution. The logic in the program which allows one command to read another command's `stdout` output as `stdin`

To allow a command to read another command's `stdout` output as `stdin`, use the function `os.pipe()` to create 2 file descriptors `r` and `w` to read and write respectively. Then fork a child process by calling `os.fork()`. Inside the child process, redirect the write end `w` to `stdout` by calling `os.dup2(w, 1)` and then execute the command. In the parent process, redirect the read end `r` to `stdin` by calling `os.dup2(r, 0)` and then execute the command.

By setting up the pipe connection, the output of a command is captured and then passed onto another command as input.

To handle a pipeline of $n$ commands, create $n-1$ pipes. For each command, fork a child process and set up the pipes' direction as explained above. In the parent process, wait for all child processes to finish.

---
The tests created are I/O tests. Structure of the tests is as below:
- Test 1-4: parsing commands
- Test 5-9: cd built-in commands
- Test 10-11: pwd built-in commands
- Test 12-15: exit built-in commands
- Test 16-23: var built-in commands
- Test 24-28: which built-in commands
- Test 29-33: executing commands
- Test 34-37: pipe
- Test 38-41: environment variables