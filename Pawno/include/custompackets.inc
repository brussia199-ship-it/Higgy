#define CUSTOM_PACKET_VERSION	0x4

const CUSTOM_PACKET_SYSTEM = 242; // для кастомной системы пакетов
#define CUSTOM_PACKET_DRIFT_STATUS   1   // internal IDs

forward OnPlayerDriftStatusChanged(playerid, status);

IPacket:CUSTOM_PACKET_SYSTEM(playerid, BitStream:bs)
{
	BS_IgnoreBits(bs, 8);
	new packetid;
	BS_ReadInt8(bs, packetid);
	
	switch(packetid)
	{
		case CUSTOM_PACKET_DRIFT_STATUS: // иды пакетов
		{
			new status;
			BS_ReadUint8(bs, status);
			OnPlayerDriftStatusChanged(playerid, status);
			return 0;
		}
	}

	return 0;

}