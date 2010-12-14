#!/usr/bin/env python

"""

	gmkdir
	GDataCopier, http://gdatacopier.googlecode.com/
	
	Copyright 2010 Eternity Technologies.
	Distributed under the terms and conditions of the GNU/GPL v3
	
	GDataCopier is free software and comes with absolutely NO WARRANTY. Use 
	of this software is completely at YOUR OWN RISK.
	
	Version 2.2.0
		
"""

__version__ = "2.2.0"
__author__  = "Devraj Mukherjee, Matteo Canato"


"""
	Imports the required modules 
"""

try:
	from optparse import OptionParser
        import ConfigParser
	import datetime
	import sys
	import os
	import re
	import signal
	import getpass
        from gdatacopier import helpers
        from gdatacopier.exceptions import *
except:
	print "gmkdir failed to find some basic python modules, please validate the environment"
	exit(1)

try:
        import gdata
        import gdata.docs.service
        import gdata.gauth
        import gdata.docs.data
        import gdata.docs.client
except:
	print "gmkdir %s requires gdata-python-client v2.0+, fetch from Google at" % __version__
	print "<http://code.google.com/p/gdata-python-client/>"
	exit(1)

try:
        # Add logs functionality
        import logging
        LOG = logging.getLogger(helpers.LOGGER_NAME)
except:
	print "gmkdir failed to find logging python modules, please validate the environment"
	exit(1)

"""
    Default values read from configuration file
"""
defaults = {
    'configdir' : '~/.gdatacopier/',
    'config' : 'gdatacopierrc',
}

"""
    The following fields are update when oauth 2 legged is used and values are
    read from a configuration file
"""
oauth_values = {
    'consumer_key'    : None,
    'consumer_secret' : None,
}

"""
	Methods
"""
def signal_handler(signal, frame):
    print "\n[Interrupted] Bye Bye!"
    sys.exit(0)

"""
    Setup the global (root, basic) configuration for logging.
"""
def setup_logger(options):
    msg_format = '%(message)s'
    if options.debug:
        level = logging.DEBUG
        msg_format = '%(levelname)s:%(name)s:%(message)s'
    elif options.verbose:
        level = logging.DEBUG
    elif options.silent:
        level = logging.ERROR
    else:
        level = logging.INFO
    # basicConfig does nothing if it's been called before
    # (e.g. in run_interactive loop)
    # TODO insert LOG file path
    logging.basicConfig(level=level, format=msg_format)
    # Redundant for single-runs, but necessary for run_interactive.
    LOG.setLevel(level)
    # XXX: Inappropriate location (style-wise).
    if options.debug:
        LOG.debug('Gdata will be imported from ' + gdata.__file__)

