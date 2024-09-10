import signal
import sys
import os
import json
import parsing

# DO NOT REMOVE THIS FUNCTION!
# This function is required in order to correctly switch the terminal foreground group to
# that of a child process.

def setup_signals() -> None:
    """
    Setup signals required by this program.
    """
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)

def check_valid_var(var):
    ''' return True if variable var has a valid name, False otherwise '''
    for c in var:
        if not c.isalnum() and c != '_':
            return False
    return True

def subvar(s : str):
    ''' substitute variable inside string s '''
    subbed_list = {}
    op = -1
    for i in range(0, len(s)):
        if s[i] == '{' and i-1 >= 0 and s[i-1] == '$':
            op = i
        if s[i] == '}' and op != -1:
            var = s[op+1:i]
            if not check_valid_var(var):
                sys.stderr.write(f"mysh: syntax error: invalid characters for variable {var}\n")
                return
            if op-2 >= 0 and s[op-2] == '\\':
                subbed_list[op-2] = -1
            else:
                subbed_list[op-1] = i, var
            op = -1
    subbed_list[len(s)] = -1
    ans = ""
    index = -1
    for key in subbed_list.keys():
        val = subbed_list[key]
        if isinstance(val, tuple):
            ans += s[index+1:key]
            index = val[0]
            if os.environ.get(val[1]) is not None:
                ans += os.environ[val[1]]
        else:
            ans += s[index+1:key]
            index = key
    return ans

def load_ini():
    ''' load initialisation file .myshrc '''
    if os.environ.get("MYSHDOTDIR") is not None:
        d = f"{os.environ["MYSHDOTDIR"]}/.myshrc"
    else:
        d = os.path.expanduser("~") + "/.myshrc"
    if not os.path.exists(d):
        return
    try:
        with open(d, "r") as f:
            data = json.load(f)
    except json.decoder.JSONDecodeError:
        sys.stderr.write("mysh: invalid JSON format for .myshrc\n")
        return
    for key in data.keys():
        if not check_valid_var(key):
            sys.stderr.write(f"mysh: .myshrc: {key}: invalid characters for variable name\n")
            continue
        if not isinstance(data[key], str):
            sys.stderr.write(f"mysh: .myshrc: {key}: not a string\n")
            continue
        os.environ[key] = subvar(data[key])

def escape(st : int, s : str):
    ''' detect escaped quote '''
    if st >= len(s):
        sys.exit(1)
    if s[st+1] == '"' or s[st+1] == "'":
        return [s[st+1], st+1]
    return -1

def split(s : str):
    ''' split command into arguments '''
    sep = tuple(' ')
    s += ' '
    open_quote = ''
    ans = []
    t = ""
    i = 0
    while i < len(s):
        if s[i] == '\\':
            x = escape(i, s)
            if x != -1:
                t += x[0]
                i = x[1]+1
                continue
        if open_quote == '':
            if s[i] in sep:
                if t != "":
                    ans.append(t)
                t = ""
            elif s[i] == '"' or s[i] == "'":
                open_quote = s[i]
            else:
                t += s[i]
        else:
            if s[i] == open_quote:
                if s[i+1] in sep:
                    ans.append(t)
                    t = ""
                open_quote = ""
            else:
                t += s[i]
        i += 1
    if open_quote != '':
        sys.stderr.write("mysh: syntax error: unterminated quote\n")
        return
    return ans

def var_built(parsed : list):
    ''' var builtin command '''
    if len(parsed) < 3:
        sys.stderr.write(f"var: expected 2 arguments, got {len(parsed)-1}\n")
        return
    if parsed[1][0] == '-':
        if len(parsed) != 4:
            sys.stderr.write(f"var: expected 2 arguments, got {len(parsed)-2}\n")
            return
        for c in parsed[1]:
            if c != '-' and c != 's':
                sys.stderr.write(f"var: invalid option: -{c}\n")
                return
        if not check_valid_var(parsed[2]):
            sys.stderr.write(f"var: invalid characters for variable {parsed[2]}\n")
            return
        command_argument = parsed[3]
        command_output = ""
        r,w = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.setpgid(0,0)
            os.close(r)
            os.dup2(w, 1)
            os.close(w)
            execute(command_argument)
            os._exit(0)
        elif pid > 0:
            try:
                os.setpgid(pid, pid)
            except PermissionError:
                pass
            fd = os.open("/dev/tty", os.O_RDONLY)
            os.tcsetpgrp(fd, os.getpgid(pid))
            os.close(w)
            os.wait()
            os.tcsetpgrp(fd, os.getpgid(0))
            os.close(fd)
            r = os.fdopen(r)
            command_output = r.read()
            r.close()
        os.environ[parsed[2]] = command_output
    else:
        if len(parsed) != 3:
            sys.stderr.write(f"var: expected 2 arguments, got {len(parsed)-1}\n")
            return
        if not check_valid_var(parsed[1]):
            sys.stderr.write(f"var: invalid characters for variable {parsed[1]}\n")
            return
        os.environ[parsed[1]] = parsed[2]

