import sys	#For sys.exit()
import re	#Regex library
import socket	#Library for sockets
import errno	#Error indication
import struct	#Performs conversions between Python values and bytes objects
import threading	#Multithreding library
from time import sleep

#----------Variables----------
detected_bulbs = {} #Dictionary of detected light bulbs ip->bulb map
bulb_idx2ip = {} #Index->ip
current_command_id = 0
DEBUGGING = True	#Turn on/off debugging messages
RUNNING = True	#Stops bulb detection loop
MCAST_GRP = '239.255.255.250' #Multicast group
MCAST_PORT = 1982 #Multicast port


#----------Sockets----------
#Creating socket	
scan_socket= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#SOCK_DGRAM <- allows UDP connection (SOCK.STREAM for TCP)
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#udp
#listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)#allows multiple instances
listen_socket.bind(("", 1982))#sock.bind((UDP_IP, UDP_PORT))
mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
listen_socket.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 0)#To stop looping back the send requests

#----------Functions----------
def debug(msg):
	if DEBUGGING:
		print(msg)

def next_cmd_id():
	"""Creates an Id to help request sender to correlate request and response"""
	global current_command_id
	current_command_id += 1
	return current_command_id

def print_cli_usage():
	"""Prints viable user commands"""
	print("Usage:")
	print("  q|quit: quit bulb manager")
	print("  h|help: print this message")
	print("  t|toggle <idx>: toggle bulb indicated by idx")
	print("  b|bright <idx> <bright>: set brightness of bulb with label <idx>")
	print("  r|refresh: refresh bulb list")
	print("  l|list: lsit all managed bulbs")

def get_param_value(data, param):
	'''
	Match line of 'param = value'
	'''
	param_re = re.compile(param+":\s*([ -~]*)") #match all printable characters
	match = param_re.search(data)
	value=""
	if match != None:
		value = match.group(1)
		return value

def send_search_broadcast():
	"""Multicast search request to all hosts in LAN, do not wait for response"""
	multicase_address = (MCAST_GRP, MCAST_PORT) #Tuple with Multicast group and port
	debug("\nSend search broadcast")
	msg = "M-SEARCH * HTTP/1.1\r\n" 
	msg = msg + "HOST: 239.255.255.250:1982\r\n"
	msg = msg + "MAN: \"ssdp:discover\"\r\n"
	msg = msg + "ST: wifi_bulb"
	#Sends SSDP? search request to the socket
	scan_socket.sendto(msg.encode(), multicase_address)#UDP
	#.encode() to encode string into bytestring
	sleep(1)

def handle_search_response(data):
	"""
	Parse search response and extract all interested data.
	If new bulb is found, insert it into dictionary of managed bulbs.
	"""
	#Compile the pattern into regex object
	location_re = re.compile("Location.*yeelight[^0-9]*([0-9]{1,3}(\.[0-9]{1,3}){3}):([0-9]*)")
	#https://regex101.com/ <-explanation. Grabs (Ex): Location: yeelight://192.168.1.239:55443
	# match() only attempts to match a pattern at the beginning of a string
	match = location_re.search(data)
	if match == None:
		debug( "invalid data received: " + data )
		return
	#	
	host_ip = match.group(1) #host_ip = /192.168.1.239(Ex)
	#Check if bulb is already known
	if host_ip in detected_bulbs:
		#If known, give an id
		bulb_id = detected_bulbs[host_ip][0]
	else:
		#If not give a new one
		bulb_id = len(detected_bulbs)+1
	host_port = match.group(3)
	model = get_param_value(data, "model")
	power = get_param_value(data, "power")
	bright = get_param_value(data, "bright")
	rgb = get_param_value(data, "rgb")
	supported = get_param_value(data, "support") #Grab supported methods
	# use two dictionaries to store index->ip and ip->bulb map
	detected_bulbs[host_ip] = [bulb_id, model, power, bright, rgb, host_port, supported]
	bulb_idx2ip[bulb_id] = host_ip

def bulbs_detection_loop():
	"""A standalone thread broadcasting search request and listening on all responses"""
	scan_socket.setblocking(0)
	listen_socket.setblocking(0)
	debug("bulbs_detection_loop running") #msg if debuging
	search_interval=30000
	read_interval=100
	time_elapsed=0

	while RUNNING:
		#send search broadcast every "search_interval"
		if time_elapsed%search_interval == 0:
		  send_search_broadcast()#Constructs and sends a search request to a socket scan_socket
		
		# scanner
		while True:
			try:
				DataBytes = scan_socket.recv(2048)#Receives data from the socket
				#.recv() receives TCP message
				data = DataBytes.decode()#Decode bytes->str
			except socket.error as e:
				err = e.args[0]
				if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
					break
				else:
					print(e)
					sys.exit(1)
			debug("search_socket:\n"+ data+"\n")
			handle_search_response(data)
		# passive listener 
		while True:
			try:
				DataBytes, addr = listen_socket.recvfrom(2048)
				#.recvfrom() receives UDP message
				data = DataBytes.decode()
			except socket.error as e:
				err = e.args[0]
				if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
					break
				else:
					print (e)
					sys.exit(1)
			debug("listener socket:\n"+ data+"\n")
			handle_search_response(data)

		time_elapsed+=read_interval
		sleep(read_interval/1000.0)
		#debug(time_elapsed)
	scan_socket.close()
	listen_socket.close()

