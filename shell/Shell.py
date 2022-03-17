#file descriptors that are default when the shell starts running 
# 0	Represents standard input. - fd_in = 0
# 1	Represents standard output. - fd_out = 1
# 2	Represents standard error.  - fdError = 2

from distutils import command
import os, sys, re, fileinput

from tokenize import String

# Set up file descriptors shortcut
fd_in = 0
fd_out = 1
fd_Error = 2

def shell():
    
    lock = False
    # get and remember the parent pid, will be used for piping 
    pid_parent = os.getpid()

    while(1):

        #write to the screen the current directory 
        os.write(1, ">>".encode())

        #read input from the user
        command_original = os.read(1, 1000).decode()

        command = command_original.strip()

        #if the command is exit then no longer take command, else execute the command
        if(command.lower() == 'exit'):
            break
        
        #if the command was to change directory
        elif(command.lower().find('cd') > -1):
            path = command.split()
            os.chdir(path[1])

        elif(command.__contains__('|')):
            pipe_handler(command.split())
                    
        else:
            #create a process
            pid = os.fork()
            command = command.split()

            # Failed to fork a child
            if pid < 0:
                os.write(2, "Fork Failed: command will not be executed".encode())
                sys.exit(1)

            #case: if you're the child
            elif pid == 0:

                #redirecting cases
                if(command.__contains__('>')):
                    arrow_loc = command.index('>')
                    dest = command[arrow_loc + 1]
                    prog = command[0:arrow_loc]
                    os.close(1)
                    os.open(dest, os.O_CREAT|os.O_WRONLY)
                    os.set_inheritable(1, True)

                    executeProgram(prog)


                # elif(command.__contains__('<')):
                #     arrow_loc = command.index('<')
                #     dest = command[0]
                #     args = command[arrow_loc + 2:]
                #     prog = command[arrow_loc + 1]
                #     os.close(0)
                #     os.open(, os.O_CREAT|os.O_WRONLY)
                #     os.set_inheritable(0, True)

                             
                else:
                    executeProgram(command)
            
            else:
                os.wait()
                    


def executeProgram(program_command):
    for dir in re.split(":", os.environ['PATH']): # try each directory in the path
        program = "%s/%s" % (dir, program_command[0])
        try:
            os.execve(program, program_command[0:], os.environ) # try to exec program
        except FileNotFoundError:             # ...expected
            pass                              # ...fail quietly

    os.write(1, ("%s command not found.\n" % program_command[0].encode()))


def pipe_handler(command_array):
    # pw - the end of the pipe where we write to 
    # pr - the end of the pipe where we read from 

    # create the pipe and make it inheritable so that the children can communicate with each other
    pr, pw = os.pipe()
    for f in (pr, pw):
        os.set_inheritable(f, True)

    # Create the first child and turn lock on
    lock = True
    child1_id = os.fork()
    
    
    # fork failed
    if(child1_id < 0):
        os.write(2, "Fork1 Failed: command will not be executed".encode())
        sys.exit(1)

    # case: child1 handles writing to the pipe 
    elif(child1_id == 0):
        # disconnect fd1 from display
        os.close(fd_out)

        # rewire output to the pipe
        os.dup(pw)
        os.set_inheritable(fd_out, True)

        # close rest of unneccesary connections
        # for fd in (pw, pr):
        #         os.close(fd)
        # os.close(fd_in)
        # os.close(fd_Error)

        # execute the left hand side command
        pipe_loc = command_array.index('|')
        prog = command_array[0: pipe_loc]
        executeProgram(prog)

    # Case: parent will create the second child
    else:
        child2_id = os.fork()

        if(child2_id < 0):
            os.write(2, "Fork2 Failed: command will not be executed".encode())
            sys.exit(1)
        
        elif(child2_id == 0):
             # disconnect fd1 from display
            os.close(fd_in)

            # rewire output to the pipe
            os.dup(pr)
            os.set_inheritable(fd_in, True)

            # close rest of unneccesary connections
            for fd in (pw, pr):
                os.close(fd)
            # os.close(fd_out)
            # os.close(fd_Error)

            # Execute right side command with input from the pipe
            pipe_loc = command_array.index('|')
            prog = command_array[pipe_loc + 1:]
            executeProgram(prog)

        else:
            for fd in (pw, pr):
                os.close(fd)
            if(lock):
                os.wait()

shell()


