# Author: Marco Simoes
# Adapted from Java's implementation of Rui Pedro Paiva
# Teoria da Informacao, LEI, 2022

import sys
from huffmantree import HuffmanTree


class GZIPHeader:
    ''' class for reading and storing GZIP header fields '''

    ID1 = ID2 = CM = FLG = XFL = OS = 0
    MTIME = []
    lenMTIME = 4
    mTime = 0

    # bits 0, 1, 2, 3 and 4, respectively (remaining 3 bits: reserved)
    FLG_FTEXT = FLG_FHCRC = FLG_FEXTRA = FLG_FNAME = FLG_FCOMMENT = 0   
    
    # FLG_FTEXT --> ignored (usually 0)
    # if FLG_FEXTRA == 1
    XLEN, extraField = [], []
    lenXLEN = 2
    
    # if FLG_FNAME == 1
    fName = ''  # ends when a byte with value 0 is read
    
    # if FLG_FCOMMENT == 1
    fComment = ''   # ends when a byte with value 0 is read
        
    # if FLG_HCRC == 1
    HCRC = []
        
        
    
    def read(self, f):
        ''' reads and processes the Huffman header from file. Returns 0 if no error, -1 otherwise '''

        # ID 1 and 2: fixed values
        self.ID1 = f.read(1)[0]  
        if self.ID1 != 0x1f: return -1 # error in the header
            
        self.ID2 = f.read(1)[0]
        if self.ID2 != 0x8b: return -1 # error in the header
        
        # CM - Compression Method: must be the value 8 for deflate
        self.CM = f.read(1)[0]
        if self.CM != 0x08: return -1 # error in the header
                    
        # Flags
        self.FLG = f.read(1)[0]
        
        # MTIME
        self.MTIME = [0]*self.lenMTIME
        self.mTime = 0
        for i in range(self.lenMTIME):
            self.MTIME[i] = f.read(1)[0]
            self.mTime += self.MTIME[i] << (8 * i)                 
                        
        # XFL (not processed...)
        self.XFL = f.read(1)[0]
        
        # OS (not processed...)
        self.OS = f.read(1)[0]
  
        # --- Check Flags
        self.FLG_FTEXT = self.FLG & 0x01
        self.FLG_FHCRC = (self.FLG & 0x02) >> 1
        self.FLG_FEXTRA = (self.FLG & 0x04) >> 2
        self.FLG_FNAME = (self.FLG & 0x08) >> 3
        self.FLG_FCOMMENT = (self.FLG & 0x10) >> 4
                    
        # FLG_EXTRA
        if self.FLG_FEXTRA == 1:
            # read 2 bytes XLEN + XLEN bytes de extra field
            # 1st byte: LSB, 2nd: MSB
            self.XLEN = [0]*self.lenXLEN
            self.XLEN[0] = f.read(1)[0]
            self.XLEN[1] = f.read(1)[0]
            self.xlen = self.XLEN[1] << 8 + self.XLEN[0]
            
            # read extraField and ignore its values
            self.extraField = f.read(self.xlen)
        
        def read_str_until_0(f):
            s = ''
            while True:
                c = f.read(1)[0]
                if c == 0: 
                    return s
                s += chr(c)
        
        # FLG_FNAME
        if self.FLG_FNAME == 1:
            self.fName = read_str_until_0(f)
        
        # FLG_FCOMMENT
        if self.FLG_FCOMMENT == 1:
            self.fComment = read_str_until_0(f)
        
        # FLG_FHCRC (not processed...)
        if self.FLG_FHCRC == 1:
            self.HCRC = f.read(2)
            
        return 0
            



