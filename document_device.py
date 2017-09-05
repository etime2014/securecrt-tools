﻿# $language = "python"
# $interface = "1.0"

# ################################################   SCRIPT INFO    ###################################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
# This script will grab the output for the list of commands in the document_device.json file that should exist in the
# same directory where this script is located.
#

# ################################################  SCRIPT SETTING  ###################################################
#
# Global settings that affect all scripts (output directory, date format, etc) is stored in the "global_settings.json"
# file in the "settings" directory.
#
# If any local settings are used for this script, they will be stored in the same settings folder, with the same name
# as the script that uses them, except ending with ".json".
#
# All settings can be manually modified in JSON format (the same syntax as Python lists and dictionaries). Be aware of
# required commas between items, or else options are likely to get run together and break the script.
#
# **IMPORTANT**  All paths saved in .json files must contain either forward slashes (/home/jcaesar) or
# DOUBLE back-slashes (C:\\Users\\Jamie).   Single backslashes will be considered part of a control character and will
# cause an error on loading.
#


# ################################################     IMPORTS      ###################################################
import os
import sys

# If the "crt" object exists, this is being run from SecureCRT.  Get script directory so we can add it to the
# PYTHONPATH, which is needed to import our custom modules.
if 'crt' in globals():
    script_dir, script_name = os.path.split(crt.ScriptFullName)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
else:
    script_dir, script_name = os.path.split(os.path.realpath(__file__))
os.chdir(script_dir)

# Now we can import our custom modules
import securecrt_tools.sessions as sessions
import securecrt_tools.settings as settings
import securecrt_tools.utilities as utils


# ################################################  LOAD SETTINGS   ###################################################

session_set_filename = os.path.join(script_dir, "settings", settings.global_settings_filename)
session_settings = settings.SettingsImporter(session_set_filename, settings.global_defs)

local_set_filename = os.path.join(script_dir, "settings", script_name.replace(".py", ".json"))
local_settings_default = {"__version": "1.0",
                          "IOS": ["show ver",
                                  "show int status",
                                  "show run",
                                  "show standby brief"],
                          "NXOS": ["show ver",
                                    "show int status",
                                    "show run",
                                    "show hsrp brief"],
                          "ASA": ["show ver",
                                  "show run"]
                          }
local_importer = settings.SettingsImporter(local_set_filename, local_settings_default)
local_settings = local_importer.get_settings_dict()


# ################################################     SCRIPT       ###################################################

def script_main(session):
    supported_os = ["IOS", "NXOS", "ASA"]
    if session.os not in supported_os:
        logger.debug("Unsupported OS: {0}.  Exiting program.".format(session.os))
        session.message_box("{0} is not a supported OS for this script.".format(session.os), "Unsupported OS",
                            options=sessions.ICON_STOP)
        return
    else:
        command_list = local_settings[session.os]

    for command in command_list:
        # Generate filename used for output files.
        full_file_name = session.create_output_filename(command)

        # Get the output of our command and save it to the filename specified
        session.write_output_to_file(command, full_file_name)

    # Clean up before closing session
    session.end()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, create our session object using the "crt" object provided by SecureCRT
if __name__ == "__builtin__":
    # Create a session object for this execution of the script and pass it to our main() function
    crt_session = sessions.CRTSession(crt, session_settings)
    if session_settings.get_setting('debug'):
        import logging
        logger = logging.getLogger("securecrt")
    script_main(crt_session)

# Else, if this script is run directly then create a session object without the SecureCRT API (crt object)  This would
# be done for debugging purposes (running the script outside of SecureCRT and feeding it the output it failed on)
elif __name__ == "__main__":
    direct_session = sessions.DirectSession(os.path.realpath(__file__), session_settings)
    if session_settings.get_setting('debug'):
        import logging
        logger = logging.getLogger("securecrt")
    script_main(direct_session)