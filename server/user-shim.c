/* a simple "shim" that is run setuid for a particular user
hardwrited to only run python scripts in /usr/local/athen/
(each user gets their own copy or hardlink of this program, 
all setuid */

#include <stdio.h> 
#include <unistd.h> 
#include <string.h>

int main (int argc, char *argv[]) 
{
  char path[1024];
  char *newargv[20];
  short i;

  if (getuid () != 2001 && getuid () != 0) 
    return 1; // die if we are not real user ID "vmail" or root
  if (argc < 2 || argc > 19)
    return 1;
  if (strlen(argv[1]) > 20) // no suspiciously large script names
    return 1;
  if (strstr(argv[1],".")) // no ascending directory tree via path
    return 1;

  
  setreuid(geteuid (), geteuid ()); // set real user ID to same as effective user ID


  snprintf (path, 1024, "/usr/local/lib/athen/python/%s.py", argv[1]); // full path to script
  newargv[0] = "/usr/bin/python3";
  newargv[1] = path;
  for (i = 2; i<argc ; i++)
    newargv[i] = argv[i];
  newargv[argc] = NULL;

  execv(newargv[0], newargv);

  return 0;
} 