class GZIP:
    ''' class for GZIP decompressing file (if compressed with deflate) '''

    gzh = None
    gzFile = ''
    fileSize = origFileSize = -1
    numBlocks = 0
    f = None
    

    bits_buffer = 0
    available_bits = 0        


    def __init__(self, filename):
        self.gzFile = filename
        self.f = open(filename, 'rb')
        self.f.seek(0,2)
        self.fileSize = self.f.tell()
        self.f.seek(0)

    def readDynamicBlock (self):
        '''Interprets Dinamic Huffman compressed blocks'''
        #readbits é dado 
        HLIT = self.readBits(5)
        HDIST = self.readBits(5)
        HCLEN = self.readBits(4)
  
        return HLIT, HDIST, HCLEN

    def storeCLENLengths(self, HCLEN):
        '''Stores the code lengths for the code lengths alphabet in an array'''
     
        # Ordem de comprimentos em que os bits são lidos
        idxCLENcodeLens = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
        CLENcodeLens = [0 for i in range(19)]

        # CLENcodeLens[idx] = N traduz para: "o código para idx, no alfabeto de comprimentos de código, tem um comprimento de N"
        # se N == 0, o comprimento do código desse índice não é usado
        for i in range(0, HCLEN+4):
            temp = self.readBits(3)
            CLENcodeLens[idxCLENcodeLens[i]] = temp
        return CLENcodeLens

    def createHuffmanFromLens(self, lenArray, verbose=False):
        '''Takes an array with symbols' Huffman codes' lengths and returns
        a formated Huffman tree with said codes
        If verbose==True, it prints the codes as they're added to the tree'''
  
        htr = HuffmanTree()
        # max_len é o codigo com o maior tamanho
        max_len = max(lenArray)
        # max_symbol é o maior símbolo a codificar, necessário para determinar o intervalo de comprimentos para a criação de códigos Huffman.
        max_symbol = len(lenArray)
        
        bl_count = [0 for i in range(max_len+1)]
        # Obter array com numero de codigos com comprimento N (bl_count)
        for N in range(1, max_len+1):
            bl_count[N] += lenArray.count(N)

        # obter o primeiro codigo de cada comprimento#
        #code usado para gerar os codigos de huffman
        code = 0
        #next code guarda o codigo seguinte para o comprimento N
        next_code = [0 for i in range(max_len+1)]
        #Gera o próximo código Huffman para cada comprimento.Usa a contagem de códigos com o comprimento anterior para determinar o ponto inicial do comprimento atual.
        codes_list = []        
        for bits in range(1, max_len+1):
            #<< move os bits para a esquerda, garantindo que os codigoes estao separados por pelo menos um bit 
            code = (code + bl_count[bits-1]) << 1
            next_code[bits] = code
  
        # Define codigos para cada simbolo em ordem lexicográfica 
        for n in range(max_symbol):
            # Tamanho associado ao simbolo n 
            length = lenArray[n]
            #se nao for zero
            if(length != 0):
                #[2:] remove o prefixo "0b"
                code = bin(next_code[length])[2:]
                # No caso de haver 0 no inicio do codigo bin,temos de os adicionar manualmente
                # length-len(code) 0s têm se ser adicionados (int nao os adiciona)
                #Calcula o número de zeros a serem adicionados ao início da representação binária para torná-la o comprimento correto
                extension = "0"*(length-len(code)) 
                huffman_code = extension + code
                codes_list.append((n, huffman_code))
                #Adiciona um nó à árvore Huffman com o código Huffman gerado, o índice de símbolos e imprime o código se verbose for True.
                htr.addNode(extension+code, n, verbose=True)                #incrementa o próximo código para o comprimento atual, preparando-o para a próxima iteração.
                next_code[length] += 1

        print(f"lista de (símbolos, codigos): {codes_list}")
        return htr;

    def storeTreeCodeLens(self, size, CLENTree):
        '''Takes the code lengths huffmantree and stores the code lengths accordingly'''

        # Array onde o comprimento dos codigos ira ser guaradado 
        treeCodeLens = [] 
        prevCode=-1
  
        while (len(treeCodeLens) < size):
            # mete o nó atual na raiz da arvore de huffman
            CLENTree.resetCurNode()
            found = False
   
            # Durante a leitura, se uma folha não foi encontrada, continue procurando bit a bit
            while(not found):
                curBit = self.readBits(1)
                # atualiza o nó atual de acordo com o bit lido
                code = CLENTree.nextNode(str(curBit))
                if(code != -1 and code != -2):
                    # se foi encontrada uma foha, dar break do loop
                    found = True

            # SPECIAL CHARACTERS
            # 18 - lê 7 bits extra
            # 17 - lê 3 bits extra
            # 16 - lê 2 bits extra
            if(code == 18):
                ammount = self.readBits(7)
                # De acordo com os 7 bits que acabamos de ler, define os valores 11-139 seguintes no array de comprimento como 0
                treeCodeLens += [0]*(11 + ammount)
            if(code == 17):
                ammount = self.readBits(3)
                # De acordo com os 3 bits que acabamos de ler, define os valores 3-11 seguintes no array de comprimento como 0 
                treeCodeLens += [0]*(3 + ammount)
            if(code == 16):
                ammount = self.readBits(2)
                # De acordo com os 2 bits que acabamos de ler, define os valores 3-6 seguintes no array de comprimento como o comprimento lido anteriormente
                treeCodeLens += [prevCode]*(3 + ammount)
            elif(code >= 0 and code <= 15):
                # Se um caractere especial não for encontrado, basta definir o próximo comprimento do código para o valor encontrado
                treeCodeLens += [code]
                # defenir o prevCode para o código atual caso o caractere especial 16 seja encontrado na próxima iteração
                prevCode = code

        return treeCodeLens

    def decompressLZ77(self, HuffmanTreeLITLEN, HuffmanTreeDIST, output):
     
        #Quantos bits são necessários ler se o comprimento da leitura do código for maior que 265
        ExtraLITLENBits = [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5,0]
        
        #Comprimento necessário adicionar se o código de comprimento lido for maior que 265
        ExtraLITLENLens = [11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227,258]
        
        #Quantos bits necessários ler se o código de distância lido for maior que 4
        ExtraDISTBits = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13]        
        
        #Distância necessária adicionar se o caractere especial lido for maior que 4
        ExtraDISTLens = [5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577]


        codeLITLEN = -1


        # le da stream do input ate 256 ser encontrado
        while(codeLITLEN != 256):
            # Dá reset ao nó atual para a base da arvore
            HuffmanTreeLITLEN.resetCurNode()

            foundLITLEN = False
            distFound = True

            # enquanto um literal ou comprimento não seja encontrado na árvore LITLEN, continua a pesquisar bit a bit

            while(not foundLITLEN):
                curBit = str(self.readBits(1))
                #Dá update ao nó atual de acordo ao bit lido
                codeLITLEN = HuffmanTreeLITLEN.nextNode(curBit)
    
                #Caso seja atingida uma folha na árvore LITLEN, segue as instruções de acordo com o valor encontrado
                if (codeLITLEN != -1 and codeLITLEN != -2):
                    foundLITLEN = True
     
                    # Se o código atingido estiver no intervalo [0, 256[, apenas adiciona o valor lido correspondente a um literal ao array de saída
                    if(codeLITLEN < 256):
                        output += [codeLITLEN]

                    # Se o código estiver no intervalo [257, 285], refere-se ao comprimento da string a ser copiada
                    if(codeLITLEN > 256):
         
                        distFound = False
      
                        # Se o código estiver no intervalo [257, 265[, define o comprimento da string a ser copiada como o código lido - 257 + 3
                        if(codeLITLEN < 265):
                            length = codeLITLEN - 257 + 3
                           
                        # Os códigos no intervalo [265, 285] são especiais e requerem mais bits para serem lidos
                        else:
                            # dif define os índices nos "Arrays Extras" a serem usados 
                            dif = codeLITLEN - 265
                            # Quantos bits extras precisarão ser lidos
                            readExtra = ExtraLITLENBits[dif]
                            # Quanto comprimento extra adicionar
                            lenExtra = ExtraLITLENLens[dif]
                            length = lenExtra + self.readBits(readExtra)

                        # Reseta o nó atual na árvore de distâncias para sua raiz
                        HuffmanTreeDIST.resetCurNode()
                        #Enquanto uma distância não for encontrada na árvore DIST, continue procurando bit a bit
                        while(not distFound):
                            distBit = str(self.readBits(1))
                            # Atualiza o nó atual de acordo com o bit acabado de ler
                            codeDIST = HuffmanTreeDIST.nextNode(distBit)

                            # Se uma folha for atingida na árvore LITLEN, siga as instruções de acordo com o valor encontrado
                            if(codeDIST != -1 and codeDIST != -2):
                                distFound = True

                                # Se o código lido estiver no intervalo [0, 4[, define a distância para retroceder como o código lido + 1
                                if(codeDIST < 4):
                                    distance = codeDIST + 1

                                # dif define os índices nos "Arrays Extras" a serem usados
                                else:
                                    # dif define os índices nos "Arrays Extras" a serem usados
                                    dif = codeDIST - 4
                                    readExtra = ExtraDISTBits[dif]
                                    # Quantos bits extras precisam ser lidos
                                    distExtra = ExtraDISTLens[dif]
                                    # Quanto distância extra adicionar
                                    distance = distExtra + self.readBits(readExtra)
                                
                                # Para cada uma das iterações no intervalo(length), copie o caractere no índice len(output)-distance para o final do array de saída
                                for i in range(length):
                                    output.append(output[-distance])
                                    
                                    
        return output
 
    def decompress(self):
        ''' main function for decompressing the gzip file with deflate algorithm '''
        
        numBlocks = 0

        # get original file size: size of file before compression
        origFileSize = self.getOrigFileSize()
        print(origFileSize)
        
        # read GZIP header
        error = self.getHeader()
        if error != 0:
            print('Formato invalido!')
            return
        
        # show filename read from GZIP header
        print(self.gzh.fName)
        
        
        # MAIN LOOP - decode block by block
        BFINAL = 0    
        # Opens the output file in "write binary mode"
        f = open(self.gzh.fName, 'wb')
        output = []
        while not BFINAL == 1:    
      
            BFINAL = self.readBits(1)
            
            BTYPE = self.readBits(2)                    
            if BTYPE != 2:
                print('Error: Block %d not coded with Huffman Dynamic coding' % (numBlocks+1))
                return
            
            # if BTYPE == 10 in base 2 -> read the dinamic Huffman compression format 
            if BTYPE == int('10', 2):        
                # HLIT: # of literal/length  codes
                # HDIST: # of distance codes 
                # HCLEN: # of code length codes
                
                #ex1 (semana1)
                HLIT, HDIST, HCLEN = self.readDynamicBlock()
                print("exercício 1 :", HLIT + 257, "Códigos Literais/Comprimento", HDIST + 1, "Códigos de Distância", HCLEN + 4, "Códigos de Comprimentos de Código")
                #ex2 (semana1)
                # Armazena os comprimentos de código da árvore CLEN em uma ordem predefinida
                CLENcodeLens = self.storeCLENLengths(HCLEN)
                print("exercício 2 - Os comprimentos do CLEN são:", CLENcodeLens)
                #print("Comprimentos de códigos dos índices i da árvore de comprimentos de código:", CLENcodeLens)
                #ex3 (semana2)
                # Com base nos comprimentos de código da árvore CLEN, define uma árvore Huffman para CLEN
                print("exercício 3 : HuffmanTreeCLENs")      
                HuffmanTreeCLENs = self.createHuffmanFromLens(CLENcodeLens, verbose=False)
                #ex4 (semana3)
                # Armazena os comprimentos de código da árvore literal e de comprimento com base nos códigos da árvore CLEN
                LITLENcodeLens = self.storeTreeCodeLens(HLIT + 257, HuffmanTreeCLENs)
                print("exercício 4 LEN:", LITLENcodeLens)                
                #ex5 (semana 4)
                # Armazena os comprimentos de código da árvore de distância com base nos códigos da árvore CLEN
                DISTcodeLens = self.storeTreeCodeLens(HDIST + 1, HuffmanTreeCLENs)
                print("exercício 5 LEN:", DISTcodeLens)            
                #ex6 (semana5)
                # Define a árvore Huffman literal e de comprimento com base nos comprimentos de seus códigos
                print("exercício 6 : HuffmanTreeLITLEN")                
                HuffmanTreeLITLEN = self.createHuffmanFromLens(LITLENcodeLens, verbose=False)
                # Define a árvore Huffman de distância com base nos comprimentos de seus códigos
                print("exercício 6 : HuffmanTreeDIST")    
                HuffmanTreeDIST = self.createHuffmanFromLens(DISTcodeLens, verbose=False)
                #ex7 (semana 5)
                # Com base nas árvores definidas até agora, descomprime os dados de acordo com o algoritmo Lempel-Ziv77 
                output = self.decompressLZ77(HuffmanTreeLITLEN, HuffmanTreeDIST, output)
                print("exercício 7 :", output)
                
            
            if(len(output) > 32768):
                # Escreve cada caractere que excede a faixa de 32768 no arquivo
                f.write(bytes(output[0 : len(output) - 32768]))
                # Mantém o restante no array de saída
                output = output[len(output) - 32768 :]
                
            # Atualiza o número de blocos lidos
            numBlocks += 1
            
        #ex8 (semana5)
        
        # Escreve os bytes correspondentes aos elementos do array de saída
        f.write(bytes(output))
        # Fecha o arquivo
        f.close        


        self.f.close()    
        print("End: %d block(s) analyzed." % numBlocks)
    
    
    def getOrigFileSize(self):
        ''' reads file size of original file (before compression) - ISIZE '''
        
        # saves current position of file pointer
        fp = self.f.tell()
        
        # jumps to end-4 position
        self.f.seek(self.fileSize-4)
        
        # reads the last 4 bytes (LITTLE ENDIAN)
        sz = 0
        for i in range(4): 
            sz += self.f.read(1)[0] << (8*i)
        
        # restores file pointer to its original position
        self.f.seek(fp)
        
        return sz        
    

    
    def getHeader(self):  
        ''' reads GZIP header'''

        self.gzh = GZIPHeader()
        header_error = self.gzh.read(self.f)
        return header_error
        

    def readBits(self, n, keep=False):
        ''' reads n bits from bits_buffer. if keep = True, leaves bits in the buffer for future accesses '''

        while n > self.available_bits:
            self.bits_buffer = self.f.read(1)[0] << self.available_bits | self.bits_buffer
            self.available_bits += 8
        
        mask = (2**n)-1
        value = self.bits_buffer & mask

        if not keep:
            self.bits_buffer >>= n
            self.available_bits -= n

        return value

    

if __name__ == '__main__':

    # gets filename from command line if provided
    fileName = "FAQ.txt.gz"
    if len(sys.argv) > 1:
        fileName = sys.argv[1]            

    # decompress file
    gz = GZIP(fileName)
    gz.decompress()