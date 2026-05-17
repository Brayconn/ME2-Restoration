#pragma description Adobe Shockwave W3D Model files

import std.io;
import std.mem;

struct String {
    u16 length;
    char data[length];
};

struct Entry {
    std::mem::AlignTo<4>;
    u32 type;
    u32 length;
    u32 start = $;
    if(type == 0xFFFFFF72)
    {
        String name;
        String parentName;
        //std::print("\"{}\", //{}", name.data, parentName.data);
        std::print("{} --> {}", parentName.data, name.data);
    }
    u32 read = $ - start;
    u32 remaining = length - read;
    if(remaining > 0)
    {
        u8 data[remaining] [[sealed]];
    }
};

struct W3D {
    char signature[3];
    u8 pad;
    u32 unk1;
    u32 unk2;
    u32 fileSize;
    Entry entries[while((fileSize - $) >= 4)];
    //Entry entries[4];
};

W3D w3d @ 0x0;
//Entry e @ 0x10;