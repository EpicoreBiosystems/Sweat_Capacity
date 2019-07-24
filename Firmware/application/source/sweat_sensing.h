#ifndef SWEAT_SENSING_H__
#define SWEAT_SENSING_H__

#pragma pack (1)

#ifdef __cplusplus
extern "C" {
#endif
  
/* Constant and variable definition for DAC. */
#define PI (3.14159265)
  
typedef struct 
{
    uint8_t     packetNo;
    uint8_t     packetId;
    uint32_t    timeStamp;
    uint8_t     sweatRate;
    uint8_t     sweatChloride;
    uint16_t    sweatRateRaw;
    uint16_t    sweatChlorideRaw;
    uint8_t     bodyTemp;
    uint8_t     battLevel;
    uint8_t     reserved;
    uint8_t     checkSum;        
} SWEAT_REPORT_PACKET_T;
  
void sweat_sensing_init(void);
void sweat_sensing_start(void);
void sweat_sensing_stop(void);


#ifdef __cplusplus
}
#endif

#endif // SWEAT_SENSING_H__