"""
	Checks to see if folder exists, otherwise creates it
"""
def make_folder(server_string, options):
	username, document_path = server_string.split(':', 1)
	
	if not helpers.is_email(username):
		LOG.error("Usernames must be provided as your full Gmail address, hosted domains included.")
		sys.exit(2)
		
	doc_param_parts = document_path.split('/')

	if len(doc_param_parts) < 1:
		LOG.error("no folder name provided, aborting!")
		sys.exit(2)

	if len(doc_param_parts) > 1 and not (doc_param_parts[1] == '' or doc_param_parts[1] == '*'):
            folder_name = doc_param_parts[1]
            create_subfolder = False

	if len(doc_param_parts) > 2 and not (doc_param_parts[2] == '' or doc_param_parts[2] == '*'):
            subfolder_name = doc_param_parts[2]
            create_subfolder = True

	# Get a handle to the document list service
        LOG.info("Logging into Google server as %s" % (username))
        gd_client = gdata.docs.client.DocsClient(source='etk-gdatacopier-v2')
        """
            NOTE: starting Jan 2011 Google Document List API will support only
            SSL connection (spreedsheets aren't under SSL yet)
            http://code.google.com/intl/it/apis/documents/forum.html?place=topic%2Fgoogle-documents-list-api%2FaEDGbZMul9s%2Fdiscussion
        """
        gd_client.ssl = True                # Force all API requests through HTTPS
        gd_client.api_version = '3.0'       # Force API version 3.0

        if (options.debug):
            gd_client.http_client.debug = True  # Set to True for debugging HTTP requests
        else:
            gd_client.http_client.debug = False

	try:
            # Authenticate to the document service'
            helpers.login(username, oauth_values, options, gd_client)

            LOG.info("Fetching folder list feeds from Google servers for %s ... " % (username))

            existing_folder = helpers.get_folder_entry(gd_client, folder_name)

            if create_subfolder == False:
                # Create a standard folder. NOTE: Google allows to have multiple
                # folders with the same name
                new_folder = gd_client.Create(gdata.docs.data.FOLDER_LABEL, folder_name)
            else:
                # Create a Subfolder but we check if the main folder exists
                if existing_folder != None:
                    new_folder = gd_client.Create(gdata.docs.data.FOLDER_LABEL, subfolder_name, folder_or_id=existing_folder)
                else:
                    raise GDataCopierFolderNotExists("Unable to create subfolder '%s'. Parent folder '%s' not exists!" % (subfolder_name, folder_name))

            # Print (sub)folder name if all is ok
            LOG.info("Folder %s created!" % new_folder.title.text)

	except gdata.client.BadAuthentication:
		LOG.error("Standard login failed. Bad Password!")
		sys.exit(2)
	except gdata.client.CaptchaChallenge:
		LOG.error("Captcha required, please login using the web interface and try again.")
		sys.exit(2)
	except gdata.client.Unauthorized:
		LOG.error("Unauthorized!\nCheck the OAuth key/secret stored into gdatacopierrc file.")
		sys.exit(2)
	except gdata.client.Error, e:
		LOG.error("OAuth login failed. Reason: %s \n" % e[0]['reason'])
		sys.exit(2)
        except GDataCopierFolderNotExists, e:
                LOG.error('Error: %s\n' % e)
                sys.exit(2)
	except Exception, e:
		LOG.error("Failed. %s" % e)
		sys.exit(2)

	
def parse_user_input():	
	usage  = "usage: %prog [options] username@domain.com:/[foldername]*\n"
	usage += "              where [foldername] is the name of the folder you wish to create"
	parser = OptionParser(usage)

	parser.add_option('-s', '--silent',
                            action = 'store_true',
                            dest = 'silent',
                            default = False,
                            help = 'decreases verbosity, supresses all messages '
                                    'but summaries and critical errors')
	parser.add_option('-p', '--password',
                            dest = 'password',
                            help = 'password for the user account, use with '
                                    'extreme caution. Could be stored in logs/history')
        parser.add_option('--configdir',
                            dest='configdir',
                            action='store', 
                            default=defaults['configdir'],
                            help='look in DIR for config/data files', metavar='DIR')
        parser.add_option('--config',
                            dest='config',
                            action='append',
                            default=defaults['config'],
                            help='load configuration from FILE',
                            metavar='FILE')
        parser.add_option('--debug', 
                            dest='debug',
                            action='store_true',
                            default = False,
                            help=('Enable all debugging output, including HTTP data'))
        parser.add_option('--verbose', 
                            dest='verbose',
                            action='store_true',
                            default = False,
                            help='Print all messages.')
	parser.add_option('--standard_login',
                            action = 'store_true',
                            dest = 'standard_login',
                            default = False,
                            help = 'use authentication with standard login')
	parser.add_option('--two_legged_oauth',
                            action = 'store_true',
                            dest = 'two_legged_oauth',
                            default = False,
                            help = 'use OAuth 2-legged authentication, \
                                    use in combination with a configuration file. \
                                    Use with extreme caution')
						
	(options, args) = parser.parse_args()

	greet(options)

        # Set up the logger
        setup_logger(options)
	
	# arg1 must be a remote server string to fetch document lists
	
	if not len(args) == 1 or (not helpers.is_remote_server_string(args[0])):
		print "you most provide a remote server address as username@gmail.com:/[foldername]"
		sys.exit(1)

        # Exit if user provide both standard login and oauth options
        if (options.two_legged_oauth and options.standard_login):
            print "You have to select only one authentication method"
            exit(2)

        # Exit if user don't provide the login type
        if not (options.two_legged_oauth or options.standard_login):
            LOG.error("You have to select an authentication method: --standard_login OR --two_legged_oauth")
            exit(3)

        if (options.two_legged_oauth):
            # Check if configdir exists
            configdir_type = 'Default'
            if options.configdir != defaults['configdir']:
                configdir_type = 'Specified'
            configdir = helpers.expand_user_vars(options.configdir)
            if not os.path.exists(configdir):
                raise GDataCopierOperationError('%s config/data dir "%s" does not '
                        'exist - create or specify alternate directory with '
                        '--configdir option' % (configdir_type, configdir))
            if not os.path.isdir(configdir):
                raise GDataCopierOperationError('%s config/data dir "%s" is not a '
                        'directory - fix or specify alternate directory with '
                        '--configdir option' % (configdir_type, configdir))
            if not os.access(configdir, os.W_OK):
                raise GDataCopierOperationError('%s config/data dir "%s" is not writable '
                        '- fix permissions or specify alternate directory with '
                        '--configdir option'% (configdir_type, configdir))

            # Check if configuration file exists
            path = os.path.join(os.path.expanduser(options.configdir), options.config)
            LOG.debug('processing config %s\n' % path)
            if not os.path.exists(path):
                raise GDataCopierOperationError('configuration file %s does not exist' % path)
            elif not os.path.isfile(path):
                raise GDataCopierOperationError('%s is not a file' % path)

            """
                Read from configuration file.
                An example of configuration file is this:
                    [oauth]
                    consumer_key: yourdomain.com
                    consumer_secret: rt3Fweg/AGrG0t3FwegB
            """
            try:
                config = ConfigParser.ConfigParser()
                config.read(path)
                oauth_values['consumer_key'] = config.get("oauth", "consumer_key")
                oauth_values['consumer_secret'] = config.get("oauth", "consumer_secret")
            except ConfigParser.NoSectionError, o:
                raise GDataCopierConfigurationError('configuration file %s missing section (%s)' % (path, o))
            except ConfigParser.NoOptionError, o:
                raise GDataCopierConfigurationError('configuration file %s missing option (%s)' % (path, o))
            except (ConfigParser.DuplicateSectionError,ConfigParser.InterpolationError,
                        ConfigParser.MissingSectionHeaderError,ConfigParser.ParsingError), o:
                raise GDataCopierConfigurationError('configuration file %s incorrect (%s)' % (path, o))
            except GDataCopierConfigurationError, o:
                raise GDataCopierConfigurationError('configuration file %s incorrect (%s)' % (path, o))

	"""
		If password not provided as part of the command line arguments, prompt the user
		to enter the password on the command line
	"""
	if (options.standard_login and options.password == None):
		options.password = getpass.getpass()

        return options, args

