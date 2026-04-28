#define PC_ANIMFIX_VERSION	0x1

static RPC_Animation = 86;

enum ENUM_DANCE_INFO
{
  DANCE_NAME[64],
  DANCE_SCORE,
  DANCE_LIBS[64],
  DANCE_NAMES[64],
  DANCE_STPRICE
}

static g_DanceList[12][ENUM_DANCE_INFO] =
{
  {"FLOSS",       500,   "CDANCESTA",   "DANCE_G1",    100},
  {"HYPE",       500,   "CDANCESTA",   "DANCE_G2",    250},
  {"OrangeJuictie",   500,   "CDANCESTA",   "DANCE_G3",    300},
  {"GROOVE JAM",     500,   "CDANCESTA",   "DANCE_G4",    350},
  {"Electro Shuffle", 500,   "CDANCESTA",   "DANCE_G5",    400},
  {"ELECTRO SWING",   500,   "CDANCESTA",   "DANCE_G6",    450},
  {"SIDE HUSTLE",   500,   "CDANCESTA",   "DANCE_G7",    500},
  {"BREAKNECK",     500,   "CDANCESTA",   "DANCE_G8",    550},
  {"Bold stance",   500,   "CDANCESTA",   "DANCE_G9",    600},
  {"DANCE OFF",     500,   "CDANCESTA",   "DANCE_G10",  750},
  {"DREAM FEET",     500,   "CDANCESTA",   "DANCE_G11",  800},
  {"POKI",       500,   "CDANCESTA",   "DANCE_G12",  1_000}
};

ORPC:RPC_Animation(playerid, BitStream:bs)
{
	if(isPlayerAndroid(playerid))
	{
		return 1;
	}

	new pedplayerid;
	new szLibName[255];
	new szAnimName[255];
	
	new libNameLength;
	new animNameLength;
	
	BS_ReadUint16(bs, pedplayerid);
	BS_ReadUint8(bs, libNameLength);
	
	if(libNameLength >= 255)
	{
		return 0;
	}
	BS_ReadString(bs, szLibName, libNameLength);
	
	BS_ReadUint8(bs, animNameLength);
	if(animNameLength >= 255)
	{
		return 0;
	}
	
	BS_ReadString(bs, szAnimName, animNameLength);
	
	for(new i = 0; i < sizeof(g_DanceList); i++)
	{
		if(!strcmp(g_DanceList[i][DANCE_NAMES], szAnimName))
		{
			return 0;
		}
	}
	
	return 1;
}