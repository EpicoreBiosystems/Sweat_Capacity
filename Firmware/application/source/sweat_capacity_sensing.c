
#include <stdbool.h>
#include "nrf.h"
#include "nrf_gpio.h"
#include "boards.h"
#include "nrf_drv_timer.h"
#include "app_error.h"
#include "app_util_platform.h"
#include "nrf_drv_twi.h"
#include "nrf_drv_saadc.h"
#include "nrf_delay.h"
#include "nrf_log.h"
#include "nrf_log_ctrl.h"
#include "boards.h"
#include "sweat_capacity_sensing.h"

/* TWI instance ID. */
#define TWI_INSTANCE_ID     0

#define FDC1004_I2C_ADDR        (0x50) //   (0xA0U >> 1)

#define FDC1004_I2C_SCL_PIN     20
#define FDC1004_I2C_SDA_PIN     18

static fdc1004_measurement_cfg_t measurement_cfgs;
static uint8_t measDelay;

/* Indicates if operation on TWI has ended. */
static volatile bool m_xfer_done = false;

/* TWI instance. */
static const nrf_drv_twi_t m_twi = NRF_DRV_TWI_INSTANCE(TWI_INSTANCE_ID);

/* FDC1004 sensor register definitions. */
uint8_t MEAS_CONFIG[] = {0x08, 0x09, 0x0A, 0x0B};
uint8_t CAP_OFFSET_CALIB_CONFIG[] = {0x0D, 0x0E, 0x0F, 0x10};
uint8_t MEAS_MSB[] = {0x00, 0x02, 0x04, 0x06};
uint8_t MEAS_LSB[] = {0x01, 0x03, 0x05, 0x07};
uint8_t SAMPLE_DELAY[] = {11,11,6,3};

static void fdc1004_write16(uint8_t reg, uint16_t data)
{
    uint8_t tx_data[3];
    
    tx_data[0] = reg;
    tx_data[1] = (uint8_t)(data >> 8);
    tx_data[2] = (uint8_t) data;
    
    m_xfer_done = false;
    ret_code_t err_code = nrf_drv_twi_tx(&m_twi, FDC1004_I2C_ADDR, tx_data, sizeof(tx_data), false);
    APP_ERROR_CHECK(err_code);
    while (m_xfer_done == false);
    
}

static uint16_t fdc1004_read16(uint8_t reg)
{
    /* Read 2 bytes from the specified address, two I2C transactions, set register address first, then read register value */
    m_xfer_done = false;

    uint8_t tx_data = reg;
    ret_code_t err_code = nrf_drv_twi_tx(&m_twi, FDC1004_I2C_ADDR, &tx_data, sizeof(tx_data), false);
    APP_ERROR_CHECK(err_code);
    while (m_xfer_done == false);
    
    m_xfer_done = false;
    
    uint8_t reg_bytes[2];    
    err_code = nrf_drv_twi_rx(&m_twi, FDC1004_I2C_ADDR, reg_bytes, sizeof(reg_bytes));
    APP_ERROR_CHECK(err_code);
    while (m_xfer_done == false);
    
    uint16_t reg_value = (((uint16_t)(reg_bytes[0])) << 8) + reg_bytes[1]; 
    return reg_value;
}

//configure a measurement
static uint8_t fdc1004_configureMeasurementSingle(uint8_t measurement, uint8_t channel, uint8_t capdac, int8_t cap_offset_calib)
{
    /* Verify data */
    if (!FDC1004_IS_MEAS(measurement) || !FDC1004_IS_CHANNEL(channel) || capdac > FDC1004_CAPDAC_MAX) {
        return 1;
    }

    /* build 16 bit configuration */
    uint16_t configuration_data;
    configuration_data = ((uint16_t)channel) << 13;     // CHA
    configuration_data |= ((uint16_t)0x04) << 10;       // CHB disable / CAPDAC enable
    configuration_data |= ((uint16_t)capdac) << 5;      // CAPDAC value
    fdc1004_write16(MEAS_CONFIG[measurement], configuration_data);
    
    /* Configure capacitance offset calibration to fine-tune CAPDAC to remove parasitic capacitance. */
    uint16_t cap_offset_calib_configuration_data;
    cap_offset_calib_configuration_data = (((int16_t)cap_offset_calib) << 11);      
    fdc1004_write16(CAP_OFFSET_CALIB_CONFIG[measurement], cap_offset_calib_configuration_data);
    
    return 0;
}

