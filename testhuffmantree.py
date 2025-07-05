from huffmantree import HuffmanTree


hft = HuffmanTree()

verbose = True

# insert new code
code = "000"		
erro = hft.addNode(code, 0, verbose)

# insert code already present
code = "000"
erro = hft.addNode(code, 1, verbose)

# try add child to leaf
code = "00001"
erro = hft.addNode(code, 1, verbose)


# insert new code
code = "11100"
erro = hft.addNode(code, 3, verbose)

# insert code already present
code = "11100"
erro = hft.addNode(code, 3, verbose)

# try add child to leaf
code = "111001"
erro = hft.addNode(code, 3, verbose)


# ------------------- Search

code = "000"
pos = hft.findNode(code, None, verbose)

code = "11100"
pos = hft.findNode(code, None, verbose)

code = "111"
pos = hft.findNode(code, None, verbose)


# search code bit by bit
def search_bit_by_bit(buffer, verbose=False):

	lv = 0
	l = len(buffer)
	terminate = False
	code = ""


	while not terminate and lv < l:
		
		nextBit = buffer[lv]
		code = code + nextBit
		
		pos = hft.nextNode(nextBit)
					
		if pos != -2:
			terminate = True
		else:
			lv = lv + 1

	if verbose:
		if pos == -1:
			print("Code '" + buffer + "' not found!!!")
		elif pos == -2:
			print("Code '" + buffer + "': not found but prefix!!!")
		else:
			print("Code '" + buffer + "' found, alphabet position: " + str(pos) )

	return pos	



code = "111000100"
pos = search_bit_by_bit(code, True)


code = "1110"
pos = search_bit_by_bit(code, True)
