#ifndef SWEAT_SENSING_H__
#define SWEAT_SENSING_H__

#ifdef __cplusplus
extern "C" {
#endif

#pragma pack (1)
    
/* FDC1004 sensor measure definitions. */
//Constants and limits for FDC1004
#define FDC1004_100HZ (1)
#define FDC1004_200HZ (2)
#define FDC1004_400HZ (3)
#define FDC1004_IS_RATE(x) (x == FDC1004_100HZ || \
                            x == FDC1004_200HZ || \
                            x == FDC1004_400HZ)

#define FDC1004_RATE_DEFAULT    (FDC1004_100HZ)
#define FDC1004_CAPDAC_MAX (0x1F)

#define FDC1004_CHANNEL_MAX      (1)    /* Limit the measurement channel to 0 & 1. */    
#define FDC1004_IS_CHANNEL(x) (x <= FDC1004_CHANNEL_MAX)

#define FDC1004_NUM_MEASUREMENTS (2)    /* Limit the measurements to two for two channels. */
#define FDC1004_MEAS_MAX         (1)
#define FDC1004_IS_MEAS(x) (x <= FDC1004_MEAS_MAX)

#define FDC_REGISTER (0x0C)

#define MEAS_INTERVAL_DEFAULT_IN_SECS   (10)
#define MEAS_INTERVAL_MIN_IN_SECS       (10)
#define MEAS_INTERVAL_MAX_IN_SECS       (60)

typedef enum
{
    CMD_SUCCESS = 0x0,
    CMD_INVALID_LEN = 0x1,
    CMD_INVALID_CHECKSUM = 0x2,
    CMD_INVALID_CMD = 0x3,
    CMD_INVALID_PARAMS = 0x4,

} EPICORE_BLE_CMD_ERRCODE_T;
    
typedef struct
{
    uint8_t packet_num;
    uint8_t packet_id;           // CMD_ACK_MSG
    uint8_t cmd;                // cmd ID acknowledged
    uint8_t err_code;    
    uint8_t check_sum;
} CMD_ACK_MSG_T;    

typedef enum 
{
    CMD_CONFIG_SENSOR = 0x41,
    CMD_START_DATA_STREAM = 0x42,
    CMD_STOP_DATA_STREAM = 0x43,
    CMD_SET_TIME = 0x44,
    CMD_GET_TIME = 0x45,
    
    CMD_GET_FW_INFO = 0X58,
    CMD_RESET_SYSTEM = 0x59,
    CMD_SHUT_DOWN = 0x5A,
        
} EPICORE_BLE_CMD_T;

typedef enum 
{
    MSG_CMD_ACK = 0x0,
    MSG_DATA_STREAM = 0x62,
    MSG_SYS_TIME = 0x65,
    MSG_FW_INFO = 0x78,
    
} EPICORE_BLE_MST_T;

typedef enum 
{
    SWEAT_CAPACITY_TYPE = 0,
    NUM_DATA_TYPES
} EPICORE_DATA_TYPE_T;

typedef __packed struct 
{
    uint8_t     packetNo;
    uint8_t     packetId;
    uint32_t    timeStamp;
    uint8_t     dataType;
    uint8_t     dataLen;
    uint32_t    sweat_capacity_data[2];
    uint8_t     checkSum;        
} SWEAT_DATA_REPORT_PACKET_T;

/********************************************************************************************************
 * Capacity sensor measurement typedefs
 *******************************************************************************************************/
typedef struct {
    uint8_t enable;
    uint8_t channel;
    uint8_t capdac;
    int8_t cap_offset_calib;
} measurement_cfg_t;

typedef struct 
{
    uint8_t rate;
//    uint8_t measurement_report_interval;
    measurement_cfg_t measurements[FDC1004_NUM_MEASUREMENTS]; 
} fdc1004_measurement_cfg_t;

uint8_t sweat_capacity_sensing_init(void);
uint8_t sweat_capacity_sensing_cfg(fdc1004_measurement_cfg_t *new_meas_cfg);
uint8_t sweat_capacity_sensing(uint32_t * value);

#ifdef __cplusplus
}
#endif

#endif // SWEAT_SENSING_H__