def join(strs: list, sep:str=";") -> str:
    result = ""
    for s in strs:
        result += str(len(s))+sep+s
    return result

def joinBytes(bytesList: list, sep: bytes=b";") -> bytes:
    result = b''
    for bt in bytesList:
        result += str(len(bt)).encode()+sep+bt
    return result

def dejoinBytes(bytestr: bytes, sep: bytes=b';') -> list:
    result = []
    while len(bytestr) > 0:
        try:
            index = bytestr.find(sep)
            num = int(bytestr[:index])
            result.append(bytestr[index+1:index+1+num])
            bytestr = bytestr[index+1+num:]
        except Exception as e:
            raise Exception("error happend when dejoin, errinfo: {}".format(e))
    return result

def dejoin(string: str, sep:str=";") -> list:
    result = []
    while len(string) > 0:
        try:
            index = string.find(sep)
            num = int(string[:index])
            result.append(string[index+1:index+1+num])
            string = string[index+1+num:]
        except Exception as e:
            raise Exception("error happend when dejoin, errinfo: {}".format(e))
    return result

if __name__=="__main__":
    a = ["a", ";b", "ccde;"]
    s = join(a)
    print("join: {}".format(s))
    b = dejoin(s)
    print("dejoin: {}".format(b))
