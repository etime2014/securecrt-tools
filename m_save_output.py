# $language = "python"
# $interface = "1.0"

import os
import sys
import logging

# Add script directory to the PYTHONPATH so we can import our modules (only if run from SecureCRT)
if 'crt' in globals():
    script_dir, script_name = os.path.split(crt.ScriptFullName)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
else:
    script_dir, script_name = os.path.split(os.path.realpath(__file__))

# Now we can import our custom modules
from securecrt_tools import scripts
from securecrt_tools import sessions
from securecrt_tools import utilities
# Import message box constants names for use specifying the design of message boxes
from securecrt_tools.message_box_const import *

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {0}".format(script_name))


# ################################################   SCRIPT LOGIC   ##################################################

def script_main(script):
    """
    | MULTIPLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will prompt for a CSV list of devices, then will prompt for a command to run on each device in the list.
    The output from each device will be saved to a file.  The path where the file is saved is specified in the
    settings.ini file.

    :param script: A subclass of the scripts.Script object that represents the execution of this particular script
                   (either CRTScript or DirectScript)
    :type script: scripts.Script
    """
    session = script.get_main_session()

    # If this is launched on an active tab, disconnect before continuing.
    logger.debug("<M_SCRIPT> Checking if current tab is connected.")
    if session.is_connected():
        logger.debug("<M_SCRIPT> Existing tab connected.  Stopping execution.")
        raise scripts.ScriptError("This script must be launched in a not-connected tab.")

    # Load a device list
    device_list = script.import_device_list()
    if not device_list:
        return

    send_cmd = script.prompt_window("Enter the command to capture on each device.")
    logger.debug("Received command: '{0}'".format(send_cmd))

    if send_cmd == "":
        return

    # ##########################################  START JUMP BOX SECTION  ############################################
    # Check settings if we should use a jumpbox.  If so, prompt for password (and possibly missing values)
    use_jumpbox = script.settings.getboolean("Global", "use_jumpbox")

    if use_jumpbox:
        jumpbox = script.settings.get("Global", "jumpbox_host")
        j_username = script.settings.get("Global", "jumpbox_user")
        j_ending = script.settings.get("Global", "jumpbox_prompt_end")

        if not jumpbox:
            jumpbox = script.prompt_window("Enter the HOSTNAME or IP for the jumpbox".format(jumpbox))
            script.settings.update("Global", "jumpbox_host", jumpbox)

        if not j_username:
            j_username = script.prompt_window("JUMPBOX: Enter the USERNAME for {0}".format(jumpbox))
            script.settings.update("Global", "jumpbox_user", j_username)

        j_password = script.prompt_window("JUMPBOX: Enter the PASSWORD for {0}".format(j_username), hide_input=True)

        if not j_ending:
            j_ending = script.prompt_window("Enter the last character of the jumpbox CLI prompt")
            script.settings.update("Global", "jumpbox_prompt_end", j_ending)

    # ############################################  END JUMP BOX SECTION  ############################################

    # ########################################  START DEVICE CONNECT LOOP  ###########################################

    # We are not yet connected to a jump box.  This will be updated later in the code if needed.
    jump_connected = False
    # Create a filename to keep track of our connection logs, if we have failures.  Use script name without extension
    failed_log = session.create_output_filename("{0}-LOG".format(script_name.split(".")[0]), include_hostname=False)

    for device in device_list:
        hostname = device['hostname']
        protocol = device['protocol']
        username = device['username']
        password = device['password']
        enable = device['enable']

        if use_jumpbox:
            logger.debug("<M_SCRIPT> Connecting to {0} via jumpbox.".format(hostname))
            if "ssh" in protocol.lower():
                try:
                    if not jump_connected:
                        session.connect_ssh(jumpbox, j_username, j_password, prompt_endings=[j_ending])
                        jump_connected = True
                    session.ssh_via_jump(hostname, username, password)
                    per_device_work(session, enable, send_cmd)
                    session.disconnect_via_jump()
                except (sessions.ConnectError, sessions.InteractionError) as e:
                    with open(failed_log, 'a') as logfile:
                        logfile.write("Connect to {0} failed: {1}\n".format(hostname, e.message.strip()))
                    session.disconnect()
                    jump_connected = False
            elif protocol.lower() == "telnet":
                try:
                    if not jump_connected:
                        session.connect_ssh(jumpbox, j_username, j_password, prompt_endings=[j_ending])
                        jump_connected = True
                    session.telnet_via_jump(hostname, username, password)
                    per_device_work(session, enable, send_cmd)
                    session.disconnect_via_jump()
                except (sessions.ConnectError, sessions.InteractionError) as e:
                    with open(failed_log, 'a') as logfile:
                        logfile.write("Connect to {0} failed: {1}\n".format(hostname, e.message.strip()))
                    session.disconnect()
                    jump_connected = False
        else:
            logger.debug("<M_SCRIPT> Connecting to {0}.".format(hostname))
            try:
                session.connect(hostname, username, password, protocol=protocol)
                per_device_work(session, enable, send_cmd)
                session.disconnect()
            except sessions.ConnectError as e:
                with open(failed_log, 'a') as logfile:
                    logfile.write("Connect to {0} failed: {1}\n".format(hostname, e.message.strip()))
            except sessions.InteractionError as e:
                with open(failed_log, 'a') as logfile:
                    logfile.write("Failure on {0}: {1}\n".format(hostname, e.message.strip()))

    # If we are still connected to our jump box, disconnect.
    if jump_connected:
        session.disconnect()

    # #########################################  END DEVICE CONNECT LOOP  ############################################


def per_device_work(session, enable_pass, send_cmd):
    """
    This function contains the code that should be executed on each device that this script connects to.  It is called
    after establishing a connection to each device in the loop above.

    You can either put your own code here, or if there is a single-device version of a script that performs the correct
    task, it can be imported and called here, essentially making this script connect to all the devices in the chosen
    CSV file and then running a single-device script on each of them.
    """
    session.start_cisco_session(enable_pass=enable_pass)

    # Generate filename used for output files.
    full_file_name = session.create_output_filename(send_cmd)

    # Get the output of our command and save it to the filename specified
    session.write_output_to_file(send_cmd, full_file_name)

    # End cisco session
    session.end_cisco_session()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    # Initialize script object
    crt_script = scripts.CRTScript(crt)
    # Run script's main logic against the script object
    script_main(crt_script)
    # Shutdown logging after
    logging.shutdown()

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    # Initialize script object
    direct_script = scripts.DebugScript(os.path.realpath(__file__))
    # Run script's main logic against the script object
    script_main(direct_script)
    # Shutdown logging after
    logging.shutdown()