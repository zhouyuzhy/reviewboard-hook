#!/usr/bin/env python
#
# svn-hook-postcommit-review
# This script should be invoked from the subversion post-commit hook like this:
#
# REPOS="$1"
# REV="$2"
# /usr/bin/python /some/path/svn-hook-postcommit-review "$REPOS" "$REV" || exit 1
#
# Searches the commit message for text in the form of:
#   publish review - publishes a review request
#   draft review - creates a draft review request
#
# The space before 'review' may be ommitted.
#
# The log message is interpreted for review request parameters:
#    summary = up to first period+space, first new-line, or 250 chars
#    description = entire log message
#    existing review updated if log message includes 'update review:[0-9]+'
#    bugs added to review if log message includes commands as defined in
#      supported_ticket_cmds
#
# By default, the review request is created out of a diff between the current
# revision (M) and the previous revision (M-1).
#
# To create a diff that spans multiple revisions, include
# 'after revision:[0-9]+' in the log message.
#
# To limit the diff to changes in a certain path (e.g. a branch), include
# 'base path:"<path>"' in the log message.  The path must be relative to
# the root of the repository and be surrounded by single or double quotes.
#
# An example commit message is:
#
#    Changed blah and foo to do this or that.  Publish review ticket:1
#      update review:2 after revision:3 base path:'internal/trunk/style'.
#
# This would update the existing review 2 with a diff of changes to files under
# the style directory between this commit and revision 3.  It would place
# the entire log message in the review summary and description, and put
# bug id 1 in the bugs field.
#
# This script may only be run from outside a working copy.
#

#
# User configurable variables
#

# Username and password for Review Board user that will be connecting
# to create all review requests.  This user must have 'submit as'
# privileges, since it will submit requests in the name of svn committers.

# Path contains rbt script
POSTREVIEW_PATH = "/usr/bin/"
# Path contains svnlook
SVNLOOK_PATH = "/usr/bin/"
# Path contains svn
SVN_PATH = "/usr/bin/"
# reviewboard user
USERNAME = 'repository'
PASSWORD = 'qxy2ag'
# reviewboard server
SERVER = 'http://10.0.0.0'
# svn repository address
REPOSITORY = ''
# read-only svn user
SVN_USER = ''
SVN_PASSWORD = ''
#SVN_USER = 'pm'
#SVN_PASSWORD = 'pm_pw'
# (libsvn / svn / pysvn) python script path
ENCODING = 'UTF-8'

# If true, runs rbt in debug mode and outputs its diff
DEBUG = False
#DEBUG = True

#
# end user configurable variables
#

import logging
import sys
import os
import subprocess
import re
#import svn.fs
#import svn.core
#import svn.repos

reload(sys)
sys.setdefaultencoding('UTF8')
# list of trac commands from trac-post-commit-hook.py.
# numbers following these commands will be added to the bugs
# field of the review request.
supported_ticket_cmds = {'review':         '_cmdReview',
                         'publishreview':  '_cmdReview',
                         'publish review': '_cmdReview',
                         'draftreview':    '_cmdReview',
                         'draft review':   '_cmdReview'}

ticket_prefix = '(?:#|(?:ticket|issue|bug)[: ]?)'
ticket_reference = ticket_prefix + '[0-9]+'
ticket_command = (r'(?P<action>[A-Za-z]*).?'
                  '(?P<ticket>%s(?:(?:[, &]*|[ ]?and[ ]?)%s)*)' %
                  (ticket_reference, ticket_reference))

def execute(command, env=None, ignore_errors=False, shell=False):
    """
    Utility function to execute a command and return the output.
    Derived from Review Board's rbt script.
    """
    if env:
        env.update(os.environ)
    else:
        env = os.environ

    p = subprocess.Popen(command,
                         stdin = subprocess.PIPE,
                         stdout = subprocess.PIPE,
                         stderr = subprocess.STDOUT,
                         shell = shell,
                         close_fds = sys.platform.startswith('win'),
                         universal_newlines = True,
                         env = env)
    data = p.stdout.read()
    rc = p.wait()
    if rc and not ignore_errors:
        sys.stderr.write('Failed to execute command: %s\n%s\n' % (command, data))
        return ''

    return data