def exit_built(parsed : list):
    ''' exit builtin command '''
    if len(parsed) > 2:
        sys.stderr.write("exit: too many arguments\n")
        return
    if len(parsed) == 1:
        sys.exit(0)
    if not parsed[1].isdigit():
        sys.stderr.write(f"exit: non-integer exit code provided: {parsed[1]}\n")
        return
    sys.exit(int(parsed[1]))

def pwd_built(parsed : list):
    ''' pwd bultin command '''
    if len(parsed) == 1:
        print(os.environ["PWD"])
        return
    for i in range(1, len(parsed)):
        if parsed[i][0] != '-':
            sys.stderr.write("pwd: not expecting any arguments\n")
            return
    for i in range(1, len(parsed)):
        for c in parsed[i]:
            if c not in ('-', 'P'):
                sys.stderr.write(f"pwd: invalid option: -{c}\n")
                return
    print(os.getcwd())

def cd_built(parsed : list):
    ''' cd builtin command '''
    if len(parsed) == 1 or (len(parsed) == 2 and parsed[1] == '~'):
        os.environ["PWD"] = os.path.expanduser("~")
        os.chdir(os.environ["PWD"])
        return
    if len(parsed) > 2:
        sys.stderr.write("cd: too many arguments\n")
        return
    if os.path.isabs(parsed[1]):
        d = parsed[1]
    else:
        d = os.environ["PWD"] + '/' + parsed[1]
    d = os.path.normpath(d)
    if not os.path.exists(d):
        sys.stderr.write(f"cd: no such file or directory: {parsed[1]}\n")
        return
    if not os.path.isdir(d):
        sys.stderr.write(f"cd: not a directory: {parsed[1]}\n")
        return
    if not os.access(d, os.X_OK):
        sys.stderr.write(f"cd: permission denied: {parsed[1]}\n")
        return
    os.environ["PWD"] = d
    os.chdir(os.environ["PWD"])

def which_built(parsed : list):
    ''' which builtin command '''
    if os.environ.get("PATH") is not None:
        path = os.environ["PATH"]
    else:
        path = os.defpath
    if len(parsed) == 1:
        sys.stderr.write("usage: which command ...\n")
        return
    ans = ""
    for i in range(1, len(parsed)):
        cm = parsed[i]
        if cm == "var" or cm == "pwd" or cm == "cd" or cm == "exit" or cm == "which":
            ans += f"{cm}: shell built-in command\n"
            continue
        found = False
        for d in path.split(':'):
            if not os.path.exists(d + '/' + cm):
                continue
            ans += d + '/' + cm + '\n'
            found = True
            break
        if not found:
            ans += f"{cm} not found\n"
    ans = ans[:-1]
    print(ans)

