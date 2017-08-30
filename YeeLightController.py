import sys	#For sys.exit()
import re	#Regex library
import socket	#Library for sockets
import errno	#Error indication
import struct	#Performs conversions between Python values and bytes objects
import threading	#Multithreding library
from YeeBulb import YeeBulb
from time import sleep

#----------Variables----------
##Dictionary of discovered bulbs. {bulb_ip:YeeBulb)
detected_bulbs = {} #Dictionary of detected light bulbs ip->bulb map
bulb_id2ip = {} #{bulb_index:bulb_ip}
supported_properties = ["power", "bright", "ct", "rgb", "hue", "sat", "color_mode", "flowing", "delayoff", "flow_params", "music_on", "name"]
DEBUGGING = False	#Turn on/off debugging messages
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

def print_cli_usage():
	"""Prints viable user commands"""
	print("Usage:")
	print("  q|quit: quit bulb manager")
	print("  h|help: print this message")
	print("  on: Turn the bulb on")
	print("  off: Turn the bulb off")
	print("  t|toggle <idx>: toggle bulb indicated by idx")
	print("  b|bright <idx> <bright>: set brightness of bulb with label <idx>")
	print("  r|refresh: refresh bulb list")
	print("  l|list: list all managed bulbs")
	print("  ct|ColorTemp <idx> <temperature> <effect> <duration>: set color temperature (1700K <= ct_value <= 6500K")
	print("  rgb <idx> <rgb value> <effect> <duration>: set rgb value (0 <= rgb_value <= 16777215)")
	print("  hue <idx> <hue> <sat> <effect> <duration>: set color hue (0 <= hue <= 359,  0 <= sat <= 100)")
	print("  p|param <idx> <param_1> <param_2> ... <param_n>: get current bulb parameter state")
	print("  s|SetDef: Sets current bulb state as default.")
	print("  a|adjust: <idx> <property> <action> This method is used to change brightness, CT or color of a smart LED")
def get_param_value(data, param):
	"""
	Match line of 'param = value'
	"""
	param_re = re.compile(param + ":\s*([ -~]*)") #match all printable characters
	match = param_re.search(data)
	value=""
	if match != None:
		value = match.group(1)
		return value