static uint8_t fdc1004_configureMeasurements() 
{
    for (int i=0; i<FDC1004_NUM_MEASUREMENTS; i++) {
        fdc1004_configureMeasurementSingle(i, measurement_cfgs.measurements[i].channel, 
                                                measurement_cfgs.measurements[i].capdac,         
                                                    measurement_cfgs.measurements[i].cap_offset_calib); 
    } 

    measDelay = SAMPLE_DELAY[measurement_cfgs.rate];    
    
    return 0;
}

//static uint8_t fdc1004_triggerSingleMeasurement(uint8_t measurement, uint8_t rate)
//{
//    /* verify data */
//    if (!FDC1004_IS_MEAS(measurement) || !FDC1004_IS_RATE(rate)) {
//        return 1;
//    }
//    
//    uint16_t trigger_data;
//    trigger_data = ((uint16_t)rate) << 10;              // sample rate
//    trigger_data |= 0 << 8;                             // repeat disabled
//    trigger_data |= (1 << (7-measurement));             // 0 > bit 7, 1 > bit 6, etc
//    fdc1004_write16(FDC_REGISTER, trigger_data);
//    
//    return 0;
//}


///**
//* Check if measurement is done, and read the measurement into value if so.
//* value should be at least 4 bytes long (24 bit measurement)
//*/
//static uint8_t fdc1004_readMeasurement(uint8_t measurement, uint16_t * value)
//{
//    /* Verify data */
//    if (!FDC1004_IS_MEAS(measurement)) {
//        return 1;
//    }
//    
//    /* check if measurement is complete */
//    uint16_t fdc_register = fdc1004_read16(FDC_REGISTER);
//    if (! (fdc_register & ( 1 << (3-measurement)))) {
//        return 2;
//    }
//    
//    // read the value
//    uint16_t msb = fdc1004_read16(MEAS_MSB[measurement]);
//    uint16_t lsb = fdc1004_read16(MEAS_LSB[measurement]);
//    value[0] = msb;
//    value[1] = lsb;
//    return 0;
//}


static uint8_t fdc1004_triggerMeasurementSingle(uint8_t measurement)
{    
    /* Verify data */
    if (!FDC1004_IS_MEAS(measurement)) {
        return 1;
    }

    uint16_t trigger_data = 0;
    trigger_data = ((uint16_t)measurement_cfgs.rate) << 10;                                             // sample rate
    trigger_data |= 0 << 8;                                                                             // repeat disabled
    trigger_data |= ((measurement_cfgs.measurements[measurement].enable ? 1 : 0) << (7 - measurement)); // 0 > bit 7, 1 > bit 6, etc
    fdc1004_write16(FDC_REGISTER, trigger_data);
    
    return 0;
}

/**
* Check if measurement is done, and read the measurement into value if so.
* value should be at least 4 bytes long (24 bit measurement)
*/
static uint8_t fdc1004_readMeasurementSingle(uint8_t measurement, uint32_t *value)
{
    /* Verify data */
    if (!FDC1004_IS_MEAS(measurement)) {
        return 1;
    }
    
    /* Check if measurement is complete */
    uint16_t fdc_register = fdc1004_read16(FDC_REGISTER);
    if (! (fdc_register & ( 1 << (3 - measurement)))) {
        return 2;
    }
    
    /* Read 4-byte measurement value. */
    uint16_t msb = fdc1004_read16(MEAS_MSB[measurement]);
    uint16_t lsb = fdc1004_read16(MEAS_LSB[measurement]);
    
    *value = (((uint32_t)(msb)) << 16) + lsb;
    
    return 0;
}

