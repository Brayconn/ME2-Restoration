import os, argparse, re
from typing import Tuple, Union, List
from pathlib import Path

class w3d_iterator:
    def __init__(self, w3dPath, encoding="ASCII") -> None:
        self.encoding = encoding
        self.handle = open(w3dPath, 'rb')
        
        magic = self.handle.read(4)
        if magic != bytes('IFX\0', encoding="ASCII"):
            self.handle.close()
            raise ValueError("File has incorrect magic")
        
        self.unk1 = int.from_bytes(self.handle.read(4), 'little')
        self.unk2 = int.from_bytes(self.handle.read(4), 'little')

        self.filesize = int.from_bytes(self.handle.read(4), 'little')
        if self.filesize != os.fstat(self.handle.fileno()).st_size:
            self.handle.close()
            raise ValueError("File size doesn't match")

    def __iter__(self):
        return self
    
    def __read_string(self, max) -> bytes:
        str_len = int.from_bytes(self.handle.read(2), 'little')
        if str_len > max:
            self.handle.close()
            raise ValueError("Invalid string length")
        
        str_data = self.handle.read(str_len)
        if len(str_data) != str_len:
            self.handle.close()
            raise ValueError("Failed to read correct string length")
        
        return str_data

    def __try_get_names(self) -> Union[Tuple[str,str],None]:
        # Entries are aligned to 4 byte offsets for some good reason probably
        diff = self.handle.tell() % 4
        if diff != 0:
            padding = self.handle.read(4 - diff)
            if any(p != 0 for p in padding):
                self.handle.close()
                raise ValueError("Encountered non-zero padding: " + str(padding))
        assert((self.handle.tell() % 4) == 0)
        if self.handle.tell() == self.filesize:
            self.handle.close()
            raise StopIteration
        
        # Entry headers are 8 bytes
        if self.filesize - self.handle.tell() < 8:
            raise ValueError("Not enough bytes to read another entry")
        
        entry_type = self.handle.read(4)
        
        entry_length = int.from_bytes(self.handle.read(4), 'little')
        if entry_length > self.filesize - self.handle.tell():
            self.handle.close()
            raise ValueError("Invalid entry length")
        
        pos = self.handle.tell()
        name = None
        parent = None
        if entry_type == bytes([0x72, 0xFF,0xFF,0xFF]):
            name_data = self.__read_string(entry_length)
            parent_data = self.__read_string(entry_length - 2 - len(name_data))
            self.handle.seek(entry_length - 2 - len(name_data) - 2 - len(parent_data), os.SEEK_CUR)

            name = name_data.decode(self.encoding)
            parent = parent_data.decode(self.encoding)
        self.handle.seek(pos + entry_length)

        if (name != None) and (parent != None):
            return (name, parent)
        else:
            return None

    def __next__(self):
        entry = None
        while entry == None:
            entry = self.__try_get_names()
        return entry

VEHICLES = ['JETSKI','ATV','WHIRLYGIG','JETPACK','DONKEY','GLIDER','BIKE','LUGE']

class zone:
    def __init__(self) -> None:
        self.root = ''
        self.add : List[str] = []
        self.rem : List[str] = []
        self.floors : List[str] = []
        self.vfloors : List[str] = []
        self.vfly : List[str] = []
        self.walls : List[str] = []
        self.walls_nc : List[str] = []
        self.ext : List[str] = []
    
    def add_w3d(self, file:Path):
        for (name,parent) in w3d_iterator(file):
            self.add.append(name)
            if 'FLOORS' in name:
                if any(v in name for v in VEHICLES):
                    self.vfloors.append(name)
                else:
                    self.floors.append(name)
            if 'WALLS' in name:
                if 'NONCAMERA' in name:
                    self.walls_nc.append(name)
                else:
                    self.walls.append(name)

class metadata:
    def __init__(self, src : str) -> None:
        self.src = src
        self.del_ : List[str] = []
        self.lights : List[str] = []
        self.zone_shapes : List[str] = []
        self.zones : List[zone] = []
    
    def add_w3d(self, file:Path):
        for (name,parent) in w3d_iterator(file):
            if 'LIGHTS' in name:
                self.lights.append(name)
            if 'ZONES' in name:
                self.zone_shapes.append(name)

def indent_lines(lines:str, indent:int=4) -> str:
    return '\n'.join(f'{' '*indent}{l}' for l in lines.splitlines())