def find_executable(parsed : list):
    ''' find executable command inside system and execute it '''
    if os.environ.get("PATH") is not None:
        path = os.environ["PATH"]
    else:
        path = os.defpath
    new_parsed = []
    for i in range(0, len(parsed)):
        t = os.path.expanduser(parsed[i])
        t = os.path.normpath(t)
        new_parsed.append(t)
    if parsed[0].find('/') == -1:
        found = False
        for d in path.split(':'):
            if os.path.exists(f"{d}/{parsed[0]}"):
                found = True
                break
        if not found:
            sys.stderr.write(f"mysh: command not found: {parsed[0]}\n")
            return
        child_pid = os.fork()
        if child_pid == 0: # child process
            os.setpgid(0,0)
            os.execvp(parsed[0], new_parsed)
        elif child_pid > 0: # parent process
            try:
                os.setpgid(child_pid, child_pid)
            except PermissionError:
                pass
            fd = os.open("/dev/tty", os.O_RDONLY)
            os.tcsetpgrp(fd, os.getpgid(child_pid))
            os.wait()
            os.tcsetpgrp(fd, os.getpgid(0))
            os.close(fd)
    else:
        if not os.path.exists(new_parsed[0]):
            sys.stderr.write(f"mysh: no such file or directory: {parsed[0]}\n")
            return
        if os.path.isdir(new_parsed[0]):
            sys.stderr.write(f"mysh: is a directory: {parsed[0]}\n")
            return
        if not os.access(new_parsed[0], os.X_OK):
            sys.stderr.write(f"mysh: permission denied: {parsed[0]}\n")
            return
        child_pid = os.fork()
        if child_pid == 0: # child process
            os.setpgid(0,0)
            os.execv(new_parsed[0], new_parsed)
        elif child_pid > 0: # parent process
            try:
                os.setpgid(child_pid, child_pid)
            except PermissionError:
                pass
            fd = os.open("/dev/tty", os.O_RDONLY)
            os.tcsetpgrp(fd, os.getpgid(child_pid))
            os.wait()
            os.tcsetpgrp(fd, os.getpgid(0))
            os.close(fd)

def pipeline(parsed : list):
    ''' create a pipeline with parsed as list of commands '''
    for s in parsed:
        if s.isspace() or s == '':
            sys.stderr.write(f"mysh: syntax error: expected command after pipe\n")
            return
    for i in range(len(parsed)):
        parsed[i] = split(parsed[i])
    pipes = []
    pids = []
    for i in range(len(parsed)-1):
        pipes.append(os.pipe())
    for i in range(len(parsed)):
        pids.append(os.fork())
        if pids[i] == 0: # child process
            os.setpgid(0, pids[0])
            if i > 0:
                os.dup2(pipes[i-1][0], 0)
            if i < len(parsed)-1:
                os.dup2(pipes[i][1], 1)
            for pipe in pipes:
                os.close(pipe[0])
                os.close(pipe[1])
            if parsed[i][0].find('/') == -1:
                os.execvp(parsed[i][0], parsed[i])
            else:
                os.execv(parsed[i][0], parsed[i])
            os._exit(0)
        elif pids[i] > 0: # parent process
            try:
                os.setpgid(pids[i], pids[0])
            except PermissionError:
                pass
    # parent process
    fd = os.open("/dev/tty", os.O_RDONLY)
    os.tcsetpgrp(fd, os.getpgid(pids[0]))
    for pipe in pipes:
        os.close(pipe[0])
        os.close(pipe[1])
    for i in range(len(parsed)):
        os.waitpid(pids[i], 0)
    os.tcsetpgrp(fd, os.getpgid(0))
    os.close(fd)

def execute(command : str):
    ''' execute user's command '''
    command = subvar(command)
    if command is None:
        return
    parsed = split(command)
    if parsed is None or len(parsed) == 0:
        return
    if parsed[0] == "var":
        var_built(parsed.copy())
        return
    if parsed[0] == "exit":
        exit_built(parsed.copy())
        return
    if parsed[0] == "pwd":
        pwd_built(parsed.copy())
        return
    if parsed[0] == "cd":
        cd_built(parsed.copy())
        return
    if parsed[0] == "which":
        which_built(parsed.copy())
        return
    pipe_parsed = parsing.split_by_pipe_op(command)
    if len(pipe_parsed) == 1:
        find_executable(parsed.copy())
        return
    pipeline(pipe_parsed)

def main() -> None:
    ''' main function '''
    # DO NOT REMOVE THIS FUNCTION CALL!
    setup_signals()

    # Start your code here!

    load_ini()

    if os.environ.get("PROMPT") is None:
        os.environ["PROMPT"] = ">> "
    if os.environ.get("MYSH_VERSION") is None:
        os.environ["MYSH_VERSION"] = "1.0"
    os.environ["PWD"] = os.getcwd()

    try:
        while True:
            print(os.environ["PROMPT"], end='')
            try:
                command = input()
            except KeyboardInterrupt:
                print()
                continue
            execute(command)
    except EOFError:
        print('')

if __name__ == "__main__":
    main()