def display_bulb(idx):
	"""Displays bulb information"""
	if not idx in bulb_idx2ip:
		print("error: invalid bulb idx")
		return
	bulb_ip = bulb_idx2ip[idx]
	model = detected_bulbs[bulb_ip][1]
	power = detected_bulbs[bulb_ip][2]
	bright = detected_bulbs[bulb_ip][3]
	rgb = detected_bulbs[bulb_ip][4]
	supported = detected_bulbs[bulb_ip][6]
	#TODO tidy up the printing
	print(str(idx) + ":\nip = "
		+bulb_ip + ",\nmodel = " + model
		+",\npower = " + power + ",\nbright = "
		+ bright + ",\nrgb = " + rgb+",\nmethods = "+supported+"\n")

def display_bulbs():
	"""Displays info of the known bulbs"""	
	print(str(len(detected_bulbs)) + " Managed bulbs:")
	for i in range(1, len(detected_bulbs)+1):
		display_bulb(i)

def operate_on_bulb(idx, method, params):
	'''
	Operate on bulb; no gurantee of success.
	Input data 'params' must be a compiled into one string.
	E.g. params="1"; params="\"smooth\"", params="1,\"smooth\",80"
	'''
	#TODO check if successful
	if not idx in bulb_idx2ip:
		print("error: invalid bulb idx")
		return	
	bulb_ip=bulb_idx2ip[idx]
	port=detected_bulbs[bulb_ip][5]
	try:
		tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		print("connect ",bulb_ip, port ,"...")
		tcp_socket.connect((bulb_ip, int(port)))
		msg="{\"id\":" + str(next_cmd_id()) + ",\"method\":\""
		msg += method + "\",\"params\":[" + params + "]}\r\n"
		tcp_socket.send(msg.encode())
		tcp_socket.close()
	except Exception as e:
		print("Unexpected error:", e)

def toggle_bulb(idx):
	operate_on_bulb(idx, "toggle", "")

def set_bright(idx, bright):
	operate_on_bulb(idx, "set_bright", str(bright))

def handle_user_input():
  '''
  User interaction loop.
  '''
  while True:
    command_line = input("Enter a command: ")
    valid_cli=True
    debug("command_line=" + command_line)
    command_line.lower() # convert all user input to lower case, i.e. cli is caseless
	#create an array of word/parameters
    argv = command_line.split() # i.e. don't allow parameters with space characters
    if len(argv) == 0:
      continue
    if argv[0] == "q" or argv[0] == "quit":
      print("Bye!")
      return
    elif argv[0] == "l" or argv[0] == "list":
      display_bulbs()
	  #----------------------------------------
    elif argv[0] == "r" or argv[0] == "refresh":
      detected_bulbs.clear()
      bulb_idx2ip.clear()
      send_search_broadcast()
      sleep(0.5)
      display_bulbs()
    elif argv[0] == "h" or argv[0] == "help":
      print_cli_usage()
      continue
    elif argv[0] == "t" or argv[0] == "toggle":
      if len(argv) != 2:
        valid_cli=False
      else:
        try:
          i = int(float(argv[1]))
          toggle_bulb(i)
        except:
          valid_cli=False
    elif argv[0] == "b" or argv[0] == "bright":
      if len(argv) != 3:
        print("incorrect argc")
        valid_cli=False
      else:
        try:
          idx = int(float(argv[1]))
          print("idx"), idx
          bright = int(float(argv[2]))
          print("bright"), bright
          set_bright(idx, bright)
        except:
          valid_cli=False
    else:
      valid_cli=False

    if not valid_cli:
      print("error: invalid command line:", command_line)
      print_cli_usage()

#----------Main----------
print("Hello there buddy\n")
print_cli_usage()

#Creates a seperate thread that executes bulbs_detection_loop 
detection_thread = threading.Thread(target=bulbs_detection_loop)
#Start the thread
detection_thread.start()
# give detection thread some time to collect bulb info
sleep(0.2)
# user interaction loop
handle_user_input()
# user interaction end, tell detection thread to quit and wait
RUNNING = False
detection_thread.join()
sys.exit(0)
#Done