def render(value:Union[str,List,metadata,zone], indent:int=4) -> str:
    if isinstance(value, str):
        return f'"{value}"'
    elif isinstance(value, List):
        if len(value) == 0:
            return '[]'
        elif len(value) == 1:
            return f'[\n{indent_lines(render(value[0],indent))}\n]'
        else:
            result = '[\n'
            for v in value[:-1]:
                result += f'{indent_lines(render(v,indent))},\n'
            result += f'{indent_lines(render(value[-1],indent))}\n]'
            return result
    elif isinstance(value, metadata):
        result = '[\n'
        result += f'{indent_lines('#src: ' + render(value.src), indent)},\n'
        result += f'{indent_lines('#del: ' + render(value.del_), indent)},\n'
        result += f'{indent_lines('#lights: ' + render(value.lights), indent)},\n'
        result += f'{indent_lines('#zones: ' + render(value.zone_shapes), indent)}'
        if len(value.zones) > 0:
            result += ',\n'
            for i,z in enumerate(value.zones[:-1]):
                result += f'{indent_lines(f'#Z{(i+1):02}: ' + render(z), indent)},\n'
            result += f'{indent_lines(f'#Z{len(value.zones):02}: ' + render(value.zones[-1]), indent)}\n'
        else:
            result += '\n'
        result += ']'
        return result
    elif isinstance(value, zone):
        result = '[\n'
        result += f'{indent_lines('#ROOT: ' + render(value.root))},\n'
        result += f'{indent_lines('#add: ' + render(value.add))},\n'
        result += f'{indent_lines('#rem: ' + render(value.rem))},\n'
        result += f'{indent_lines('#floors: ' + render(value.floors))},\n'
        result += f'{indent_lines('#vfloors: ' + render(value.vfloors))},\n'
        result += f'{indent_lines('#vfly: ' + render(value.vfly))},\n'
        result += f'{indent_lines('#walls: ' + render(value.walls))},\n'
        result += f'{indent_lines('#walls_nc: ' + render(value.walls_nc))},\n'
        result += f'{indent_lines('#ext: ' + render(value.ext))}\n'
        result += ']'
        return result
    else:
        raise ValueError(f'Unknown type: {type(value)}')

FILENAME_RE = re.compile(r'W(\d{2})L(\d{2})(?:(BASE)|(STRUCT)|A(\d{2})Z(\d{2}))')

def main():
    parser = argparse.ArgumentParser('ME2 Map Metadata generator')
    parser.add_argument('source', type=Path, help='The .w3d file to use as the source')
    parser.add_argument('output', type=Path, help='The file to output to')
    parser.add_argument('--extend', type=Path, nargs='+', help='w3d files to add to the extend list')

    args = parser.parse_args()
    output : Path = args.output
    source : Path = args.source
    extend : List[Path] = args.extend if args.extend != None else []

    if not source.is_file():
        print("All inputs must be files")
        return
    if any(not p.is_file() for p in extend):
        print("All extensions must be files")
        return
    
    match = FILENAME_RE.match(source.name)
    if match == None:
        print("Input file has a bad format")
        return
    
    world = match.group(1)
    level = match.group(2)
    
    meta = metadata(source.name)
    meta.add_w3d(source)

    if len(extend) == 0 and (match.group(3) == None or match.group(4) == None):
        tz = zone()
        tz.root = 'scene'
        tz.add_w3d(source)
        meta.zones.append(tz)
    else:
        exp_area = None
        for ext in sorted(extend):
            ext_match = FILENAME_RE.match(ext.name)
            if ext_match == None:
                print('Invalid extension format')
                return
            if ext_match.group(1) != world:
                print('World mismatch')
                return
            if ext_match.group(2) != level:
                print('Level mismatch')
                return
            
            area = ext_match.group(5)
            if area != None:
                if exp_area == None:
                    exp_area = area
                elif exp_area != area:
                    print('Area mismatch')
                    return
                z = ext_match.group(6)

                tz = zone()
                tz.root = 'scene'
                tz.add_w3d(ext)
                tz.ext.append(ext.name)
                meta.zones.append(tz)
            else:
                meta.add_w3d(ext)

    res = render(meta)
    #print(res)
    output.write_text(res)

if __name__ == '__main__':
    main()