def main(repos, rev):
    # verify that rev parameter is an int
    try:
        int(rev)
    except ValueError:
        sys.stderr.write("Parameter <rev> must be an int, was given %s\n" % rev)
        return
    repo = REPOSITORY+repos.split("/")[-2]+"/"+repos.split("/")[-1]
    print repo
    # get the svn file system object
    #fs_ptr = svn.repos.svn_repos_fs(svn.repos.svn_repos_open(
    #        svn.core.svn_path_canonicalize(repos)))
    command = SVN_PATH + "svn log -r " + str(rev) + " -l 1 -v " + repo +" --username " + SVN_USER + " --password "+ SVN_PASSWORD + " --non-interactive"
    if DEBUG:
        print command

    logData = execute(command,
                   env = {'LANG': 'en_US.UTF-8'}, shell=True)

    if DEBUG:
        print logData	
    log = ""
    logDataLines = logData.split('\n')
    if len(logDataLines) < 3:
        print 'no log found in ',rev
        return

    logLineCount = logDataLines[1].split(' ')[12]
    logLineCount = int(logLineCount)

    firstChangePath = logDataLines[3].split(' ')[4]
    if firstChangePath.find('branch') < 0:
        print 'no branch found in ',rev
        return

    branchSlashIndex = firstChangePath.find('/',firstChangePath.find('branches')+9,len(firstChangePath)-1)
    if branchSlashIndex == -1:
    	branch = firstChangePath
    else:
	branch = firstChangePath[0:branchSlashIndex]
    if DEBUG:
        print 'branch=',branch
    print branch,' ',rev

    for i in range(len(logDataLines)-2-logLineCount,len(logDataLines)-2):
        log+=logDataLines[i]+"\n"
    if DEBUG:
        print "log=",log
    # get the log message
    #log = svn.fs.svn_fs_revision_prop(fs_ptr, int(rev),
    #                                svn.core.SVN_PROP_REVISION_LOG)
    # error if log message is blank
    if len(log.strip()) < 1:
        sys.stderr.write("Log message is empty, no review request created\n")
        return

    author = logDataLines[1].split(' ')[2]
    # get the author
    #author = svn.fs.svn_fs_revision_prop(fs_ptr, int(rev),
    #                                   svn.core.SVN_PROP_REVISION_AUTHOR)
    # error if author is blank
    if len(author.strip()) < 1:
        sys.stderr.write("Author is blank, no review request created\n")
        return

    # check whether to create a review, based on presence of word
    # 'review' with prefix
    review = r'(?:publish|draft)(?: )?(?:update)?(?: )?(?:branch)?(?: )?review'
    if not re.search(review, log, re.M | re.I):
        print 'No review requested'
        return

    # check for update to existing review
    m = re.search(r'update(?: )?(?:branch)?(?: )?review:([0-9]+)', log, re.M | re.I)
    if m:
        reviewid = '--review-request-id=' + m.group(1)
    else:
        reviewid = ''

    # check whether to publish or leave review as draft
    if re.search(r'draft(?: )?(?:update)?(?: )?(?:branch)?(?: )?review', log, re.M | re.I):
        publish = ''
    else:
        publish = '-p'

    # get previous revision number -- either 1 prior, or
    # user-specified number
    m = re.search(r'after(?: )?revision:([0-9]+)', log, re.M | re.I)
    if m:
        prevrev = m.group(1)
    else:
        prevrev = int(rev) - 1
    
    branchlog = ''
    m = re.search(r'(?:branch)(?: )?review', log, re.M | re.I)
    if m:
        command = SVN_PATH + "svn log --stop-on-copy " + repo + branch +" --username " + SVN_USER + " --password "+ SVN_PASSWORD + " --non-interactive"
        if DEBUG:
            print command

        branchlog = execute(command,
                       env = {'LANG': 'en_US.UTF-8'}, shell=True)
        branchloglines = branchlog.splitlines()
        branchcount = 0
        for branchlogline in reversed(branchloglines):
            if len(branchlogline.split('|')) == 4:
                branchcount += 1
			# sometimes fetch the first commit from branch cannot get the diff,
			# but most time, need fetch from the first commit
            if len(branchlogline.split('|')) == 4 and branchcount == 1:
                prevrev = int(branchlogline.split(' ')[0][1:])
                break

    # check for an explicitly-provided base path (must be contained
    # within quotes)
    m = re.search(r'base ?path:[\'"]([^\'"]+)[\'"]', log, re.M | re.I)
    if m:
        base_path = m.group(1)
    else:
        base_path = ''

    # get bug numbers referenced in this log message
    ticket_command_re = re.compile(ticket_command)
    ticket_re = re.compile(ticket_prefix + '([0-9]+)')

    ticket_ids = []
    ticket_cmd_groups = ticket_command_re.findall(log)
    for cmd, tkts in ticket_cmd_groups:
        funcname = supported_ticket_cmds.get(cmd.lower(), '')
        if funcname:
            for tkt_id in ticket_re.findall(tkts):
                ticket_ids.append(tkt_id)

    if ticket_ids:
        bugs = '--bugs-closed=' + ','.join(ticket_ids)
    else:
        bugs = ''

    # summary is log up to first period+space / first new line / first 250 chars
    # (whichever comes first)
    description = log
    if len(branchlog) > 0:
        description = branchlog
        description = description.replace('------------------------------------------------------------------------', '\n')
    summary = '--summary=' + log[:250].splitlines().pop(0).split('. ').pop(0)
    try:
        description     = "--description=(from [%s] to [%s]) %s" % (prevrev, rev, description[:3000])
    except:
        description = ""
    print description
    # other parameters for postreview
    repository_url  = '--repository-url='+repo
    password        = '--password=' + PASSWORD
    username        = '--username=' + USERNAME
    submitas        = '--submit-as=' + author
    revision        = '%s:%s' % (prevrev, rev)
    server	= '--server='+SERVER
    if len(SVN_USER) > 0:
        svnuser = '--svn-username='+SVN_USER
    if len(SVN_PASSWORD) > 0:
        svnpassword = '--svn-password='+SVN_PASSWORD

	#branch and include:execute svnlook dirs-changed -r rev repo
    brancharg = ""
    incl = ""
