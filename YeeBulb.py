import socket
import re

#Bulb class
class YeeBulb:
	""" 
	All functions return a tuple: result_tup(x, y)
	x - True|False depending whether the function executed successfully
	y - List of requested params|"ok"|error message
	"""
	DISPLAY_MSG = True	#Turn on/off debugging messages
	def __init__(self, bulb_id, bulb_ip, bulb_port, model, power, bright, rgb, methods):
		self.id = bulb_id
		self.ip = bulb_ip
		self.port = bulb_port
		self.model = model
		self.power = power
		self.bright = bright
		#self.color_mode = color_mode
		#self.ct = ct
		self.rgb = rgb
		#self.hue = hue
		#self.sat = sat
		#self.name = name
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
		param_re = re.compile(param)
		match = param_re.search(data)
		value = ""
		if match != None:
			value = match.group(1)
			return value

	@staticmethod
	def handle_result_message(method, params, data): #TODO merge this into self.operate()?
		"""
		Method to handle the bulb's response to operation request.
		"""
		if '"error"' in data:
			respose = (False, YeeBulb.get_val(data, '"message":(.*)\}\}'))
		elif method == "get_prop":
			response = (True, (YeeBulb.get_val(data, '"result":\[([ -~]*)\]\}')).split(',') )
		elif '"ok"' in data:
			response = (True, "ok")
		else:
			response = (False, "Unknown error.\n Received data:\n" + data)
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

				YeeBulb.display("Handling response")
				DataBytes = tcp_socket.recv(2048)
				data = DataBytes.decode()#Decode bytes->str
				result = YeeBulb.handle_result_message(method, params, data)
				tcp_socket.close()
				return result
			except Exception as e:
				YeeBulb.display("Unexpected error:" + e)
				return (False, e)

	def get_state(self, req_params):
		"""	Method to retrieve current state of specified bulb parameters	"""
		params = ""
		for i in range(0, len(req_params)):
			params += "\"" + req_params[i] + "\""
			if i != len(req_params) - 1:
				params +=","
		return self.operate("get_prop", params)

	def bulb_update():
		""" Method to update bulb status """
		params = ["power", "bright", "rgb"] #TODO include all parameters
		result = self.operate("get_prop", params)
		if result[0]:
			states = result[1]
			self.power = states[0]
			self.bright = states[1]
			self.rgb = states[2]

	def set_ct(self, ct_value, effect = "sudden", duration = 30):
		"""
		Method to change the color temperature of the bulb
		ct_value - targeted color temperature (1700 <= ct_value <= 6500 (k))
		effect - sudden/smooth
		duration - total time of gradual change if smooth mode is selected (duration > 30 (ms))
		"""	
		if 1700 <= int(ct_value) <= 6500 and int(duration) >= 30:
			params = str(ct_value) +",\"" + str(effect) + "\"," + str(duration)
			return self.operate("set_ct_abx", params)
		else:
			return (False, "Parameters out of range")

	def set_rgb(self, rgb_value, effect = "sudden", duration = 30):
		"""
		Metod to change the color of the bulb
		rgb_value - the target color (decimal int;  0 <= rgb_value <= 16777215)
		"""
		if 0 <= int(rgb_value) <= 16777215 and int(duration) >= 30:
			params = str(rgb_value) +",\"" + str(effect) + "\"," + str(duration)
			return self.operate("set_rgb", params)
		else:
			return (False, "Parameters out of range")

	def set_hue(self, hue, sat = 0, effect = "sudden", duration = 30):
		"""
		hue - target hue value (decimal int; 0 <= hue <= 359) 
		sat - target saturation value (int; 0 <= sat <= 100)
		"""
		if 0 <= int(hue) <= 359 and 0 <= int(sat) <= 100 and int(duration) >= 30:
			params = str(hue) + "," + str(sat) +",\"" + str(effect) + "\"," + str(duration)
			return self.operate("set_hsv", params)
		else:
			return (False, "Parameters out of range")

	def set_bright(self, bright, effect = "sudden", duration = 30):
		"""
		Method to set the brightness of the bulb
		bright - target brightness (1 <= bright <= 100)
		"""
		if (1 <= int(bright) <= 100) and (int(duration) >= 30):
			params = str(bright) + ",\"" + str(effect) + "\"," + str(duration)
			return self.operate("set_bright", params)
		else:
			return (False, "Parameters out of range")
	
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

	#NOT TESTED
	def set_default(self):
		"""Sets current bulb state as default. """
		self.operate("set_default", "")

	def start_cf(self, count, action, *flow_expressions):
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
			flow_expression: the expression of the state changing series. [duration, mode, value, brightness]
				duration: Gradual change time or sleep time in milliseconds, minimum value 50.
				mode: 1 – color, 2 – color temperature, 7 -- sleep.
				value: RGB value when mode is 1, CT value when mode is 2, ignored when mode is 7.
				brightness: Brightness value, 1 ~ 100. Ignored when mode is 7.
		Request Example: 
		{"id":1,"method":"start_cf","params":[ 4, 2, "1000, 2, 2700, 100, 500, 1,255, 10, 5000, 7, 0,0, 500, 2, 5000, 1"]
		"""
		#TODO check if "flow_expressions" corelate with "count"
		params = str(count) +"," + str(action)
		for expression in flow_expressions
			params += ',' + expression
		return self.operate("start_cf" )
	
	def stop_cf(self)
	""" Method to stop the color flow """
		return self.operate("stop_cf", "")
	
	def set_scene(self, class_type, *args)
	 """
	 This method is used to set the smart LED directly to specified state.
	 If the smart LED is off, then it will turn on the smart LED firstly and then apply the specified command
	 
	Args:
		class_type: "color", "hsv", "ct", "cf", "auto_dealy_off".
			"color": change the smart LED to specified color and brightness.
			"hsv": change the smart LED to specified color and brightness.
			"ct": change the smart LED to specified ct and brightness.
			"cf": start a color flow in specified fashion.
			"auto_delay_off": turn on the smart LED to specified brightness and start a sleep timer to turn off the light after the specified time
		args: class specific.
	 """
	 #TODO check if arg is in range for specific class_type
	 class_list =["color", "hsv", "ct", "cf", "auto_delay_off"]
	 if class_type in class_list:
		 params = str(class_type)
		 for arg in args:
			 param += str(arg) + ','
		return self.operate("set_scene", params)
	else:
		return (False, "Parameters out of range")
	
	def cron_add(self, value, mode = 0)
		"""
		This method is used to start a timer job on the smart LED.
		Args:	
			value: is the length of the timer (in minutes).
			mode: currently can only be 0. (means power off)
		"""
		params = str(mode) + ',' +str(value)
		return self.operate("cron_add", params)

	def cron_get(self, mode = 0)
	"""
	This method is used to retrieve the setting of the current cron job of the specified type. 
	Args:
		mode: type of the cron job. (currently only support 0).
	"""
	return self.operate("cron_get", str(mode))

	def cron_del(self, mode)
	"""
	This method is used to stop the specified cron job.
	Args:
		mode: the type of the cron job. (currently only support 0).
	"""
	return self.operate("cron_del", str(mode))

	def set_adjust(self, prop, action = "circle")
	"""
	This method is used to change brightness, CT or color of a smart LED without knowing the current value.
	Args:
		action: direction of the adjustment. The valid values:
			“increase": increase the specified property
			“decrease": decrease the specified property
			“circle": increase the specified property, after it reaches the max value, go back to minimum value.
		prop: property to adjust. The valid values:
			“bright": adjust brightness.
			“ct": adjust color temperature.
			“color": adjust color. (When “prop" is “color", the “action" can only be “circle", otherwise, it will be deemed as invalid request.)
	"""
	params = action + ',' + prop
	return self.operate("set_adjust", params)

	def set_music(self, action, host, port)
	"""
	This method is used to start or stop music mode on a device. Under music mode, no property will be reported and no message quota is checked.
	Args:
		action: action of set_music command. The valid values:
			0: turn off music mode.
			1: turn on music mode.
		host: IP address of the music server.
		port: TCP port music application is listening on.

	Note:
		When control device wants to start music mode, it needs start a TCP 
		server firstly and then call “set_music” command to let the device know the IP and Port of the
		TCP listen socket. After the command is received, LED device will try to connect the specified
		peer address. If the TCP connection is established successfully, then control device can
		send all supported commands through this channel without any limits to simulate any music effect.
		The control device can stop music mode by explicitly sending a stop command or by closing the socket.
	"""
	pass

	def set_name(self, name)
	"""
	This method is used to name the device. The name will be stored on the device and reported in discovering response.
	User can also read the name through “get_prop” method.
	Args:
		name: new name of the bulb
	"""
	return self.operate("set_name", str(name))