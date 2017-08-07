from subprocess import check_output, call, Popen, PIPE
from time import sleep
from os import chown, chmod, makedirs, path, getenv
from requests import get
from pwd import getpwnam
from string import ascii_letters, digits
from random import randint, SystemRandom
from dialog import Dialog

# Create Dialog object to create Dialog widgets
d = Dialog(dialog="dialog")

def main(client_cert_url, ca_cert_url, private_key_url, save_path=path.expanduser('~') + '/eduroam_certificates/'):

    d.msgbox("Welcome to python client for setting up eduroam with certificates on linux \
    Press OK to get started:", title="Eduroam connect", width=50)

    if(isConnected()):
        #choice= input("You are already connected to eduroam, would you like to reset the current configuration? [y/N]: ")
        code = d.yesno("You are already connected to eduroam, would you like to reset the current configuration?", width=50)
        if(code is d.OK):
            resetConfiguration()
        else:
            return
    # If the network is configured but not connected that probably means that the configuration is corrupt, and will be reset.
    elif(networkManagerIsConfigured() or wpaSupplicantIsConfigured()):
        resetConfiguration()

    code, identity = d.inputbox("Please provide your user ID", width=50)
    if(code is d.CANCEL):
        return

    getAuthenticationFiles(client_cert_url, ca_cert_url, private_key_url, save_path)
    client_cert = save_path + getUrlFileName(client_cert_url)
    ca_cert = save_path + getUrlFileName(ca_cert_url)
    private_key = save_path + getUrlFileName(private_key_url)
    private_key_password = generatePassword()
    addPasswordToSSHKey(private_key, private_key_password)

    if(packageExists("network-manager")):
        #choice= input("Network-manager detected, would you like to use wpa_supplicant instead? (switches off network-manager) [y/N]: ")
        code = d.yesno("Network-manager detected, would you like to disable Network-manager and use wpa_supplicant instead? (Not recommended)", width=50)
        if(code is d.OK):
            networkManagerStop()
            networkManagerDisable()
            wpaSupplicantConnect(identity, client_cert, ca_cert, private_key, private_key_password)
        else:
            networkManagerStart()
            networkManagerEnable()
            networkManagerConnect(identity, client_cert, ca_cert, private_key, private_key_password)
    else:
        wpaSupplicantConnect(identity, client_cert, ca_cert, private_key, private_key_password)

# Adds password protection to private key
def addPasswordToSSHKey(private_key, private_key_password):
    Popen(["ssh-keygen", "-p", "-N", private_key_password, "-f", private_key])

# Generates random password with length between 10 and 30
def generatePassword():
    length = randint(10,30)
    chars = ascii_letters + digits + '!@#$%^&*()'
    return ''.join(SystemRandom().choice(chars) for i in range(length))

# Return only the filename found at the end of the url
def getUrlFileName(url):
    return url.split("/")[-1]

def getUserName():
    return path.expanduser('~').split("/")[-1]

def getUserId(name=getUserName()):
    return getpwnam(name).pw_uid

def getGroupId(name=getUserName()):
    return getpwnam(name).pw_gid

# Retrieve the wireless interface
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
    except:
        pass
    if output:
        return True
    return False

# Reset network configuration
def resetConfiguration():
    if(packageExists("network-manager")):
        networkManagerStart()
        if(networkManagerIsConfigured()):
            networkManagerRemoveConnection()
    networkManagerStop()
    wpaSupplicantRemoveConnection()
    d.msgbox("Current configuration has been removed", title="Success", width=50)
    return

# Connect to eduroam with network-manager client
def networkManagerConnect(identity, client_cert, ca_cert, private_key, private_key_password, ifName=getIfName()):
    try:
        process = Popen(["nmcli", "con", "add", "type", "wifi", "con-name", "eduroam", "ifname", ifName, \
        "ssid", "eduroam", "--", "wifi-sec.key-mgmt", "wpa-eap", "802-1x.eap", "tls", \
        "802-1x.identity", identity, "802-1x.client-cert", client_cert, "802-1x.ca-cert", ca_cert, \
        "802-1x.private-key-password", private_key_password, "802-1x.private-key", private_key], stdout=PIPE)
    except:
        d.msgbox(process.communicate()[0].decode('utf-8'), title="Error", width=50)
        return False
    d.msgbox(process.communicate()[0].decode('utf-8'), title="Success", width=50)
    return True

# Check if network-manager has an eduroam configuration
def networkManagerIsConfigured():
    if(not packageExists("network-manager")):
        return False
    networkManagerStart()
    connections = check_output(["nmcli", "connection", "show"])
    return "eduroam" in str(connections)

# Remove connection from network-manager
def networkManagerRemoveConnection():
    call(["nmcli", "con", "delete", "eduroam"])