# Prints Greeting
def greet(options):
    if not options.silent:
        print "gmkdir %s, folder creation utility. Copyright 2010 Eternity Technologies" % __version__
        print "Released under the GNU/GPL v3 at <http://gdatacopier.googlecode.com>\n"

# main() is where things come together, this joins all the messages defined above
# these messages must be executed in the defined order
def main():
    try:
	signal.signal(signal.SIGINT, signal_handler)
        # Check to see we have the right options or exit
	options, args = parse_user_input()
        # Call the method
        make_folder(args[0], options)
    # Catch exceptions
    except KeyboardInterrupt:
        LOG.warning('Operation aborted by user (keyboard interrupt)\n')
        sys.exit(0)
    except GDataCopierConfigurationError, o:
        LOG.error('Configuration error: %s\n' % o)
        sys.exit(2)
    except GDataCopierOperationError, o:
        LOG.error('Error: %s\n' % o)
        sys.exit(3)
    except StandardError, o:
        LOG.critical(
            '\nException: please read docs/BUGS and include the '
            'following information in any bug report:\n\n'
        )
        LOG.critical('  GDataCopier version %s\n' % __version__)
        LOG.critical('  Python version %s\n\n' % sys.version)
        LOG.critical('Unhandled exception follows:\n')
        (exc_type, value, tb) = sys.exc_info()
        import traceback
        tblist = (traceback.format_tb(tb, None)
                  + traceback.format_exception_only(exc_type, value))
        if type(tblist) != list:
            tblist = [tblist]
        for line in tblist:
            LOG.critical('  %s\n' % line.rstrip())
        LOG.critical('\nPlease also include configuration information from running gmkdir\n')
        sys.exit(4)

# Begin execution of the main method since we are at the bottom of the script	
if __name__ == "__main__":
	main()
	
"""
	End of Python file
"""