/**
* Take a measurement
*/
uint8_t sweat_capacity_sensing(uint32_t *value)
{    
    /* Go through all the measurements. */
    for(int i=0; i<FDC1004_NUM_MEASUREMENTS; i++) {
    
        if(measurement_cfgs.measurements[i].enable) {
            
            if (fdc1004_triggerMeasurementSingle(i)) {
                return 1;
            }

            /* Delay and wait for the measurements to complete. */
            nrf_delay_ms(measDelay);            
                        
            /* Read a single measurement. */
            if(fdc1004_readMeasurementSingle(i, &value[i])) {
                return 1;
            }
                
        }
        
    }
    
    return 0;
}

///**
// *  function to get the capacitance from a channel.
//  */
//int32_t fdc1004_getCapacitance(uint8_t channel)
//{
//    fdc1004_measurement_t value;
//    uint8_t result = getRawCapacitance(channel, &value);
//    if (result) return 0x80000000;
//
//    int32_t capacitance = ((int32_t)ATTOFARADS_UPPER_WORD) * ((int32_t)value.value); //attofarads
//    capacitance /= 1000; //femtofarads
//    capacitance += ((int32_t)FEMTOFARADS_CAPDAC) * ((int32_t)value.capdac);
//    return capacitance;
//}

/**
 * @brief TWI events handler.
 */
static void twi_handler(nrf_drv_twi_evt_t const * p_event, void * p_context)
{
    switch (p_event->type)
    {
        case NRF_DRV_TWI_EVT_DONE:
            m_xfer_done = true;
            break;
            
        default:
            break;
    }
}

/**
 * @brief UART initialization.
 */
static void twi_init (void)
{
    ret_code_t err_code;

    const nrf_drv_twi_config_t twi_fdc1004_config = {
       .scl                = FDC1004_I2C_SCL_PIN,
       .sda                = FDC1004_I2C_SDA_PIN,
       .frequency          = NRF_DRV_TWI_FREQ_100K,
       .interrupt_priority = APP_IRQ_PRIORITY_LOW,
       .clear_bus_init     = false
    };

    err_code = nrf_drv_twi_init(&m_twi, &twi_fdc1004_config, twi_handler, NULL);
    APP_ERROR_CHECK(err_code);

    nrf_drv_twi_enable(&m_twi);
}

uint8_t sweat_capacity_sensing_cfg(fdc1004_measurement_cfg_t *new_meas_cfg)
{
    /* Configure measurements. */
    memcpy((uint8_t *)&measurement_cfgs, (uint8_t *)new_meas_cfg, sizeof(measurement_cfgs));
    
    if (fdc1004_configureMeasurements()) {
        return 1;
    }
    
    return 0;
}

uint8_t sweat_capacity_sensing_init()
{
    /* Initialize the I2C interface. */
    twi_init();
    
    /* Set the default configuration for capacity measurement. */
    measurement_cfgs.rate = FDC1004_100HZ;
    
    measurement_cfgs.measurements[0].channel = 0;           /* CH1 */   
    measurement_cfgs.measurements[0].capdac = 0;            /* 0pF */
    measurement_cfgs.measurements[0].cap_offset_calib = 0;
    measurement_cfgs.measurements[0].enable = 1;
    
    measurement_cfgs.measurements[1].channel = 1;           /* CH2 */
    measurement_cfgs.measurements[1].capdac = 12;           /* 37.5pF */
    measurement_cfgs.measurements[1].cap_offset_calib = 0;
    measurement_cfgs.measurements[1].enable = 1;
    
    /* Configure measurements. */
    if (fdc1004_configureMeasurements()) {
        return 1;
    }
    
    return 0;
}





