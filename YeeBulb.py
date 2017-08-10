import socket

#----------Variables----------
DEBUGGING = True	#Turn on/off debugging messages

def debug(msg):
	if DEBUGGING:
		print(msg)

#Bulb class
class YeeBulb:
	def __init__(self, bulb_id, bulb_ip, bulb_port, model, power, bright, rgb, methods):
		self.id = bulb_id
		self.ip = bulb_ip
		self.port = bulb_port
		self.model = model
		self.power = power
		self.bright = bright
		self.rgb = rgb
		self.methods = methods #list of methods 
		
		self.cmd_id = int(0)
		#self.socket/???

	def info(self):
		"""Returns bulb information"""
		#TODO tidy up the printing
		info = ("Id = " + str(self.id)
				+",\nIP = " + str(self.ip)
				+",\nModel = "+ str(self.model)
				+",\nPower = "+ str(self.power)
				+",\nBrightness = " + str(self.bright)
				+",\nRGB = "+ str(self.rgb)
				+",\nMethods =\n")
		for i in range(0, len(self.methods)):
			info+="\t"+self.methods[i]+"\n"
		return info

	def supports_method(self, method):
		if method in self.methods:
			return True
		else:
			return False
	
	def next_id(self):
		"""Creates an Id to help request sender to correlate request and response"""
		self.cmd_id += 1
		return self.cmd_id
		
	def operate(self, method, params):
		'''
		Operate on bulb; no gurantee of success.
		Input data 'params' must be a compiled into one string.
		E.g. params="1"; params="\"smooth\"", params="1,\"smooth\",80"
		'''
		#TODO check if successful
		debug("\noperating\n")
		try:
			tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			debug("connecting " + self.ip +" "+ self.port +"...")
			tcp_socket.connect((self.ip, int(self.port)))
			msg="{\"id\":" + str(self.next_id()) + ",\"method\":\""
			msg += method + "\",\"params\":[" + params + "]}\r\n"
			tcp_socket.send(msg.encode())
			tcp_socket.close()
		except Exception as e:
			debug("Unexpected error:", e)

	def toggle(self):
		self.operate("toggle", "")

	def set_brightness(self, bright):
		self.operate("set_bright", str(bright))