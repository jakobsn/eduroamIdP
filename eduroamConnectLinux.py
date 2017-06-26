from subprocess import check_output, call, Popen
from time import sleep

def main():
    if(isConnected()):
        print("You are already connected to eduroam")
        return
    print("Welcome to python client for setting up eduroam with certificates")
    print("Please provide the required information:")
    identity = input("Identity: ")
    client_cert = input("Client certificate (full path): ")
    ca_cert = input("Certification authority certificate (full path): ")
    private_key_password = input("Private key password: ")
    private_key = input("Private key (full path): ")
    if(packageExists("network-manager")):
        choice= input("Network-manager detected, would you like to use wpa_supplicant instead? (switches off network-manager) [y/N]: ")
        if(choice is 'y' or choice is 'Y'):
            call("""sudo service network-manager stop""", shell=True)
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
        output = check_output('dpkg -l | grep -E \'^ii\' | grep %s' % (package), shell=True)
    except:
        pass
    if output:
        return True
    return False


# Connect to eduroam with network-manager client
def networkManagerConnect(identity, client_cert, ca_cert, private_key_password, private_key, ifName=getIfName()):
    print("Setting up connection...")
    try:
        connection = check_output("""nmcli con add type wifi con-name eduroam ifname %s ssid eduroam -- \
        wifi-sec.key-mgmt wpa-eap 802-1x.eap tls 802-1x.identity %s \
        802-1x.client-cert %s 802-1x.ca-cert %s 802-1x.private-key-password %s  802-1x.private-key %s"""\
        % (ifName, identity, client_cert, ca_cert, private_key_password, private_key), shell=True)
    except:
        return False
    print(str(connection).strip("b\"").strip('\""').strip("\\n"))
    return True


# Create config file for WPA supplicant
def wpaSupplicantConfig(identity, client_cert, ca_cert, private_key_password, private_key, configPath):
    try:
        call("""sudo bash -c \'printf \"network={
        ssid="\\\"eduroam\\\""
        key_mgmt=WPA-EAP
        proto=WPA2
        eap=TLS
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
        driver = " -D " + driver
    try:
        Popen("""sudo wpa_supplicant -c %s -i %s%s""" % (configPath, ifName, driver), shell=True)
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
        call("""sudo dhclient %s""" % (ifName), shell = True)
    except:
        return False
    return True


# Connect to eduroam with WPA supplicant
def wpaSupplicantConnect(identity, client_cert, ca_cert, private_key_password, private_key, configPath='/etc/wpa_supplicant/wpa_supplicant.conf'):
    confSuccess= wpaSupplicantConfig(identity, client_cert, ca_cert, private_key_password, private_key,configPath)
    setUpSucess = wpaSupplicantSetUp(configPath)
    return confSuccess and setUpSucess


if __name__ == '__main__':
    main()
    #getIfName()
    #networkManagerConnect("jakobsn@fyrkat.no","/home/jakobsn/uninettca/jakobsn@fyrkat.no.crt","/home/jakobsn/uninettca/FyrkatRootCA.crt","","/home/jakobsn/uninettca/jakobsn@fyrkat.no.key")
    #print(PackageExists("network-manager"))
    #print(PackageExists("wpasupplicant"))
    #print(PackageExists("google-chrome"))
    #print(getIfName())
    #wpaSupplicantConnect("jakobsn@fyrkat.no","/home/jakobsn/uninettca/jakobsn@fyrkat.no.crt","/home/jakobsn/uninettca/FyrkatRootCA.crt","","/home/jakobsn/uninettca/jakobsn@fyrkat.no.key")
    #print(isConnected())
