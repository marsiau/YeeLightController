import socket
import re

#Bulb class
class YeeBulb:
	DISPLAY_MSG = True	#Turn on/off debugging messages
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

	@classmethod
	def display(cls, 	msg):
		if YeeBulb.DISPLAY_MSG:
 			print(msg)

	def supports_method(self, method):
		if method in self.methods:
			return True
		else:
			return False

	def next_id(self):
		"""Creates an Id to help request sender to correlate request and response"""
		self.cmd_id += 1
		return self.cmd_id

	def info(self):
		"""Returns bulb information"""
		#TODO tidy up the printing
		info = ("Id = " + str(self.id)
				+",\nIP = " + str(self.ip)
				+",\nPort = " + str(self.port) 
				+",\nModel = " + str(self.model)
				+",\nPower = " + str(self.power)
				+",\nBrightness = " + str(self.bright)
				+",\nRGB = " + str(self.rgb)
				+",\nMethods =\n")
		for i in range(0, len(self.methods)):
			info+="\t"+self.methods[i]+"\n"
		return info
	
	@staticmethod
	def get_val(data, param):
		"""	Match line of 'param = value' """
		param_re = re.compile(param + ":\[\s*([ -~]*)\]\}") #match all printable characters
		match = param_re.search(data)
		value = ""
		if match != None:
			value = match.group(1)
			return value

	@staticmethod
	def handle_result_message(method, params, data):
		"""
		Method to handle the bulb's response to operation request.
		"""
		if method == "get_prop":
			param_list = params.split(',')
			status_list = (YeeBulb.get_val(data, '"result"')).split(',')
			response = "Current status:\n"
			for i in range(0, len(param_list)):
				response += "\t" + param_list[i] + " = " + status_list[i] + "\n" 
		elif '"ok"' in data:
			response = "operations successful"
		elif '"error"' in data:
			respose = YeeBulb.get_val(data, '"error"')
		else:
			response = "Unknown error.\n Received data:\n" + data
		return response
 
	def operate(self, method, params):
		"""
		Input data 'params' must be a compiled into one string.
		E.g. params="1"; params="\"smooth\"", params="1,\"smooth\",80"
		E.x. { "id": 1, "method": "set_power", "params":["on", "smooth", 500]}
		"""
		YeeBulb.display("\nOperating")
		if not self.supports_method(method):
			YeeBulb.display("ERROR\nMethod is not supported.")
		else:
			try:
				tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				YeeBulb.display("connecting " + self.ip +" "+ self.port +"...")
				tcp_socket.connect((self.ip, int(self.port)))
				msg="{\"id\":" + str(self.next_id()) + ",\"method\":\""
				msg += method + "\",\"params\":[" + params + "]}\r\n"
				tcp_socket.send(msg.encode())
				YeeBulb.display("Dealing with response")
				DataBytes = tcp_socket.recv(2048)
				data = DataBytes.decode()#Decode bytes->str
				response_msg = YeeBulb.handle_result_message(method, params, data)
				YeeBulb.display(response_msg + "\n")
				tcp_socket.close()
			except Exception as e:
				YeeBulb.display("Unexpected error:", e)

	def get_state(self, req_params):
		"""	Method to retrieve current state of specified bulb parameters	"""
		params = ""
		for i in range(0, len(req_params)):
			params += "\"" + req_params[i] + "\""
			if i != len(req_params) - 1:
				params +=","
		self.operate("get_prop", params)
		
	# def bulb_update():
		# use get_properties to update bulb info

	def set_ct(self, ct_value, effect = "sudden", duration = 30):
		"""
		Method to change the color temperature of the bulb
		ct_value - targeted color temperature (1700 <= ct_value <= 6500 (k))
		effect - sudden/smooth
		duration - total time of gradual change if smooth mode is selected (duration > 30 (ms))
		"""
		#TODO check if on
		if 1700 <= ct_value <= 6500 and duration > 30:
			params = str(ct_value) +",\"" + str(effect) + "\"," + str(duration)
			self.operate("set_ct_abx", params)

	def set_rgb(self, rgb_value, effect = "sudden", duration = 30):
		"""
		Metod to change the color of the bulb
		rgb_value - the target color (decimal int;  0 <= rgb_value <= 16777215)
		"""
		if 0 <= rgb_value <= 16777215 and duration >= 30:
			params = str(rgb_value) +",\"" + str(effect) + "\"," + str(duration)
			self.operate("set_rgb", params)

	def set_hue(self, hue, sat = 0, effect = "sudden", duration = 30):
		"""
		hue - target hue value (decimal int; 0 <= hue <= 359) 
		sat - target saturation value (int; 0 <= sat <= 100)
		"""
		if 0 <= hue <= 359 and 0 <= sat <= 100 and duration >= 30:
			params = str(hue) + "," + str(sat) +",\"" + str(effect) + "\"," + str(duration)
			self.operate("set_hsv", params)
	
	def set_bright(self, bright, effect = "sudden", duration = 30):
		"""
		Method to set the brightness of the bulb
		bright - target brightness (1 <= bright <= 100)
		"""
		if 1 <= bright <= 100 and duration >= 30:
			params = str(bright) + ",\"" + str(effect) + "\"," + str(duration)
			self.operate("set_bright", params)
	
	#NOT TESTED
	def turn_on(self, effect = "sudden", duration = 30):
		""" Method to turn on the bulb. """
		params = "\"on\"" + ",\"" + str(effect) + "\"," + str(duration)
		self.operate("set_power", params)

	def turn_off(self, effect = "sudden", duration = 30):
		""" Method to turn off the bulb. """
		params = "\"off\"" + ",\"" + str(effect) + "\"," + str(duration)
		self.operate("set_power", params)

	def toggle(self):
		""" Toggles on/off. """
		self.operate("toggle", "")

	def set_default(self):
		"""Sets current bulb state as default. """
		#TODO check if on
		self.operate("set_default", "")

	def start_cf(self, count, action, flow_expression):
		"""
		This method is used to start a color flow. Color flow is a series of smart
		LED visible state changing. It can be brightness changing, color changing or color
		temperature changing. This is the most powerful command. All recommended scenes,
		e.g. Sunrise/Sunset effect is implemented using this method. With the flow expression, user
		can actually “program” the light effect.
		Args:
			count: total number of visible state changing. 0 means infinite loop.
			action: action taken after the flow is stopped.
				0 means smart LED recover to the state before the color flow started.
				1 means smart LED stay at the state when the flow is stopped.
				2 means turn off the smart LED after the flow is stopped.
			flow_expression: the expression of the state changing series.
		
		Request Example: {"id":1,"method":"start_cf","params":[ 4, 2, "1000, 2, 2700, 100, 500, 1,
		255, 10, 5000, 7, 0,0, 500, 2, 5000, 1"]
		"""