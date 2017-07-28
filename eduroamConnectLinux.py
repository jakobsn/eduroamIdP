from subprocess import check_output, call, Popen, PIPE
from time import sleep

def main():
    if(isConnected()):
        choice= input("You are already connected to eduroam, would you like to reset the current configuration? [y/N]: ")
        if(choice is 'y' or choice is 'Y'):
            resetConfiguration()
        else:
            return
    print("Welcome to python client for setting up eduroam with certificates on linux")
    print("Please provide the required information:")
    identity = input("Identity: ")
    client_cert = input("Client certificate (full path): ")
    ca_cert = input("Certification authority certificate (full path): ")
    private_key_password = input("Private key password: ")
    private_key = input("Private key (full path): ")

    if(packageExists("network-manager")):
        choice= input("Network-manager detected, would you like to use wpa_supplicant instead? (switches off network-manager) [y/N]: ")
        if(choice is 'y' or choice is 'Y'):
            networkManagerStop()
            wpaSupplicantConnect(identity, client_cert, ca_cert, private_key_password, private_key)
        else:
            networkManagerConnect(identity, client_cert, ca_cert, private_key_password, private_key)
    else:
        wpaSupplicantConnect(identity, client_cert, ca_cert, private_key_password, private_key)


def getInterface():
    return check_output('iwconfig 2>&1 | grep IEEE', shell=True)


# Check if the user already is connected to eduroam
def isConnected():
    interface = getInterface()
    return 'eduroam' in str(interface)


# Retrieve wireless interface name
def getIfName():
    interface = getInterface()
    ifName = str(interface).split(" ")[0].replace("b\'", "")
    return ifName


# Check if given package is installed in the system
def packageExists(package):
    output = 0
    try:
        p1 = Popen(["dpkg", "-l"], stdout=PIPE)
        p2 = Popen(["grep", package], stdin=p1.stdout, stdout=PIPE)
        output = p2.communicate()[0]
        print(output)
    except:
        pass
        #raise
    if output:
        return True
    return False


# Connect to eduroam with network-manager client
def networkManagerConnect(identity, client_cert, ca_cert, private_key_password, private_key, ifName=getIfName()):
    print("Setting up connection...")
    try:
        Popen(["nmcli", "con", "add", "type", "wifi", "con-name", "eduroam", "ifname", ifName, \
        "ssid", "eduroam", "--", "wifi-sec.key-mgmt", "wpa-eap", "802-1x.eap", "tls", \
        "802-1x.identity", identity, "802-1x.client-cert", client_cert, "802-1x.ca-cert", ca_cert, \
        "802-1x.private-key-password", private_key_password, "802-1x.private-key", private_key])
    except:
        return False
    return True


# Check if network-manager has an eduroam configuration
def networkManagerIsConfigured():
    connections = check_output(["nmcli", "connection", "show"])
    return "eduroam" in str(connections)


# Remove connection from network-manager
def networkManagerRemoveConnection():
    call(["sudo", "nmcli", "con", "delete", "eduroam"])


def networkManagerStart():
    call(["sudo", "service", "network-manager", "start"])


def networkManagerStop():
    call(["sudo", "service", "network-manager", "stop"])


# Create config file for WPA supplicant
def wpaSupplicantConfig(identity, client_cert, ca_cert, private_key_password, private_key, configPath):
    try:
        call("""sudo bash -c \'printf \"network={
        ssid="\\\"eduroam\\\""
        key_mgmt=WPA-EAP
        proto=WPA2
        eap=TLS
        phase2="\\\"auth=MSCHAPV2\\\""
        identity="\\\"%s\\\""
        client_cert="\\\"%s\\\""
        ca_cert="\\\"%s\\\""
        private_key_passwd="\\\"%s\\\""
        private_key="\\\"%s\\\""
        }\" > %s\' """ \
        % (identity, client_cert, ca_cert, private_key_password, private_key, configPath), shell=True)
        call("""sudo chown root:root %s""" % (configPath), shell=True)
    except:
        return False
    return True


# Set up the connection with WPA supplicant
def wpaSupplicantSetUp(configPath, ifName=getIfName(), driver=""):
    if(len(driver)):
        # The -D flag is added to the driver because the command can be executed without a driver.
        driver = " -D " + driver
    try:
        Popen(["sudo", "wpa_supplicant", "-c", configPath, "-i", ifName, driver])
    except:
        return False
    # Wait for WPA supplicant to complete negotiation
    wait_time = 1
    while(not isConnected()):
        sleep(wait_time)
        wait_time = wait_time * 2
        if(wait_time > 100):
            print("Could not finish negotiation process, connection failed")
            return False
    try:
        call(["sudo", "dhclient", ifName])
    except:
        return False
    return True


# Connect to eduroam with WPA supplicant
def wpaSupplicantConnect(identity, client_cert, ca_cert, private_key_password, private_key, configPath='/etc/wpa_supplicant.conf'):
    confSuccess= wpaSupplicantConfig(identity, client_cert, ca_cert, private_key_password, private_key,configPath)
    setUpSucess = wpaSupplicantSetUp(configPath)
    return confSuccess and setUpSucess


# Remove given config file
def wpaSupplicantRemoveConnection(configPath='/etc/wpa_supplicant.conf'):
    call(["sudo", "rm", configPath])
    call(["sudo", "killall", "wpa_supplicant"])
    call(["sudo", "/etc/init.d/networking", "restart"])


# Reset network configuration
def resetConfiguration():
    if(packageExists("network-manager")):
        networkManagerStart()
        if(networkManagerIsConfigured()):
            networkManagerRemoveConnection()
            return
        else:
            networkManagerStop()
    wpaSupplicantRemoveConnection()
    print("Current configuration has been removed")
    return


if __name__ == '__main__':
    main()
    #getIfName()
    #resetConfiguration()
    #networkManagerStart()
    #networkManagerRemoveConnection()
    #networkManagerStop()
    #networkManagerConnect("jakobsn@fyrkat.no","/home/jakobsn/uninettca/jakobsn@fyrkat.no.crt","/home/jakobsn/uninettca/FyrkatRootCA.crt","","/home/jakobsn/uninettca/jakobsn@fyrkat.no.key")
    #print(packageExists("network-manager"))
    #print(packageExists("wpasupplicant"))
    #print(packageExists("google-chrome"))
    #print(getIfName())
    #networkManagerStop()
    #wpaSupplicantConnect("jakobsn@fyrkat.no","/home/jakobsn/uninettca/jakobsn@fyrkat.no.crt","/home/jakobsn/uninettca/FyrkatRootCA.crt","","/home/jakobsn/uninettca/jakobsn@fyrkat.no.key")
    #print(isConnected())
    #wpaSupplicantConfig("jakobsn@fyrkat.no","/home/jakobsn/uninettca/jakobsn@fyrkat.no.crt","/home/jakobsn/uninettca/FyrkatRootCA.crt","","/home/jakobsn/uninettca/jakobsn@fyrkat.no.key", '/etc/wpa_supplicant.conf')
    #print(networkManagerIsConfigured())
    #networkManagerRemoveConnection()