def networkManagerStart():
    call(["service", "network-manager", "start"])

def networkManagerStop():
    call(["service", "network-manager", "stop"])

def networkManagerEnable():
    call(["systemctl", "enable", "network-manager.service"])

def networkManagerDisable():
    call(["systemctl", "disable", "network-manager.service"])

# Create config file for WPA supplicant
def wpaSupplicantConfig(identity, client_cert, ca_cert, private_key, private_key_password, configPath):
    try:
        file = open(configPath, "w")
        file.write("network={ \n")
        file.write("ssid=\"eduroam\" \n")
        file.write("key_mgmt=WPA-EAP \n")
        file.write("proto=WPA2 \n")
        file.write("eap=TLS \n")
        file.write("phase2=\"auth=MSCHAPV2\" \n")
        file.write("identity=\"%s\" \n" % identity)
        file.write("client_cert=\"%s\" \n" % client_cert)
        file.write("ca_cert=\"%s\" \n" % ca_cert)
        file.write("private_key_passwd=\"%s\" \n" % private_key_password)
        file.write("private_key=\"%s\" \n" % private_key)
        file.write("}")
        file.close()

        chown(configPath, getUserId(), getGroupId())
        chmod(configPath, 960)
    except:
        return False
    return True

# Set up the connection with WPA supplicant
def wpaSupplicantSetUp(configPath, ifName=getIfName(), driver=""):
    if(len(driver)):
        # The -D flag is added to the driver because the command can be executed without a driver.
        driver = " -D " + driver
    try:
        process = Popen(["wpa_supplicant", "-c", configPath, "-i", ifName, driver, "-B"])
    except:
        return False
    # Wait for WPA supplicant to complete negotiation
    wait_time = 1
    while(not isConnected()):
        sleep(wait_time)
        wait_time = wait_time * 2
        if(wait_time > 100):
            d.msgbox("Could not finish negotiation process, connection failed", title="Error", width=50)
            return False
    try:
        call(["dhclient", ifName])
    except:
        return False
    return True

# Connect to eduroam with WPA supplicant
def wpaSupplicantConnect(identity, client_cert, ca_cert, private_key, private_key_password, configPath='/etc/wpa_supplicant.conf'):
    confSuccess= wpaSupplicantConfig(identity, client_cert, ca_cert, private_key, private_key_password, configPath)
    setUpSucess = wpaSupplicantSetUp(configPath)
    if(confSuccess and setUpSucess):
        d.msgbox("wpa_supplicant has successfully been configured", title="Success", width=50)
    return confSuccess and setUpSucess

# Remove given config file
def wpaSupplicantRemoveConnection(configPath='/etc/wpa_supplicant.conf'):
    try:
        call(["rm", configPath])
    except:
        pass
    call(["killall", "wpa_supplicant"])
    call(["/etc/init.d/networking", "restart"])

# Check if the config file for eduroam connection exists
def wpaSupplicantIsConfigured():
    try:
        output = check_output(['grep', 'eduroam', '/etc/wpa_supplicant.conf'])
    except:
        return False
    return True

# Gets authentication files and stores them in a local folder
def getAuthenticationFiles(client_cert_url, ca_cert_url, private_key_url, save_path):
    makeDirectory(save_path)
    chown(save_path, getUserId(), getGroupId())
    chmod(save_path, 960)
    for url in [client_cert_url, ca_cert_url, private_key_url]:
        name = getUrlFileName(url)
        getFile(url, save_path + name)
    chown(save_path + name, getUserId(), getGroupId())
    chmod(save_path + name, 960)
    return

# Get file with http request
def getFile(url, save_path):
    request = get(url)
    with open(save_path, 'wb') as code:
        code.write(request.content)
    return request.status_code == 200

# Create new directory
def makeDirectory(new_path):
    if not path.exists(new_path):
        makedirs(new_path)

if __name__ == '__main__':
    main('http://localhost:8000/jakobsn@fyrkat.no.crt', 'http://localhost:8000/FyrkatRootCA.crt', 'http://localhost:8000/jakobsn_nopass@fyrkat.no.key')
    #print(getuser())
    #makeDirectory('/home/jakobsn/eduroam_certificates/')
    #getAuthentication(['http://localhost:8000/FyrkatRootCA.crt', 'http://localhost:8000/jakobsn@fyrkat.no.crt', 'http://localhost:8000/jakobsn@fyrkat.no.key'])
    #print(getFile('http://localhost:8000/FyrkatRootCA.crt', '/home/jakobsn/eduroam_certificates/', 'FyrkatRootCA.crt'))
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
    #print(wpaSupplicantIsConfigured())
    #print(generatePassword())