#     try:
#         if int(rev) - int(prevrev) > 1 :
#             if DEBUG:
#                 print SVNLOOK_PATH + "svnlook dirs-changed -r" + rev + " " + repos
#             branch = execute(SVNLOOK_PATH + "svnlook dirs-changed -r" + rev + " " + repos,
#                    env = {'LANG': 'en_US.UTF-8'}, shell=True)
#             branch = branch.split('\n')[0]
#             branch = branch.strip(' \t\n\r')
#     except:
#         logging.exception("parse branch but failed")
    if len(branch) > 0:
        brancharg = "--branch " + branch
        incl = "-I" + branch

    # common arguments
    args = [repository_url, username, password, publish,
            submitas, base_path, reviewid, server, incl]
    if len(SVN_USER) > 0 and len(SVN_PASSWORD) > 0:
        args += [svnuser, svnpassword] 
    if DEBUG:
        args += ['-d']

    # filter out any potentially blank args, which will confuse rbt
    args = [i for i in args if len(i) > 1]

    # if not updating an existing review, add extra arguments
    #if len(reviewid) == 0:
    #    args += [summary, description]
    args += [summary, description]
    if len(bugs) != 0:
        args += [bugs]

    argstr = " ".join(map("'{0}'".format, args)) + " " + brancharg + " '" + revision + "'"
    rbtcommand = os.path.join(POSTREVIEW_PATH, 'rbt') + ' post ' + argstr
    # Run Review Board rbt script
    if DEBUG:
        print rbtcommand
    data = execute(rbtcommand,
                   env = {'LANG': 'en_US.UTF-8'}, shell=True)

    if DEBUG:
        print data

if __name__ == '__main__':
	try:
		main()
	except:
		import traceback
		traceback.print_exc()
		raise