def send_search_broadcast():
	"""
	Multicast search request to all hosts in LAN, do not wait for response
	"""
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
	If bulb is already known - update it's info
	"""
	#Compile the pattern into regex object
	location_re = re.compile("Location.*yeelight[^0-9]*([0-9]{1,3}(\.[0-9]{1,3}){3}):([0-9]*)")
	#https://regex101.com/ <-explanation. Grabs (Ex): Location: yeelight://192.168.1.239:55443
	# match() only attempts to match a pattern at the beginning of a string
	match = location_re.search(data)
	if match == None:
		debug( "invalid data received: " + data )
		return

	bulb_ip = match.group(1)
	#Check if bulb is already known
	if bulb_ip in detected_bulbs:
		#If known, grab an id
		bulb_id = detected_bulbs[bulb_ip].id
	else:
		#If not give a new one
		bulb_id = len(detected_bulbs)+1

	bulb_port = match.group(3)
	model = get_param_value(data, "model")
	name = get_param_value(data, "name")
	supported = get_param_value(data, "support") #Grab supported methods
	#Create a new entry for the bulb
	bulb_id2ip[int(bulb_id)] = bulb_ip
	detected_bulbs[bulb_ip] = YeeBulb(bulb_id, bulb_ip, bulb_port, model, name, supported.split())

def bulbs_detection_loop():
	"""	A standalone thread broadcasting search request and listening on all responses.	"""
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

def display_bulbs():
	"""	Displays info of the known bulbs. """	
	#TODO this could try to access a dead bulb
	print("Managed bulbs = "+str(len(detected_bulbs))+":")
	for keys, values in detected_bulbs.items():
		print(values.info())
		
def handle_user_input():
	"""	User interaction loop. """
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
		elif argv[0] == "r" or argv[0] == "refresh":
			detected_bulbs.clear()
			bulb_id2ip.clear()
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
					idx = int(float(argv[1]))
					ipb = bulb_id2ip[idx]
					detected_bulbs[ipb].toggle()
				except:
					valid_cli=False
		elif argv[0] == "b" or argv[0] == "bright":
			if not (3 <= len(argv) <= 5):
				print("incorrect argc")
				valid_cli=False
			else:
				try:
					idx = int(argv[1])
					ipb = bulb_id2ip[idx]
					response = (detected_bulbs[ipb]).set_bright(*argv[2:])
					print(response[1])
				except Exception as e:
					print(e)
					valid_cli=False
		#MINE-------------------------------------------
		elif argv[0] == "p" or argv[0] == "param":
			if len(argv) < 3:
				print("incorrect argc")
				valid_cli=False
			else:
				try:
					idx = int(argv[1])
					ipb = bulb_id2ip[idx]
					param_list = argv[2:] #Create a list of parameters
					response = (detected_bulbs[ipb]).get_state(param_list)
					state_list = response[1]
					for i in range(0, len(state_list)):
						print("\t" + param_list[i] + " = " + state_list[i])
				except Exception as e:
					print("Error: ", e)
					valid_cli=False

		elif argv[0] == "ct" or argv[0] == "ColorTemp":
			if not (3 <= len(argv) <= 5):
				print("incorrect argc")
				valid_cli=False
			else:
				try:
					idx = int(argv[1])
					ipb = bulb_id2ip[idx]
					response = detected_bulbs[ipb].set_ct(*argv[2:])#Using *args to unpack a list and pass to function (Python black magic)
					print(response[1])
				except Exception as e:
					print(e)
					valid_cli=False
		
		elif argv[0] == "rgb":
			if not (3 <= len(argv) <= 5):
				print("incorrect argc")
				valid_cli=False
			else:
				try:
					idx = int(argv[1])
					ipb = bulb_id2ip[idx]
					detected_bulbs[ipb].set_rgb(*argv[2:])
				except Exception as e:
					print(e)
					valid_cli=False

		elif argv[0] == "hue":
			if not (3 <= len(argv) <= 6):
				print("incorrect argc")
				valid_cli=False
			else:
				try:
					idx = int(argv[1])
					ipb = bulb_id2ip[idx]
					detected_bulbs[ipb].set_hue(*argv[2:])
				except Exception as e:
					print(e)
					valid_cli=False
		elif argv[0] == "on":
			if len(argv) != 2:
				print("incorrect argc")
				valid_cli=False
			else:
				try:
					idx = int(argv[1])
					ipb = bulb_id2ip[idx]
					detected_bulbs[ipb].turn_on()
				except Exception as e:
					print(e)
					valid_cli=False
		
		elif argv[0] == "off":
			if len(argv) != 2:
				print("incorrect argc")
				valid_cli=False
			else:
				try:
					idx = int(argv[1])
					ipb = bulb_id2ip[idx]
					detected_bulbs[ipb].turn_off()
				except Exception as e:
					print(e)
					valid_cli=False			
		
	#---not tested
		elif argv[0] == "set" or argv[0] == "SetDef":
			if len(argv) != 2:
				print("incorrect argc")
				valid_cli=False
			else:
				try:
					idx = int(argv[1])
					ipb = bulb_id2ip[idx]
					detected_bulbs[ipb].set_default()
				except Exception as e:
					print(e)
					valid_cli=False

		elif argv[0] == "a" or argv[0] == "adjust":
			if len(argv) != 4:
				print("incorrect argc")
				valid_cli=False
			else:
				try:
					idx = int(argv[1])
					ipb = bulb_id2ip[idx]
					detected_bulbs[ipb].set_adjust(*argv[2:])
				except Exception as e:
					print(e)
					valid_cli=False
		
		#MINE-------------------------------------------END
		else:
			valid_cli=False
		
		if not valid_cli:
			print("error: invalid command line:", command_line)
			print_cli_usage()

#----------Main----------
print("Welcome to Yeelight WifiBulb Lan controller")
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